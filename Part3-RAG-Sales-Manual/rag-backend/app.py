"""
Consolidated RAG Backend Service with OpenSearch
Adapted from IBM project-ai-services implementation
Enhanced with hybrid query routing and reranking
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import logging
import hashlib
import numpy as np
import json
from datetime import datetime
from opensearchpy import OpenSearch, helpers
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
import requests

from docling_config import (
    USE_DOCLING,
    DOCLING_CHUNK_SIZE,
    DOCLING_CHUNK_OVERLAP,
    PDF_CHUNK_SIZE,
    docling_config_dict,
)

# Import hybrid query components
from query_classifier import QueryClassifier, QueryType
from table_lookup_service import TableLookupService
from reranker_service import RerankerService

app = Flask(__name__)

# Configure CORS
cors_origin = os.environ.get('CORS_ORIGIN', '*')
if cors_origin == '*':
    CORS(app)
else:
    CORS(app, origins=[cors_origin])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional web scraping support
try:
    from web_scraper import IBMDocsScraper, create_langchain_documents, IBMDocsScraperError
    WEB_SCRAPING_AVAILABLE = True
    logger.info("Web scraping module loaded successfully")
except ImportError:
    WEB_SCRAPING_AVAILABLE = False
    logger.warning("Web scraping module not available. Running in PDF-only mode.")

# Configuration from environment variables
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))
OPENSEARCH_USERNAME = os.environ.get('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.environ.get('OPENSEARCH_PASSWORD', 'admin')
OPENSEARCH_DB_PREFIX = os.environ.get('OPENSEARCH_DB_PREFIX', 'rag').lower()
OPENSEARCH_NUM_SHARDS = int(os.environ.get('OPENSEARCH_NUM_SHARDS', '1'))
OPENSEARCH_USE_SSL = os.environ.get('OPENSEARCH_USE_SSL', 'false').lower() == 'true'

# LLM Service Configuration
# Granite service (for RAG - Part 3)
GRANITE_HOST = os.environ.get('GRANITE_HOST', os.environ.get('LLAMA_HOST', 'granite-llama-service'))
GRANITE_PORT = os.environ.get('GRANITE_PORT', os.environ.get('LLAMA_PORT', '8080'))

# TinyLlama service (for Part 1 - demonstrates hallucinations)
TINYLLAMA_HOST = os.environ.get('TINYLLAMA_HOST', 'tinyllama-service')
TINYLLAMA_PORT = os.environ.get('TINYLLAMA_PORT', '8080')

# Legacy support - default to Granite
LLAMA_HOST = GRANITE_HOST
LLAMA_PORT = GRANITE_PORT

PDF_DIR = os.environ.get('PDF_DIR', '/app/pdfs')

# Initialize OpenSearch client (lazy loading)
_opensearch_client = None

def get_opensearch_client():
    """Lazy load OpenSearch client"""
    global _opensearch_client
    if _opensearch_client is None:
        logger.info(f"Initializing OpenSearch client at {OPENSEARCH_HOST}:{OPENSEARCH_PORT} (SSL: {OPENSEARCH_USE_SSL})")
        _opensearch_client = OpenSearch(
            hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
            http_compress=True,
            use_ssl=OPENSEARCH_USE_SSL,
            http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD) if OPENSEARCH_USE_SSL else None,
            verify_certs=False,
            ssl_show_warn=False
        )
        logger.info("OpenSearch client initialized successfully")
        _create_hybrid_pipeline()
    return _opensearch_client

# Initialize embeddings model (lazy loading)
_embeddings = None

def get_embeddings():
    """Lazy load embeddings model"""
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embeddings model...")
        _embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        logger.info("Embeddings model loaded")
    return _embeddings

# Initialize hybrid query components (lazy loading)
_query_classifier = None
_table_lookup_service = None
_reranker_service = None

def get_query_classifier():
    """Lazy load query classifier"""
    global _query_classifier
    if _query_classifier is None:
        logger.info("Initializing query classifier")
        _query_classifier = QueryClassifier()
        logger.info("Query classifier initialized successfully")
    return _query_classifier

def get_table_lookup_service():
    """Lazy load table lookup service"""
    global _table_lookup_service
    if _table_lookup_service is None:
        logger.info("Initializing table lookup service")
        _table_lookup_service = TableLookupService()
        logger.info("Table lookup service initialized successfully")
    return _table_lookup_service

def get_reranker_service():
    """Lazy load reranker service"""
    global _reranker_service
    if _reranker_service is None:
        logger.info("Initializing reranker service (downloading model if needed)")
        _reranker_service = RerankerService()
        logger.info("Reranker service initialized successfully")
    return _reranker_service

def _generate_index_name(collection_name):
    """Generate OpenSearch index name from collection name"""
    hash_part = hashlib.md5(collection_name.encode()).hexdigest()
    return f"{OPENSEARCH_DB_PREFIX}_{hash_part}"

def _create_hybrid_pipeline():
    """Create hybrid search pipeline for combining dense and sparse results"""
    client = get_opensearch_client()
    pipeline_body = {
        "description": "Post-processor for hybrid search",
        "phase_results_processors": [
            {
                "normalization-processor": {
                    "normalization": {"technique": "min_max"},
                    "combination": {
                        "technique": "arithmetic_mean",
                        "parameters": {
                            "weights": [0.3, 0.7]  # Semantic heavy weights
                        }
                    }
                }
            }
        ]
    }
    try:
        client.search_pipeline.put(id="hybrid_pipeline", body=pipeline_body)
        logger.info("Hybrid search pipeline created successfully")
    except Exception as e:
        logger.warning(f"Hybrid pipeline may already exist: {e}")

def _setup_index(index_name, dim=384):
    """Setup OpenSearch index with k-NN configuration"""
    client = get_opensearch_client()
    
    if client.indices.exists(index=index_name):
        logger.info(f"Index {index_name} already exists")
        return
    
    logger.info(f"Creating new index {index_name} with dimension {dim}")
    
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100,
                "number_of_shards": OPENSEARCH_NUM_SHARDS,
                'auto_expand_replicas': '0-all'
            }
        },
        "mappings": {
            "properties": {
                "chunk_id": {"type": "long"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene",
                        "parameters": {
                            "ef_construction": 128,
                            "m": 24
                        }
                    }
                },
                "text": {
                    "type": "text",
                    "analyzer": "standard"
                },
                "metadata": {
                    "dynamic": "true",
                    "properties": {
                        "filename": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "source": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "chunk_index": {"type": "integer"},
                        "created_at": {"type": "date"},
                        "chapter": {"type": "text"},
                        "section": {"type": "text"},
                        "subsection": {"type": "text"},
                        "subsubsection": {"type": "text"},
                        "type": {"type": "keyword"},
                        "part_index": {"type": "integer"},
                        "processing_method": {"type": "keyword"}
                    }
                }
            }
        }
    }
    
    try:
        client.indices.create(index=index_name, body=index_body)
        logger.info(f"Index {index_name} created successfully")
    except Exception as e:
        logger.error(f"Failed to create index {index_name}: {e}")
        raise

def generate_chunk_id(doc_id, page_content):
    """Generate deterministic chunk ID"""
    base = f"{doc_id}||{page_content}"
    hash_digest = hashlib.md5(base.encode("utf-8")).hexdigest()
    chunk_int = int(hash_digest[:16], 16)
    chunk_id = chunk_int % (2**63)
    return np.int64(chunk_id)

# ============================================================================
# COLLECTION MANAGEMENT ENDPOINTS
# ============================================================================

@app.route('/api/collections', methods=['GET'])
def list_collections():
    """List all collections (OpenSearch indices) with MTM-based reverse mapping"""
    try:
        client = get_opensearch_client()
        indices = client.indices.get(index=f"{OPENSEARCH_DB_PREFIX}_*")
        
        # Build a reverse mapping: try to match hashed index names to known MTM-based collection names
        # For IBM Power servers, collection names are based on MTM: mtm_9080_heu, mtm_9009_42a, etc.
        known_mtms = [
            # POWER11
            "9080-HEU", "9043-MRU", "9824-42A", "9824-22A",
            # POWER10
            "9080-HEX", "9043-MRX", "9105-42A", "9105-22A",
            "9105-41B", "9028-21B", "9786-42H", "9786-22H",
            # POWER9
            "9080-M9S", "9040-MR9", "9009-42A", "9009-42G",
            "9009-22A", "9009-22G", "9009-41A", "9009-41G",
            "9223-42S", "9223-22S", "9183-22X", "9008-22L",
            "9006-22P", "9006-12P"
        ]
        
        collections_map = {}
        index_names = list(indices.keys())
        
        # Try to match each known MTM to its hashed index
        for mtm in known_mtms:
            collection_name = f"mtm_{mtm.lower().replace('-', '_')}"
            expected_index = _generate_index_name(collection_name)
            if expected_index in index_names:
                collections_map[mtm] = expected_index
        
        logger.info(f"Found {len(collections_map)} indexed MTMs: {list(collections_map.keys())}")
        
        return jsonify({
            'success': True,
            'collections': index_names,  # Keep for backward compatibility
            'collections_map': collections_map  # New: MTM -> index_name mapping
        })
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/collections/<collection_name>', methods=['DELETE'])
def drop_collection(collection_name):
    """Drop a specific collection (delete OpenSearch index)"""
    try:
        client = get_opensearch_client()
        index_name = _generate_index_name(collection_name)
        
        logger.info(f"Dropping collection: {collection_name} (index: {index_name})")
        
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            logger.info(f"Collection {collection_name} dropped successfully")
            return jsonify({
                'success': True,
                'message': f'Collection {collection_name} dropped successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Collection {collection_name} does not exist'
            }), 404
            
    except Exception as e:
        logger.error(f"Error dropping collection: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# PDF LOADING ENDPOINT
# ============================================================================

@app.route('/api/load-pdf', methods=['POST'])
def load_pdf():
    """Load a PDF into OpenSearch"""
    try:
        data = request.get_json()
        server_name = data.get('server_name')
        collection_name = data.get('collection_name', 'sales_manuals')

        if not server_name:
            return jsonify({'error': 'server_name is required'}), 400

        pdf_path = os.path.join(PDF_DIR, f"{server_name}.pdf")

        if not os.path.exists(pdf_path):
            return jsonify({'error': f'PDF not found: {pdf_path}'}), 404

        logger.info(f"Loading PDF: {pdf_path}")
        logger.info(f"Docling configuration: {docling_config_dict()}")

        processing_method = 'pypdf'
        processed_chunks = []

        if USE_DOCLING:
            try:
                from docling_converter import convert_pdf_chunked
                from hierarchical_chunker import chunk_with_hierarchy

                logger.info("USE_DOCLING enabled. Processing with Docling.")
                docling_doc = convert_pdf_chunked(pdf_path, chunk_size=PDF_CHUNK_SIZE)
                processed_chunks = chunk_with_hierarchy(
                    docling_doc,
                    max_tokens=DOCLING_CHUNK_SIZE,
                    overlap=DOCLING_CHUNK_OVERLAP
                )
                processing_method = 'docling'
            except Exception as docling_error:
                logger.exception(
                    f"Docling conversion failed for {pdf_path}. Falling back to PyPDF. Error: {docling_error}"
                )

        if not processed_chunks:
            logger.info("Processing PDF with PyPDF fallback.")
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()

            text_splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=DOCLING_CHUNK_SIZE,
                chunk_overlap=0
            )
            docs = text_splitter.split_documents(docs)

            for i, doc in enumerate(docs):
                processed_chunks.append({
                    "text": doc.page_content,
                    "metadata": {
                        "filename": f"{server_name}.pdf",
                        "doc_id": server_name,
                        "source": doc.metadata.get('source', ''),
                        "page_number": doc.metadata.get('page', i),
                        "chunk_index": i,
                        "created_at": datetime.utcnow().isoformat(),
                        "chapter": None,
                        "section": None,
                        "subsection": None,
                        "subsubsection": None,
                        "type": "text",
                        "part_index": 0,
                        "processing_method": "pypdf"
                    }
                })

        logger.info(f"Prepared {len(processed_chunks)} chunks using {processing_method}")

        embeddings = get_embeddings()
        index_name = _generate_index_name(collection_name)
        _setup_index(index_name)

        client = get_opensearch_client()
        actions = []

        for i, chunk in enumerate(processed_chunks):
            page_content = chunk.get("text", "")
            if not page_content.strip():
                continue

            doc_id = server_name
            chunk_id = generate_chunk_id(doc_id, page_content)
            embedding = embeddings.embed_query(page_content)

            chunk_metadata = chunk.get("metadata", {})
            metadata = {
                "filename": chunk_metadata.get("filename", f"{server_name}.pdf"),
                "doc_id": chunk_metadata.get("doc_id", doc_id),
                "source": chunk_metadata.get("source", processing_method),
                "page_number": chunk_metadata.get("page_number", i),
                "chunk_index": i,
                "created_at": chunk_metadata.get("created_at", datetime.utcnow().isoformat()),
                "chapter": chunk_metadata.get("chapter"),
                "section": chunk_metadata.get("section"),
                "subsection": chunk_metadata.get("subsection"),
                "subsubsection": chunk_metadata.get("subsubsection"),
                "type": chunk_metadata.get("type", "text"),
                "part_index": chunk_metadata.get("part_index", 0),
                "processing_method": processing_method
            }

            actions.append({
                "_index": index_name,
                "_id": str(chunk_id),
                "_source": {
                    "chunk_id": chunk_id,
                    "embedding": embedding,
                    "text": page_content,
                    "metadata": metadata
                }
            })

        success_count, errors = helpers.bulk(
            client,
            actions,
            stats_only=False,
            raise_on_error=False,
            refresh=True
        )

        if errors:
            logger.error(f"Some chunks failed to insert: {len(errors)} errors")
            return jsonify({
                'success': False,
                'error': 'Some chunks failed to insert',
                'chunks_inserted': success_count,
                'chunks_failed': len(errors),
                'method': processing_method
            }), 500

        logger.info(f"Successfully loaded {server_name} into collection {collection_name}")

        return jsonify({
            'success': True,
            'message': f'Successfully loaded {server_name}',
            'chunks': len(actions),
            'collection': collection_name,
            'method': processing_method
        })

    except Exception as e:
        logger.error(f"Error loading PDF: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/load-pdf-url', methods=['POST'])
def load_pdf_url():
    """Load a PDF from a URL into OpenSearch using simple PyPDF approach"""
    try:
        data = request.get_json()
        pdf_url = data.get('pdf_url')
        collection_name = data.get('collection_name', 'demo')
        chunk_size = data.get('chunk_size', 768)
        
        if not pdf_url:
            return jsonify({'error': 'pdf_url is required'}), 400
        
        logger.info(f"Downloading PDF from URL: {pdf_url}")
        
        # Download PDF to temporary file
        import tempfile
        response = requests.get(pdf_url, timeout=60)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(response.content)
            tmp_pdf_path = tmp_file.name
        
        try:
            logger.info(f"Loading PDF with PyPDFLoader: {tmp_pdf_path}")
            loader = PyPDFLoader(tmp_pdf_path)
            docs = loader.load()
            
            # Split documents into chunks (matching notebook approach)
            text_splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=chunk_size,
                chunk_overlap=0
            )
            docs = text_splitter.split_documents(docs)
            
            logger.info(f"Split into {len(docs)} chunks")
            
            # Get embeddings
            embeddings = get_embeddings()
            index_name = _generate_index_name(collection_name)
            _setup_index(index_name)
            
            client = get_opensearch_client()
            actions = []
            
            for i, doc in enumerate(docs):
                page_content = doc.page_content
                if not page_content.strip():
                    continue
                
                chunk_id = generate_chunk_id(collection_name, page_content)
                embedding = embeddings.embed_query(page_content)
                
                metadata = {
                    "filename": pdf_url.split('/')[-1],
                    "doc_id": collection_name,
                    "source": pdf_url,
                    "page_number": doc.metadata.get('page', i),
                    "chunk_index": i,
                    "created_at": datetime.utcnow().isoformat(),
                    "type": "text",
                    "processing_method": "pypdf"
                }
                
                actions.append({
                    "_index": index_name,
                    "_id": str(chunk_id),
                    "_source": {
                        "chunk_id": chunk_id,
                        "embedding": embedding,
                        "text": page_content,
                        "metadata": metadata
                    }
                })
            
            success_count, errors = helpers.bulk(
                client,
                actions,
                stats_only=False,
                raise_on_error=False,
                refresh=True
            )
            
            if errors:
                logger.error(f"Some chunks failed to insert: {len(errors)} errors")
                return jsonify({
                    'success': False,
                    'error': 'Some chunks failed to insert',
                    'chunks_inserted': success_count,
                    'chunks_failed': len(errors)
                }), 500
            
            logger.info(f"Successfully loaded PDF from URL into collection {collection_name}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully loaded PDF from URL',
                'chunks': len(actions),
                'collection': collection_name,
                'url': pdf_url
            })
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_pdf_path)
    
    except Exception as e:
        logger.error(f"Error loading PDF from URL: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# SEARCH ENDPOINT
# ============================================================================

@app.route('/api/search', methods=['POST'])
def search():
    """
    Enhanced search with hybrid query routing and reranking
    Routes queries to appropriate handler based on classification
    """
    try:
        data = request.get_json()
        question = data.get('question')
        collection_name = data.get('collection_name', 'sales_manuals')
        k = data.get('k', 5)  # Increased default for reranking
        mode = data.get('mode', 'hybrid')  # dense, sparse, or hybrid
        use_reranking = data.get('use_reranking', True)  # Enable reranking by default
        
        if not question:
            return jsonify({'error': 'question is required'}), 400
        
        logger.info(f"Searching in collection {collection_name} for: {question}")
        
        # Step 1: Classify the query
        classifier = get_query_classifier()
        classification = classifier.classify(question)
        
        logger.info(f"Query classified as: {classification['query_type']}")
        logger.info(f"Entities: {classification.get('entities', {})}")
        
        # Step 2: Route based on classification
        if classification['query_type'] == QueryType.TABLE_LOOKUP:
            # Direct table lookup - no LLM needed
            table_service = get_table_lookup_service()
            result = table_service.lookup(
                server_model=classification['entities'].get('server_model'),
                field=classification['entities'].get('field')
            )
            
            return jsonify({
                'success': True,
                'query_type': 'table_lookup',
                'results': [{
                    'content': result['answer'],
                    'metadata': {
                        'source': 'lifecycle_table',
                        'server_model': result.get('server_model'),
                        'field': result.get('field'),
                        'confidence': result.get('confidence', 1.0)
                    },
                    'score': 1.0
                }],
                'count': 1,
                'classification': classification
            })
        
        elif classification['query_type'] == QueryType.METADATA_LOOKUP:
            # Metadata-based search (e.g., feature codes, withdrawal dates)
            # Use OpenSearch metadata filters
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({'error': f'Collection {collection_name} does not exist'}), 404
            
            # Build metadata query
            must_clauses = [{"match": {"text": question}}]
            
            # Add entity filters if available
            if 'server_model' in classification['entities']:
                must_clauses.append({
                    "match": {"metadata.server_model": classification['entities']['server_model']}
                })
            
            if 'feature_code' in classification['entities']:
                must_clauses.append({
                    "match": {"metadata.feature_codes": classification['entities']['feature_code']}
                })
            
            search_body = {
                "size": k * 2,  # Get more for reranking
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": must_clauses
                    }
                }
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Metadata search found {len(hits)} results")
            
        else:  # QueryType.RAG - Standard RAG with vector search
            # Get embeddings and client
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({'error': f'Collection {collection_name} does not exist'}), 404
            
            # Generate query embedding
            query_vector = embeddings.embed_query(question)
            
            # Retrieve more candidates for reranking
            retrieval_k = k * 4 if use_reranking else k
            
            # Build search query based on mode
            if mode == "dense":
                search_body = {
                    "size": retrieval_k,
                    "_source": ["chunk_id", "text", "metadata"],
                    "query": {
                        "knn": {
                            "embedding": {
                                "vector": query_vector,
                                "k": retrieval_k
                            }
                        }
                    }
                }
            elif mode == "sparse":
                search_body = {
                    "size": retrieval_k,
                    "_source": ["chunk_id", "text", "metadata"],
                    "query": {
                        "match": {"text": question}
                    }
                }
            else:  # hybrid
                search_body = {
                    "size": retrieval_k,
                    "_source": ["chunk_id", "text", "metadata"],
                    "query": {
                        "hybrid": {
                            "queries": [
                                {
                                    "knn": {
                                        "embedding": {
                                            "vector": query_vector,
                                            "k": retrieval_k
                                        }
                                    }
                                },
                                {
                                    "match": {"text": question}
                                }
                            ]
                        }
                    }
                }
            
            # Execute search
            params = {"search_pipeline": "hybrid_pipeline"} if mode == "hybrid" else {}
            response = client.search(index=index_name, body=search_body, params=params)
            hits = response['hits']['hits']
            
            logger.info(f"Vector search found {len(hits)} results")
        
        # Step 3: Apply reranking if enabled and we have RAG/metadata results
        if use_reranking and classification['query_type'] != QueryType.TABLE_LOOKUP and len(hits) > 0:
            reranker = get_reranker_service()
            
            # Extract texts for reranking
            texts = [hit["_source"].get("text", "") for hit in hits]
            
            # Rerank
            reranked_indices = reranker.rerank(question, texts, top_k=k)
            
            # Reorder hits based on reranking
            reranked_hits = [hits[i] for i in reranked_indices]
            
            logger.info(f"Reranked to top {len(reranked_hits)} results")
        else:
            # No reranking - just take top k
            reranked_hits = hits[:k]
        
        # Step 4: Format results
        formatted_results = []
        for i, hit in enumerate(reranked_hits):
            source = hit["_source"]
            result = {
                'content': source.get("text"),
                'metadata': source.get("metadata", {}),
                'score': float(hit.get("_score", 0)),
                'rank': i + 1,
                'reranked': use_reranking and classification['query_type'] != QueryType.TABLE_LOOKUP
            }
            formatted_results.append(result)
        
        return jsonify({
            'success': True,
            'query_type': classification['query_type'].value,
            'results': formatted_results,
            'count': len(formatted_results),
            'classification': classification,
            'reranking_applied': use_reranking and classification['query_type'] != QueryType.TABLE_LOOKUP
        })
        
    except Exception as e:
        logger.error(f"Error searching: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SCRAPED CONTENT INGESTION ENDPOINT
# ============================================================================

@app.route('/ingest-scraped-content', methods=['POST'])
def ingest_scraped_content():
    """
    Ingest scraped content from Windows scraper
    Accepts JSON with sections and creates embeddings for RAG
    Each server gets its own collection: power_e1180, power_e1150, etc.
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('success'):
            return jsonify({'error': 'Invalid scraped data'}), 400
        
        url = data.get('url', 'unknown')
        page_title = data.get('page_title', 'Untitled')
        sections = data.get('sections', [])
        full_text = data.get('full_text', '')
        server_model = data.get('server_model', None)  # e.g., "E1180"
        
        if not sections:
            return jsonify({'error': 'No sections found in scraped data'}), 400
        
        logger.info(f"Ingesting scraped content from: {url}")
        logger.info(f"Title: {page_title}, Sections: {len(sections)}")
        
        # Create collection name based on server model
        if server_model:
            # Convert E1180 -> power_e1180
            collection_name = f"{OPENSEARCH_DB_PREFIX}_power_{server_model.lower().replace('-', '_')}"
            logger.info(f"Using server-specific collection: {collection_name}")
        else:
            # Fallback to generic collection
            collection_name = f"{OPENSEARCH_DB_PREFIX}_ibm_docs"
            logger.warning(f"No server_model provided, using generic collection: {collection_name}")
        
        # Initialize OpenSearch and embeddings
        client = get_opensearch_client()
        embeddings = get_embeddings()
        
        # Generate index name and create if needed
        index_name = _generate_index_name(collection_name)
        _setup_index(index_name, embeddings.client.get_sentence_embedding_dimension())
        
        # Process sections into documents
        documents = []
        for i, section in enumerate(sections):
            section_title = section.get('title', f'Section {i+1}')
            section_content = section.get('content', [])
            
            # Combine section content
            if isinstance(section_content, list):
                text = '\n'.join([
                    item.get('text', item) if isinstance(item, dict) else str(item)
                    for item in section_content
                ])
            else:
                text = str(section_content)
            
            # Skip empty sections
            if not text.strip():
                continue
            
            # Create document with metadata
            doc = {
                'text': f"{section_title}\n\n{text}",
                'metadata': {
                    'source': url,
                    'page_title': page_title,
                    'section_title': section_title,
                    'section_level': section.get('level', 'unknown'),
                    'section_index': i,
                    'scraped_at': data.get('scraped_at', datetime.now().isoformat()),
                    'scraper_method': data.get('method', 'unknown')
                }
            }
            documents.append(doc)
        
        if not documents:
            return jsonify({'error': 'No valid content found in sections'}), 400
        
        logger.info(f"Processing {len(documents)} documents for indexing")
        
        # Create embeddings and index documents
        indexed_count = 0
        failed_count = 0
        
        for doc in documents:
            try:
                # Generate embedding
                embedding = embeddings.embed_query(doc['text'])
                
                # Create document ID
                doc_id = hashlib.md5(
                    f"{doc['metadata']['source']}_{doc['metadata']['section_index']}".encode()
                ).hexdigest()
                
                # Index document
                client.index(
                    index=index_name,
                    id=doc_id,
                    body={
                        'text': doc['text'],
                        'embedding': embedding,
                        'metadata': doc['metadata']
                    }
                )
                indexed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to index document: {e}")
                failed_count += 1
        
        # Refresh index
        client.indices.refresh(index=index_name)
        
        logger.info(f"Ingestion complete: {indexed_count} indexed, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'collection': collection_name,
            'indexed': indexed_count,
            'failed': failed_count,
            'total_sections': len(sections),
            'page_title': page_title,
            'source_url': url
        })
        
    except Exception as e:
        logger.error(f"Error ingesting scraped content: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# LLM GENERATION ENDPOINT
# ============================================================================

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate response from LLM with model selection support"""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        temperature = data.get('temperature', 0.1)
        n_predict = data.get('n_predict', 256)  # Increased from 100 to 256 for better responses
        stream = data.get('stream', False)
        model = data.get('model', 'granite')  # 'granite' or 'tinyllama'
        
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        
        # Select LLM service based on model parameter
        if model.lower() == 'tinyllama':
            llm_host = TINYLLAMA_HOST
            llm_port = TINYLLAMA_PORT
            logger.info(f"Using TinyLlama model at {llm_host}:{llm_port}")
        else:
            llm_host = GRANITE_HOST
            llm_port = GRANITE_PORT
            logger.info(f"Using Granite model at {llm_host}:{llm_port}")
        
        logger.info(f"Generating response with temperature={temperature}, n_predict={n_predict}, model={model}, stream={stream}")
        
        # Call LLM service
        llm_url = f"http://{llm_host}:{llm_port}/completion"
        
        payload = {
            "prompt": prompt,
            "temperature": temperature,
            "n_predict": n_predict,
            "stream": stream
        }
        
        # Handle streaming response
        if stream:
            def generate_stream():
                try:
                    with requests.post(llm_url, json=payload, stream=True, timeout=300) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if line:
                                decoded_line = line.decode('utf-8')
                                if decoded_line.startswith('data: '):
                                    yield f"{decoded_line}\n\n"
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return Response(generate_stream(), mimetype='text/event-stream')
        
        # Non-streaming response
        response = requests.post(llm_url, json=payload, timeout=180)
        response.raise_for_status()
        
        result = response.json()
        
        return jsonify({
            'success': True,
            'content': result.get('content', ''),
            'model': model,
            'timings': result.get('timings', {})
        })
        
    except requests.exceptions.Timeout:
        logger.error("LLM request timed out")
        return jsonify({'error': 'LLM request timed out'}), 504
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling LLM: {e}")
        return jsonify({'error': f'Failed to call LLM: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({'error': str(e)}), 500
# ============================================================================
# SALES MANUAL BULK INGESTION ENDPOINTS
# ============================================================================

# Global state for tracking bulk ingestion progress
bulk_ingestion_state = {
    'in_progress': False,
    'current_server': None,
    'completed': [],
    'failed': [],
    'total': 0,
    'started_at': None
}

@app.route('/api/ingest-sales-manual', methods=['POST'])
def ingest_sales_manual():
    """
    Trigger scraping and ingestion of a single IBM Power server Sales Manual
    Calls the Windows scraper service and ingests the results
    Uses MTM (Machine Type-Model) as the unique identifier for collections
    """
    try:
        data = request.get_json()
        mtm = data.get('mtm')  # e.g., "9080-HEU", "9009-42A"
        server_model = data.get('server_model')  # e.g., "E1180", "S924"
        server_name = data.get('server_name')  # e.g., "IBM Power E1180"
        processor = data.get('processor', 'POWER')
        sales_manual_url = data.get('url')  # Sales manual URL
        
        if not mtm:
            return jsonify({'error': 'mtm is required'}), 400
        if not sales_manual_url:
            return jsonify({'error': 'url is required'}), 400
        
        logger.info(f"Starting Sales Manual ingestion for MTM {mtm} ({server_name})")
        
        # Update bulk ingestion state
        bulk_ingestion_state['current_server'] = f"{server_model} ({mtm})"
        
        # Call Windows scraper service
        # The scraper is running on the Windows laptop
        scraper_url = os.environ.get('SCRAPER_URL', 'http://host.docker.internal:5000')
        
        logger.info(f"Calling scraper at {scraper_url}/scrape?url={sales_manual_url}")
        
        try:
            # Use GET request with URL parameter as the scraper expects
            scraper_response = requests.get(
                f"{scraper_url}/scrape",
                params={'url': sales_manual_url, 'wait': 10},
                timeout=600  # 10 minute timeout for scraping
            )
            scraper_response.raise_for_status()
            scraper_data = scraper_response.json()
            
            if not scraper_data.get('success'):
                error_msg = scraper_data.get('error', 'Scraping failed')
                logger.error(f"Scraper failed for MTM {mtm}: {error_msg}")
                bulk_ingestion_state['failed'].append({
                    'server': mtm,
                    'error': error_msg
                })
                return jsonify({'error': error_msg}), 500
            
            logger.info(f"Scraping successful for MTM {mtm}, got {scraper_data.get('sections_count', 0)} sections")
            
        except requests.exceptions.Timeout:
            error_msg = f"Scraper timeout for MTM {mtm}"
            logger.error(error_msg)
            bulk_ingestion_state['failed'].append({
                'server': mtm,
                'error': 'Timeout'
            })
            return jsonify({'error': error_msg}), 504
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to call scraper: {str(e)}"
            logger.error(error_msg)
            bulk_ingestion_state['failed'].append({
                'server': mtm,
                'error': str(e)
            })
            return jsonify({'error': error_msg}), 500
        
        # Now ingest the scraped content
        # Collection name based on MTM: mtm_9080_heu, mtm_9009_42a, etc.
        collection_name = f"mtm_{mtm.lower().replace('-', '_')}"
        
        logger.info(f"Ingesting scraped content into collection: {collection_name}")
        
        # Transform Code Engine scraper format to expected format
        # Code Engine returns: {"full_text": "...", ...}
        # Backend expects: {"success": true, "sections": [...], ...}
        transformed_data = {
            'success': True,
            'url': sales_manual_url,
            'page_title': f"{server_name} Sales Manual",
            'server_model': server_model,
            'mtm': mtm,
            'sections': [{
                'title': f"{server_name} Documentation",
                'content': scraper_data.get('full_text', ''),
                'level': 1
            }],
            'scraped_at': datetime.now().isoformat()
        }
        
        # Call the existing ingest-scraped-content endpoint
        ingest_response = requests.post(
            'http://localhost:8080/ingest-scraped-content',
            json=transformed_data,
            timeout=300  # 5 minute timeout for ingestion
        )
        
        if ingest_response.status_code == 200:
            ingest_data = ingest_response.json()
            logger.info(f"Successfully ingested MTM {mtm}: {ingest_data.get('indexed', 0)} documents")
            bulk_ingestion_state['completed'].append(mtm)
            
            return jsonify({
                'success': True,
                'mtm': mtm,
                'server_model': server_model,
                'collection': collection_name,
                'indexed': ingest_data.get('indexed', 0),
                'sections': scraper_data.get('sections_count', 0)
            })
        else:
            error_msg = f"Ingestion failed: {ingest_response.text}"
            logger.error(error_msg)
            bulk_ingestion_state['failed'].append({
                'server': mtm,
                'error': 'Ingestion failed'
            })
            return jsonify({'error': error_msg}), 500
            
    except Exception as e:
        logger.error(f"Error in ingest_sales_manual: {e}")
        bulk_ingestion_state['failed'].append({
            'server': mtm if 'mtm' in locals() else 'unknown',
            'error': str(e)
        })
        return jsonify({'error': str(e)}), 500
    finally:
        bulk_ingestion_state['current_server'] = None
        
        # Check if bulk ingestion is complete
        if bulk_ingestion_state['in_progress']:
            total_processed = len(bulk_ingestion_state['completed']) + len(bulk_ingestion_state['failed'])
            if total_processed >= bulk_ingestion_state['total']:
                bulk_ingestion_state['in_progress'] = False
                logger.info(f"Bulk ingestion complete: {len(bulk_ingestion_state['completed'])} succeeded, {len(bulk_ingestion_state['failed'])} failed")


@app.route('/api/bulk-ingestion-status', methods=['GET'])
def bulk_ingestion_status():
    """
    Get the current status of bulk ingestion process
    Returns progress information for polling
    """
    try:
        status = {
            'in_progress': bulk_ingestion_state['in_progress'],
            'current_server': bulk_ingestion_state['current_server'],
            'completed': bulk_ingestion_state['completed'],
            'failed': bulk_ingestion_state['failed'],
            'total': bulk_ingestion_state['total'],
            'completed_count': len(bulk_ingestion_state['completed']),
            'failed_count': len(bulk_ingestion_state['failed']),
            'started_at': bulk_ingestion_state['started_at']
        }
        logger.info(f"[Bulk Ingestion Status] in_progress={status['in_progress']}, current={status['current_server']}, completed={status['completed_count']}/{status['total']}")
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting bulk ingestion status: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/init-bulk-ingestion', methods=['POST'])
def init_bulk_ingestion():
    """
    Initialize the bulk ingestion state before starting
    Called by frontend before triggering individual server ingestions
    """
    try:
        data = request.get_json()
        total = data.get('total', 0)
        
        # Reset the bulk ingestion state
        bulk_ingestion_state['in_progress'] = True
        bulk_ingestion_state['current_server'] = None
        bulk_ingestion_state['completed'] = []
        bulk_ingestion_state['failed'] = []
        bulk_ingestion_state['total'] = total
        bulk_ingestion_state['started_at'] = datetime.now().isoformat()
        
        logger.info(f"Initialized bulk ingestion for {total} servers")
        
        return jsonify({
            'success': True,
            'message': f'Bulk ingestion initialized for {total} servers'
        })
    except Exception as e:
        logger.error(f"Error initializing bulk ingestion: {e}")
        return jsonify({'error': str(e)}), 500
@app.route('/api/start-bulk-ingestion', methods=['POST'])
def start_bulk_ingestion():
    """
    Start bulk ingestion of all servers in a background thread
    Returns immediately and processes servers asynchronously
    Uses MTM (Machine Type-Model) as unique identifier
    """
    try:
        # Server list with MTM and URLs - ordered by processor generation (Power11 -> Power10 -> Power9)
        # Within each generation: Enterprise first, then Scale-out, then others (largest to smallest)
        servers = [
            # POWER11
            {"mtm": "9080-HEU", "model": "E1180", "name": "IBM Power E1180", "processor": "POWER11", "url": "https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu"},
            {"mtm": "9043-MRU", "model": "E1150", "name": "IBM Power E1150", "processor": "POWER11", "url": "https://www.ibm.com/docs/en/announcements/family-904302-power-e1150-enterprise-midrange-technology-based-server-9043-mru"},
            {"mtm": "9824-42A", "model": "S1124", "name": "IBM Power S1124", "processor": "POWER11", "url": "https://www.ibm.com/docs/en/announcements/family-982402-power-s1124-9824-42a"},
            {"mtm": "9824-22A", "model": "S1122", "name": "IBM Power S1122", "processor": "POWER11", "url": "https://www.ibm.com/docs/en/announcements/family-982401-power-s1122-9824-22a"},
            # POWER10
            {"mtm": "9080-HEX", "model": "E1080", "name": "IBM Power E1080", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-e1080-enterprise-server"},
            {"mtm": "9043-MRX", "model": "E1050", "name": "IBM Power E1050", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-e1050-enterprise-midrange-technology-based-server"},
            {"mtm": "9105-42A", "model": "S1024", "name": "IBM Power S1024", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-s1024-9105-42a"},
            {"mtm": "9105-22A", "model": "S1022", "name": "IBM Power S1022", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-s1022-9105-22a"},
            {"mtm": "9105-41B", "model": "S1014", "name": "IBM Power S1014", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-s1014-9105-41b"},
            {"mtm": "9028-21B", "model": "S1012", "name": "IBM Power S1012", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/family-9028-01-power-s1012"},
            {"mtm": "9786-42H", "model": "L1024", "name": "IBM Power L1024", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-l1024-9786-42h"},
            {"mtm": "9786-22H", "model": "L1022", "name": "IBM Power L1022", "processor": "POWER10", "url": "https://www.ibm.com/docs/en/announcements/power-l1022-9786-22h"},
            # POWER9
            {"mtm": "9080-M9S", "model": "E980", "name": "IBM Power System E980", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s"},
            {"mtm": "9040-MR9", "model": "E950", "name": "IBM Power System E950", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-e950-9040-mr9"},
            {"mtm": "9009-42A", "model": "S924", "name": "IBM Power System S924", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42a"},
            {"mtm": "9009-42G", "model": "S924-G", "name": "IBM Power System S924", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42g"},
            {"mtm": "9009-22A", "model": "S922", "name": "IBM Power System S922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22a"},
            {"mtm": "9009-22G", "model": "S922-G", "name": "IBM Power System S922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22g"},
            {"mtm": "9009-41A", "model": "S914", "name": "IBM Power System S914", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41a"},
            {"mtm": "9009-41G", "model": "S914-G", "name": "IBM Power System S914", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41g-2023-10-24"},
            {"mtm": "9223-42S", "model": "H924", "name": "IBM Power System H924", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-h924-9223-42s-2023-10-24"},
            {"mtm": "9223-22S", "model": "H922", "name": "IBM Power System H922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-h922-9223-22s-2023-10-24"},
            {"mtm": "9183-22X", "model": "IC922", "name": "IBM Power System IC922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-ic922-9183-22x-2021-12-14"},
            {"mtm": "9008-22L", "model": "L922", "name": "IBM Power System L922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-l922-9008-22l"},
            {"mtm": "9006-22P", "model": "LC922", "name": "IBM Power System LC922", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-system-lc922-9006-22p"},
            {"mtm": "9006-12P", "model": "LC921", "name": "IBM Power System LC921", "processor": "POWER9", "url": "https://www.ibm.com/docs/en/announcements/power-systems-lc921-9006-12p"}
        ]
        
        # Initialize state
        bulk_ingestion_state['in_progress'] = True
        bulk_ingestion_state['current_server'] = None
        bulk_ingestion_state['completed'] = []
        bulk_ingestion_state['failed'] = []
        bulk_ingestion_state['total'] = len(servers)
        bulk_ingestion_state['started_at'] = datetime.now().isoformat()
        
        # Start background thread to process servers
        def process_servers():
            for server in servers:
                try:
                    bulk_ingestion_state['current_server'] = f"{server['model']} ({server['mtm']})"
                    logger.info(f"[Bulk Ingestion] Processing MTM {server['mtm']} - {server['model']}")
                    
                    # Call the ingest-sales-manual endpoint internally with MTM-based parameters
                    with app.test_request_context(
                        '/api/ingest-sales-manual',
                        method='POST',
                        json={
                            'mtm': server['mtm'],
                            'server_model': server['model'],
                            'server_name': server['name'],
                            'processor': server['processor'],
                            'url': server['url']
                        }
                    ):
                        response = ingest_sales_manual()
                        if isinstance(response, tuple):
                            response_data, status_code = response
                        else:
                            response_data = response
                            status_code = 200
                        
                        if status_code == 200:
                            bulk_ingestion_state['completed'].append(server['model'])
                            logger.info(f"[Bulk Ingestion] ✓ {server['model']} completed")
                        else:
                            bulk_ingestion_state['failed'].append(server['model'])
                            logger.error(f"[Bulk Ingestion] ✗ {server['model']} failed")
                            
                except Exception as e:
                    bulk_ingestion_state['failed'].append(server['model'])
                    logger.error(f"[Bulk Ingestion] Error processing {server['model']}: {e}")
            
            # Mark as complete
            bulk_ingestion_state['in_progress'] = False
            bulk_ingestion_state['current_server'] = None
            logger.info(f"[Bulk Ingestion] Complete: {len(bulk_ingestion_state['completed'])} succeeded, {len(bulk_ingestion_state['failed'])} failed")
        
        # Start thread
        import threading
        thread = threading.Thread(target=process_servers, daemon=True)
        thread.start()
        
        logger.info(f"Started bulk ingestion of {len(servers)} servers in background thread")
        
        return jsonify({
            'success': True,
            'message': f'Bulk ingestion started for {len(servers)} servers',
            'total': len(servers)
        })
        
    except Exception as e:
        logger.error(f"Error starting bulk ingestion: {e}")
        return jsonify({'error': str(e)}), 500





# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Check OpenSearch
        client = get_opensearch_client()
        client.cluster.health()
        opensearch_status = "connected"
    except Exception as e:
        logger.error(f"OpenSearch health check failed: {e}")
        opensearch_status = "disconnected"
    
    # Check LLM service
    try:
        llm_url = f"http://{LLAMA_HOST}:{LLAMA_PORT}/health"
        response = requests.get(llm_url, timeout=5)
        llm_status = "connected" if response.status_code == 200 else "disconnected"
    except:
        llm_status = "disconnected"
    
    overall_status = "healthy" if opensearch_status == "connected" else "degraded"
    
    return jsonify({
        'status': overall_status,
        'opensearch': opensearch_status,
        'llm': llm_status
    }), 200 if overall_status == "healthy" else 503

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.route('/', methods=['GET'])
def root():
    """API documentation"""
    return jsonify({
        'service': 'RAG Backend with OpenSearch',
        'version': '3.1.0',
        'endpoints': {
            'collections': {
                'GET /api/collections': 'List all collections',
                'DELETE /api/collections/<name>': 'Drop a collection'
            },
            'documents': {
                'POST /api/load-pdf': 'Load PDF into vector database',
                'POST /ingest-scraped-content': 'Ingest scraped content from Windows scraper',
                'POST /api/search': 'Search for relevant documents'
            },
            'generation': {
                'POST /api/generate': 'Generate LLM response'
            },
            'health': {
                'GET /health': 'Health check'
            }
        }
    })

if __name__ == '__main__':
    # Create PDF directory if it doesn't exist
    os.makedirs(PDF_DIR, exist_ok=True)
    
    logger.info(f"OpenSearch host: {OPENSEARCH_HOST}:{OPENSEARCH_PORT}")
    logger.info(f"PDF directory: {PDF_DIR}")
    logger.info(f"Docling enabled: {USE_DOCLING}")
    logger.info(f"Docling config: {docling_config_dict()}")
    logger.info("Starting RAG Backend with OpenSearch...")
    
    app.run(host='0.0.0.0', port=8080, debug=False)

# Made with Bob
