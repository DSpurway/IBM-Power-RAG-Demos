"""
Consolidated RAG Backend Service with OpenSearch
Adapted from IBM project-ai-services implementation
Enhanced with hybrid query routing and reranking
"""

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import os
import re
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
from activation_feature_service import ActivationFeatureService
from physical_feature_service import PhysicalFeatureService

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
# Three LLM backends run side-by-side for comparison:
#   granite   — llama.cpp server, POST /completion          (port 8080)
#   tinyllama — llama.cpp server, POST /completion          (port 8080)
#   vllm      — vLLM/OpenAI-compatible, POST /v1/chat/completions (port 8000)
#   ollama    — Ollama/OpenAI-compatible, POST /v1/chat/completions (port 11434)

GRANITE_HOST = os.environ.get('GRANITE_HOST', os.environ.get('LLAMA_HOST', 'granite-service'))
GRANITE_PORT = os.environ.get('GRANITE_PORT', os.environ.get('LLAMA_PORT', '8080'))

# TinyLlama (Part 1 - demonstrates hallucinations) — llama.cpp format
TINYLLAMA_HOST = os.environ.get('TINYLLAMA_HOST', 'llama-service')
TINYLLAMA_PORT = os.environ.get('TINYLLAMA_PORT', '8080')

# vLLM service — OpenAI-compatible API on port 8000
# Deploy alongside granite/tinyllama for performance comparison
VLLM_HOST = os.environ.get('VLLM_HOST', 'vllm-service')
VLLM_PORT = os.environ.get('VLLM_PORT', '8000')

# Ollama service — OpenAI-compatible API on port 11434
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'ollama-service')
OLLAMA_PORT = os.environ.get('OLLAMA_PORT', '11434')

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
    """Lazy load table lookup service with OpenSearch backend"""
    global _table_lookup_service
    if _table_lookup_service is None:
        logger.info("Initializing table lookup service with OpenSearch")
        client = get_opensearch_client()
        embeddings = get_embeddings()
        _table_lookup_service = TableLookupService(
            opensearch_client=client,
            embeddings=embeddings,
            index_prefix=OPENSEARCH_DB_PREFIX
        )
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
    """List all collections (OpenSearch indices) with MTM-based reverse mapping and document counts"""
    try:
        client = get_opensearch_client()
        
        # Get all indices - try with and without prefix
        try:
            indices = client.indices.get(index=f"{OPENSEARCH_DB_PREFIX}_*")
            logger.info(f"Found {len(indices)} indices with prefix '{OPENSEARCH_DB_PREFIX}_*'")
        except Exception as e:
            logger.warning(f"No indices found with prefix '{OPENSEARCH_DB_PREFIX}_*': {e}")
            # Try getting all indices
            try:
                indices = client.indices.get(index="*")
                logger.info(f"Found {len(indices)} total indices (no prefix filter)")
            except Exception as e2:
                logger.error(f"Failed to get any indices: {e2}")
                indices = {}
        
        # Build a reverse mapping: try to match hashed index names to known MTM-based collection names
        # For IBM Power servers, collection names are based on MTM: mtm_9080_heu, mtm_9009_42a, etc.
        # Note: This excludes other collections like Harry Potter which are used in other parts of the demo
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
        collections_details = {}
        index_names = list(indices.keys())
        
        logger.info(f"All index names found: {index_names}")
        
        # Build a map of all possible collection names to their expected hashed index names
        mtm_to_expected_index = {}
        for mtm in known_mtms:
            collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{mtm.lower().replace('-', '_')}"
            expected_index = _generate_index_name(collection_name)
            mtm_to_expected_index[mtm] = {
                'collection_name': collection_name,
                'expected_index': expected_index
            }
        
        logger.info(f"Expected index mappings: {mtm_to_expected_index}")
        
        # Filter out non-Sales Manual collections (like Harry Potter)
        # Only process MTM-based collections for Sales Manual servers
        sales_manual_indices = []
        other_indices = []
        
        for index_name in index_names:
            # Check if this is a Sales Manual MTM-based index
            is_sales_manual = False
            matched_mtm = None
            
            for mtm, mapping in mtm_to_expected_index.items():
                if index_name == mapping['expected_index']:
                    is_sales_manual = True
                    matched_mtm = mtm
                    break
            
            if is_sales_manual:
                sales_manual_indices.append(index_name)
                logger.info(f"Index {index_name} matched to MTM {matched_mtm}")
            else:
                other_indices.append(index_name)
                logger.info(f"Index {index_name} is not a Sales Manual index")
        
        logger.info(f"Found {len(sales_manual_indices)} Sales Manual indices and {len(other_indices)} other indices")
        
        # Try to match each known MTM to its hashed index and get document count
        for mtm in known_mtms:
            mapping = mtm_to_expected_index[mtm]
            collection_name = mapping['collection_name']
            expected_index = mapping['expected_index']
            
            logger.info(f"Checking MTM {mtm}: collection={collection_name}, expected_index={expected_index}, exists={expected_index in index_names}")
            
            if expected_index in index_names:
                # Get document count for this index
                try:
                    count_response = client.count(index=expected_index)
                    doc_count = count_response.get('count', 0)
                    
                    logger.info(f"MTM {mtm} index {expected_index} has {doc_count} documents")
                    
                    # Include even if it has 0 documents (to show it exists but is empty)
                    collections_map[mtm] = expected_index
                    collections_details[mtm] = {
                        'index_name': expected_index,
                        'document_count': doc_count,
                        'collection_name': collection_name
                    }
                    
                    if doc_count > 0:
                        logger.info(f"✓ Found indexed MTM {mtm}: {doc_count} documents in {expected_index}")
                    else:
                        logger.warning(f"⚠ MTM {mtm} index exists but has 0 documents: {expected_index}")
                        
                except Exception as count_error:
                    logger.error(f"Error getting count for {mtm} ({expected_index}): {count_error}")
            else:
                logger.info(f"✗ MTM {mtm} not found (expected index: {expected_index})")
        
        logger.info(f"Final result: {len(collections_map)} MTMs found with indices")
        logger.info(f"MTMs with documents: {[mtm for mtm, details in collections_details.items() if details['document_count'] > 0]}")
        
        return jsonify({
            'success': True,
            'collections': index_names,  # All indices (including Harry Potter) for backward compatibility
            'sales_manual_collections': sales_manual_indices,  # Only Sales Manual indices
            'other_collections': other_indices,  # Other collections (Harry Potter, etc.)
            'collections_map': collections_map,  # MTM -> index_name mapping (Sales Manual only)
            'collections_details': collections_details,  # MTM -> detailed info including doc count (Sales Manual only)
            'debug_info': {
                'opensearch_prefix': OPENSEARCH_DB_PREFIX,
                'total_indices': len(index_names),
                'expected_mappings_sample': {k: v for k, v in list(mtm_to_expected_index.items())[:3]}
            }
        })
    except Exception as e:
        logger.error(f"Error listing collections: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'collections': [], 'collections_map': {}, 'collections_details': {}}), 500

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
        
        # Determine if this is a simple collection (like Harry Potter) or complex (sales manuals)
        # Check if collection is in the sales manual collections by checking if it's in the MTM mapping
        is_sales_manual_collection = False
        
        # Method 1: Check if it's in the known MTM format (starts with rag_ and is a hash)
        if collection_name.startswith('rag_') and len(collection_name) > 10:
            # This is likely a sales manual collection (hashed format)
            is_sales_manual_collection = True
            logger.info(f"Detected sales manual collection (hashed format): {collection_name}")
        # Method 2: Check for explicit sales_manual or ibm_power_ prefix
        elif 'sales_manual' in collection_name.lower() or collection_name.startswith('ibm_power_'):
            is_sales_manual_collection = True
            logger.info(f"Detected sales manual collection (named format): {collection_name}")
        
        # Step 1: Classify the query and extract entities (only for sales manual collections)
        classification = None
        if is_sales_manual_collection:
            classifier = get_query_classifier()
            classification = classifier.get_query_intent(question)
            
            logger.info(f"Query classified as: {classification['query_type']}")
            logger.info(f"Entities: server_model={classification.get('server_model')}, mtm={classification.get('mtm')}, lifecycle_field={classification.get('lifecycle_field')}")
        else:
            # Simple collection - skip classification, use basic RAG
            logger.info(f"Simple collection detected, skipping classification")
            classification = {
                'query_type': 'rag',
                'original_query': question,
                'server_model': None,
                'mtm': None,
                'feature_code': None,
                'lifecycle_field': None
            }
            # Use dense search by default for simple collections (more reliable)
            if mode == 'hybrid':
                mode = 'dense'
                logger.info(f"Switching to dense mode for simple collection")
        
        # Step 2: Route based on classification
        if classification['query_type'] == 'table_lookup':
            # Direct table lookup from OpenSearch - no LLM generation needed
            server_model = classification.get('server_model')
            
            if not server_model:
                return jsonify({
                    'success': False,
                    'error': 'Could not identify server model in query',
                    'query_type': 'table_lookup',
                    'classification': classification
                }), 400
            
            table_service = get_table_lookup_service()
            result = table_service.lookup(
                server_model=server_model,
                field=classification.get('lifecycle_field'),
                collection_name=collection_name,
                server_mtm=classification.get('mtm')
            )
            
            if not result.get('success'):
                # If lookup fails, return error
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Table lookup failed'),
                    'query_type': 'table_lookup',
                    'classification': classification
                }), 404
            
            return jsonify({
                'success': True,
                'query_type': 'table_lookup',
                'results': [{
                    'content': result['answer'],
                    'table_data': result.get('table_data'),  # Raw table text for display
                    'metadata': {
                        'source': result.get('source', 'sales_manual'),
                        'source_url': result.get('source_url'),  # Link to sales manual
                        'source_filename': result.get('source_filename'),
                        'server_model': result.get('server_model'),
                        'mtm': result.get('mtm'),
                        'field': result.get('field'),
                        'chunks_found': result.get('chunks_found', 0)
                    },
                    'score': 1.0
                }],
                'count': 1,
                'classification': classification,
                'table_lookup': True  # Flag to indicate this is a direct table lookup
            })
        
        elif classification['query_type'] == 'activation_lookup':
            # Activation feature lookup - vector search + structured extraction
            logger.info("Processing activation feature query")
            
            # Use vector search to find activation-related chunks
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({'error': f'Collection {collection_name} does not exist'}), 404
            
            # Generate query embedding
            query_vector = embeddings.embed_query(question)
            
            # Search for activation-related chunks (get more candidates)
            search_body = {
                "size": 20,  # Get more chunks to find all activation features
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_vector,
                                        "k": 20
                                    }
                                }
                            }
                        ],
                        "should": [
                            {"match": {"text": "activation"}},
                            {"match": {"text": "activations"}},
                            {"match": {"text": "memory activation"}},
                            {"match": {"text": "processor activation"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Found {len(hits)} potential activation chunks")
            
            # Extract activation features from chunks
            # Process one feature description at a time to avoid repeated Granite timeouts
            activation_service = ActivationFeatureService(max_llm_calls=1)
            chunks = [{'text': hit['_source']['text'], 'metadata': hit['_source'].get('metadata', {})}
                     for hit in hits]
            
            features = activation_service.extract_features_from_chunks(chunks)
            
            if not features:
                # Provide context-aware response based on server type
                server_model = classification.get('server_model', 'unknown')
                is_small_system = server_model and (
                    server_model.startswith('S10') or
                    server_model.startswith('L10') or
                    server_model.startswith('S9') and len(server_model) == 4
                )
                
                if is_small_system:
                    answer = (
                        f"The IBM Power {server_model} is a scale-out system with fixed processor and memory configurations. "
                        f"These systems typically do not offer processor or memory activation features. "
                        f"All processors and memory are included in the base configuration."
                    )
                else:
                    answer = (
                        f"I couldn't find any activation features in the sales manual for the IBM Power {server_model}. "
                        f"This could mean this model doesn't support processor/memory activations, or the data needs to be re-ingested."
                    )
                
                return jsonify({
                    'success': True,
                    'query_type': 'activation_lookup',
                    'answer': answer,
                    'features': [],
                    'summary': {
                        'total': 0,
                        'available': 0,
                        'discontinued': 0
                    },
                    'results': [{
                        'content': answer,
                        'metadata': {
                            'source': 'sales_manual',
                            'total_features': 0,
                            'available_features': 0,
                            'discontinued_features': 0
                        },
                        'score': 1.0
                    }],
                    'count': 0,
                    'classification': classification,
                    'activation_lookup': True,
                    'chunks_searched': len(hits)
                })
            
            # Format the results
            summary = activation_service.format_activation_summary(features, question)
            answer = activation_service.generate_activation_answer(features, question)
            
            # Extract source URL from chunk metadata (if available)
            source_url = None
            source_filename = None
            for hit in hits:
                metadata = hit['_source'].get('metadata', {})
                if metadata.get('source'):
                    source_url = metadata['source']
                    source_filename = metadata.get('filename') or metadata.get('source_filename')
                    break  # Use first available source
            
            # Build metadata with source information
            result_metadata = {
                'source': 'sales_manual',
                'total_features': len(features),
                'available_features': summary['summary']['available'],
                'discontinued_features': summary['summary']['discontinued']
            }
            
            if source_url:
                result_metadata['source_url'] = source_url
                logger.info(f"Including source URL in activation response: {source_url}")
            if source_filename:
                result_metadata['source_filename'] = source_filename
            
            return jsonify({
                'success': True,
                'query_type': 'activation_lookup',
                'answer': answer,
                'features': summary['features'],
                'categories': summary['categories'],
                'summary': summary['summary'],
                'results': [{
                    'content': answer,
                    'metadata': result_metadata,
                    'score': 1.0
                }],
                'count': len(features),
                'classification': classification,
                'activation_lookup': True
            })
        
        elif classification['query_type'] == 'physical_feature_lookup':
            # Physical feature lookup (processors, memory - non-activation)
            logger.info("Processing physical feature query")
            
            # Use vector search to find physical feature chunks
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({'error': f'Collection {collection_name} does not exist'}), 404
            
            # Generate query embedding
            query_vector = embeddings.embed_query(question)
            
            # Search for physical feature chunks (exclude activation keywords)
            search_body = {
                "size": 20,
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_vector,
                                        "k": 20
                                    }
                                }
                            }
                        ],
                        "should": [
                            {"match": {"text": "processor"}},
                            {"match": {"text": "memory"}},
                            {"match": {"text": "core"}},
                            {"match": {"text": "GB"}}
                        ],
                        "must_not": [
                            {"match": {"text": "activation"}},
                            {"match": {"text": "activations"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Found {len(hits)} potential physical feature chunks")
            
            # Extract physical features from chunks
            physical_service = PhysicalFeatureService()
            chunks = [{'text': hit['_source']['text'], 'metadata': hit['_source'].get('metadata', {})}
                     for hit in hits]
            
            features = physical_service.extract_features_from_chunks(chunks)
            
            if not features:
                server_model = classification.get('server_model', 'unknown')
                answer = (
                    f"I couldn't find any physical processor or memory features in the sales manual for the IBM Power {server_model}. "
                    f"This could mean the data needs to be re-ingested or the features are documented differently."
                )
                
                return jsonify({
                    'success': True,
                    'query_type': 'physical_feature_lookup',
                    'answer': answer,
                    'features': [],
                    'results': [{
                        'content': answer,
                        'metadata': {'source': 'sales_manual', 'total_features': 0},
                        'score': 1.0
                    }],
                    'count': 0,
                    'classification': classification,
                    'physical_feature_lookup': True
                })
            
            # Generate answer
            answer = physical_service.generate_physical_feature_answer(features, question)
            
            # Extract source URL
            source_url = None
            source_filename = None
            for hit in hits:
                metadata = hit['_source'].get('metadata', {})
                if metadata.get('source'):
                    source_url = metadata['source']
                    source_filename = metadata.get('filename') or metadata.get('source_filename')
                    break
            
            result_metadata = {
                'source': 'sales_manual',
                'total_features': len(features),
                'available_features': len([f for f in features if f.is_available]),
                'discontinued_features': len([f for f in features if not f.is_available])
            }
            
            if source_url:
                result_metadata['source_url'] = source_url
            if source_filename:
                result_metadata['source_filename'] = source_filename
            
            return jsonify({
                'success': True,
                'query_type': 'physical_feature_lookup',
                'answer': answer,
                'features': [f.to_dict() for f in features],
                'results': [{
                    'content': answer,
                    'metadata': result_metadata,
                    'score': 1.0
                }],
                'count': len(features),
                'classification': classification,
                'physical_feature_lookup': True
            })
        
        elif classification['query_type'] == 'metadata_lookup':
            # Metadata-based search (e.g., feature codes, withdrawal dates)
            # Use OpenSearch metadata filters
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({'error': f'Collection {collection_name} does not exist'}), 404
            
            # Build metadata query
            must_clauses = [{"match": {"text": question}}]
            
            # Add entity filters if available
            if classification.get('server_model'):
                must_clauses.append({
                    "match": {"metadata.server_model": classification['server_model']}
                })
            
            if classification.get('feature_code'):
                must_clauses.append({
                    "match": {"metadata.feature_codes": classification['feature_code']}
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
            
            # Execute search with fallback to dense if hybrid fails
            try:
                params = {"search_pipeline": "hybrid_pipeline"} if mode == "hybrid" else {}
                response = client.search(index=index_name, body=search_body, params=params)
                hits = response['hits']['hits']
                logger.info(f"{mode.upper()} search found {len(hits)} results")
            except Exception as search_error:
                if mode == "hybrid":
                    # Hybrid search failed, fall back to dense search
                    logger.warning(f"Hybrid search failed: {search_error}. Falling back to dense search.")
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
                    response = client.search(index=index_name, body=search_body)
                    hits = response['hits']['hits']
                    logger.info(f"Dense fallback search found {len(hits)} results")
                else:
                    # Re-raise if not hybrid mode
                    raise
        
        # Step 3: Apply reranking if enabled and we have RAG/metadata results
        if use_reranking and classification['query_type'] != 'table_lookup' and len(hits) > 0:
            reranker = get_reranker_service()
            
            # Prepare chunks for reranking (reranker expects list of dicts with 'text' field)
            chunks = [{"text": hit["_source"].get("text", ""), "hit": hit} for hit in hits]
            
            # Rerank - returns reranked chunks
            reranked_chunks = reranker.rerank(question, chunks, top_k=k)
            
            # Extract the original hits from reranked chunks
            reranked_hits = [chunk["hit"] for chunk in reranked_chunks]
            
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
                'reranked': use_reranking and classification['query_type'] != 'table_lookup'
            }
            formatted_results.append(result)
        
        return jsonify({
            'success': True,
            'query_type': classification['query_type'],
            'results': formatted_results,
            'count': len(formatted_results),
            'classification': classification,
            'reranking_applied': use_reranking and classification['query_type'] != 'table_lookup'
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
    Ingest scraped content with smart hierarchical chunking
    Preserves table structure and creates semantic chunks for hybrid query system
    """
    try:
        from sales_manual_chunker import SalesManualChunker
        
        data = request.get_json()
        
        if not data or not data.get('success'):
            return jsonify({'error': 'Invalid scraped data'}), 400
        
        url = data.get('url', 'unknown')
        page_title = data.get('page_title', 'Untitled')
        full_text = data.get('full_text', '')
        sections = data.get('sections', [])  # Get structured sections
        server_model = data.get('server_model', None)
        mtm = data.get('mtm', None)
        
        if not full_text:
            return jsonify({'error': 'No content found in scraped data'}), 400
        
        logger.info(f"Ingesting scraped content from: {url}")
        logger.info(f"Server: {page_title}, MTM: {mtm}, Full text length: {len(full_text)} characters")
        logger.info(f"Structured sections available: {len(sections)}")
        
        # Create collection name based on MTM
        if mtm:
            collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{mtm.lower().replace('-', '_')}"
            logger.info(f"Using MTM-based collection: {collection_name}")
        elif server_model:
            collection_name = f"{OPENSEARCH_DB_PREFIX}_power_{server_model.lower().replace('-', '_')}"
            logger.info(f"Using server-specific collection: {collection_name}")
        else:
            collection_name = f"{OPENSEARCH_DB_PREFIX}_ibm_docs"
            logger.warning(f"No MTM/server_model provided, using generic collection: {collection_name}")
        
        # Initialize smart chunker
        chunker = SalesManualChunker(max_chunk_size=1500, overlap=100)
        
        # Apply smart hierarchical chunking with structured sections
        chunks = chunker.chunk_sales_manual(
            full_text=full_text,
            server_name=page_title,
            mtm=mtm or server_model or 'unknown',
            url=url,
            sections=sections  # Pass structured sections
        )
        
        logger.info(f"Smart chunking created {len(chunks)} chunks")
        
        # Log chunk distribution by type
        chunk_types = {}
        for chunk in chunks:
            chunk_type = chunk['metadata']['section_type']
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        logger.info(f"Chunk distribution: {chunk_types}")
        
        # Initialize OpenSearch and embeddings
        client = get_opensearch_client()
        embeddings = get_embeddings()
        
        # Generate index name and create if needed
        index_name = _generate_index_name(collection_name)
        _setup_index(index_name, embeddings.client.get_sentence_embedding_dimension())
        
        # Index chunks
        indexed_count = 0
        failed_count = 0
        
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding = embeddings.embed_query(chunk['text'])
                
                # Create document ID
                doc_id = hashlib.md5(
                    f"{chunk['metadata']['source']}_{chunk['metadata']['section_title']}_{i}".encode()
                ).hexdigest()
                
                # Index document
                client.index(
                    index=index_name,
                    id=doc_id,
                    body={
                        'text': chunk['text'],
                        'embedding': embedding,
                        'metadata': chunk['metadata']
                    }
                )
                indexed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to index chunk {i}: {e}")
                failed_count += 1
        
        # Refresh index
        client.indices.refresh(index=index_name)
        
        logger.info(f"Ingestion complete: {indexed_count} indexed, {failed_count} failed")
        
        return jsonify({
            'success': True,
            'collection': collection_name,
            'indexed': indexed_count,
            'failed': failed_count,
            'chunk_distribution': chunk_types,
            'page_title': page_title,
            'source_url': url,
            'mtm': mtm
        })
        
    except Exception as e:
        logger.error(f"Error ingesting scraped content: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


# ============================================================================
# LLM GENERATION ENDPOINT
# ============================================================================

@app.route('/api/generate', methods=['POST'])
def generate():
    """
    Generate response with intelligent query routing
    - Table lookup queries: Fast response from structured data (no LLM)
    - Regular queries: Full RAG with LLM
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        temperature = data.get('temperature', 0.1)
        n_predict = data.get('n_predict', 256)
        stream = data.get('stream', False)
        model = data.get('model', 'granite')  # 'granite' or 'tinyllama'
        
        # Get clarification parameters from UI
        server_mtm_override = data.get('server_mtm')  # MTM selected by user (e.g., "9009-42A")
        server_model_override = data.get('server_model')  # Server model selected by user (e.g., "S924")
        lifecycle_field_override = data.get('lifecycle_field')  # Lifecycle field selected by user
        
        if not prompt:
            return jsonify({'error': 'prompt is required'}), 400
        
        logger.info(f"Processing query: {prompt[:100]}...")
        if server_mtm_override:
            logger.info(f"User selected MTM: {server_mtm_override}")
        if server_model_override:
            logger.info(f"User selected server model: {server_model_override}")
        if lifecycle_field_override:
            logger.info(f"User selected lifecycle field: {lifecycle_field_override}")
        
        # Step 1: Classify the query to determine if it's a table lookup
        classifier = get_query_classifier()
        query_intent = classifier.get_query_intent(prompt)
        query_type = query_intent['query_type']
        
        # Override query intent with user selections if provided
        if server_mtm_override:
            # Convert MTM to server model (e.g., "9009-42A" -> "S924")
            from server_mtm_mapper import MTM_SERVER_MAP
            server_model = MTM_SERVER_MAP.get(server_mtm_override)
            if server_model:
                query_intent['server_model'] = server_model
                query_intent['mtm'] = server_mtm_override
                query_intent['mtm_options'] = []  # Clear options since user already selected
                logger.info(f"Overriding with user-selected MTM: {server_mtm_override} -> {server_model}")
        
        if server_model_override:
            query_intent['server_model'] = server_model_override
            logger.info(f"Overriding with user-selected server model: {server_model_override}")
        
        if lifecycle_field_override:
            query_intent['lifecycle_field'] = lifecycle_field_override
            logger.info(f"Overriding with user-selected lifecycle field: {lifecycle_field_override}")
        
        logger.info(f"Query classified as: {query_type}")
        
        # Step 2: Handle table lookup queries without LLM
        if query_type == 'table_lookup':
            logger.info("Handling as table lookup query (no LLM needed)")
            table_service = get_table_lookup_service()
            
            server_model = query_intent.get('server_model')
            lifecycle_field = query_intent.get('lifecycle_field')
            mtm_options = query_intent.get('mtm_options', [])
            
            # Check if Watson is asking for MTM clarification (A vs G model, etc.)
            if mtm_options:
                logger.info(f"Watson requesting MTM clarification for {server_model}: {len(mtm_options)} options")
                return jsonify({
                    'success': True,
                    'content': f"I found multiple variants of the IBM Power {server_model}. Which one are you interested in?",
                    'query_type': 'mtm_clarification_needed',
                    'server_model': server_model,
                    'clarification_options': [
                        {'label': opt['label'], 'value': opt['mtm']}
                        for opt in mtm_options
                    ],
                    'ai_services_used': ['watsonx_assistant'],
                    'processing_method': 'nlp_intent_detection'
                })
            
            if not server_model:
                # Watson detected lifecycle query but couldn't identify the server
                # Ask user to clarify which server they're asking about
                logger.info("Check_Date intent detected but no server model - requesting clarification")
                
                # Get list of available servers from our known MTM map
                from server_mtm_mapper import SERVER_MTM_MAP
                
                # Group by processor generation for better UX
                power11_servers = [(model, mtm) for model, mtm in SERVER_MTM_MAP.items() if model.startswith(('E11', 'S11'))]
                power10_servers = [(model, mtm) for model, mtm in SERVER_MTM_MAP.items() if model.startswith(('E10', 'S10', 'L10'))]
                power9_servers = [(model, mtm) for model, mtm in SERVER_MTM_MAP.items() if model.startswith(('E9', 'S9', 'H9', 'IC9', 'L9', 'LC9'))]
                
                clarification_options = []
                
                # Add POWER11 servers
                for model, mtm in sorted(power11_servers):
                    clarification_options.append({
                        'label': f'IBM Power {model} ({mtm})',
                        'value': model,
                        'processor': 'POWER11'
                    })
                
                # Add POWER10 servers
                for model, mtm in sorted(power10_servers):
                    clarification_options.append({
                        'label': f'IBM Power {model} ({mtm})',
                        'value': model,
                        'processor': 'POWER10'
                    })
                
                # Add POWER9 servers
                for model, mtm in sorted(power9_servers):
                    clarification_options.append({
                        'label': f'IBM Power {model} ({mtm})',
                        'value': model,
                        'processor': 'POWER9'
                    })
                
                return jsonify({
                    'success': True,
                    'content': f"I understand you're asking about a lifecycle date, but I couldn't identify which IBM Power server you're referring to. Which server are you interested in?",
                    'query_type': 'server_clarification_needed',
                    'clarification_options': clarification_options,
                    'ai_services_used': ['watsonx_assistant'],
                    'processing_method': 'nlp_intent_detection'
                })
            elif not lifecycle_field:
                # Watson detected Check_Date intent but didn't extract which date field
                # Ask user to clarify which lifecycle date they want
                logger.info(f"Check_Date intent detected for {server_model} but no specific lifecycle field - requesting clarification")
                return jsonify({
                    'success': True,
                    'content': f"I understand you want to check a lifecycle date for the IBM Power {server_model}. Which date would you like to know about?",
                    'query_type': 'lifecycle_clarification_needed',
                    'server_model': server_model,
                    'clarification_options': [
                        {'label': 'Announcement Date', 'value': 'announced'},
                        {'label': 'Availability Date', 'value': 'available'},
                        {'label': 'Marketing Withdrawal Date', 'value': 'withdrawn'},
                        {'label': 'Service Discontinuation Date', 'value': 'end_of_support'},
                        {'label': 'Show All Lifecycle Dates', 'value': 'all'}
                    ],
                    'ai_services_used': ['watsonx_assistant'],
                    'processing_method': 'nlp_intent_detection'
                })
            else:
                # Get MTM for the server model if we have it
                logger.info(f"DEBUG: query_intent keys: {query_intent.keys()}")
                logger.info(f"DEBUG: query_intent['mtm'] = {query_intent.get('mtm')}")
                server_mtm = query_intent.get('mtm')
                logger.info(f"DEBUG: server_mtm after get = {server_mtm}")
                if not server_mtm and server_model:
                    from server_mtm_mapper import get_mtm_for_model
                    server_mtm = get_mtm_for_model(server_model)
                    logger.info(f"DEBUG: server_mtm after lookup = {server_mtm}")
                
                result = table_service.query(
                    query=prompt,
                    server_model=server_model,
                    lifecycle_field=lifecycle_field,
                    server_mtm=server_mtm
                )
                
                if result.get('success'):
                    logger.info(f"Table lookup successful for {server_model}")
                    return jsonify({
                        'success': True,
                        'content': result.get('answer', 'No answer found'),
                        'query_type': 'table_lookup',
                        'server_model': server_model,
                        'field': lifecycle_field,
                        'response_time_ms': result.get('response_time_ms', 10),
                        'chunks_found': result.get('chunks_found', 0),
                        'table_data': result.get('table_data'),
                        'source_url': result.get('source_url'),
                        'source_filename': result.get('source_filename'),
                        'ai_services_used': ['watsonx_assistant', 'opensearch'],
                        'processing_method': 'hybrid_table_lookup'
                    })
                else:
                    logger.warning(f"Table lookup failed: {result.get('error')}")
                    # Fall through to LLM if table lookup fails
        
        # Step 2.5: Handle activation feature queries
        elif query_type == 'activation_lookup':
            logger.info("Handling as activation feature query")
            
            # Get server model from query intent
            server_model = query_intent.get('server_model')
            
            if not server_model:
                return jsonify({
                    'success': False,
                    'error': 'Could not identify server model in query',
                    'query_type': 'activation_lookup',
                    'content': 'I understand you\'re asking about activation features, but I couldn\'t identify which IBM Power server you\'re referring to. Please specify the server model (e.g., E1080, S1024).'
                }), 400
            
            # Determine collection name from server model
            from server_mtm_mapper import get_mtm_for_model
            server_mtm = get_mtm_for_model(server_model)
            
            if server_mtm:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{server_mtm.lower().replace('-', '_')}"
            else:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_power_{server_model.lower()}"
            
            logger.info(f"Looking for activation features in collection: {collection_name}")
            
            # Use vector search to find activation-related chunks
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({
                    'success': False,
                    'error': f'No sales manual data found for {server_model}',
                    'query_type': 'activation_lookup',
                    'content': f'I don\'t have sales manual data for the IBM Power {server_model} yet. Please ensure the sales manual has been ingested.'
                }), 404
            
            # Generate query embedding
            query_vector = embeddings.embed_query(prompt)
            
            # Search for activation-related chunks
            # CRITICAL: Filter by section_type=feature_code to get structured feature descriptions
            # This avoids pulling from summary tables in "Highlights" or "Models" sections
            search_body = {
                "size": 100,  # Increased to get all activation features
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": [
                            # MUST be a feature_code section (from Feature Descriptions)
                            {"term": {"metadata.section_type": "feature_code"}}
                        ],
                        "should": [
                            {"match": {"text": "activation"}},
                            {"match": {"text": "activations"}},
                            {"match": {"text": "memory activation"}},
                            {"match": {"text": "processor activation"}},
                            {"match": {"text": "proc act"}},
                            {"match": {"text": "mem act"}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}}
                ]
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Found {len(hits)} potential activation chunks")
            
            # Get processor and memory feature code lists from "Features - Chargeable" section
            # These lists help us accurately categorize activation features
            category_lists_query = {
                "size": 10,
                "_source": ["text"],
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metadata.section_type": "content_section"}},
                            {"match": {"metadata.section_title": "Features - Chargeable"}}
                        ],
                        "should": [
                            {"match": {"text": "Memory"}},
                            {"match": {"text": "Processor"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            category_response = client.search(index=index_name, body=category_lists_query)
            category_hits = category_response['hits']['hits']
            
            # Extract feature codes from the lists
            processor_codes = set()
            memory_codes = set()
            
            for hit in category_hits:
                text = hit['_source']['text']
                # Find all feature codes in format (#CODE)
                codes = re.findall(r'\(#([A-Z0-9]{4})\)', text)
                
                # Determine if this is a processor or memory list
                text_lower = text.lower()
                if 'processor' in text_lower[:200]:  # Check first 200 chars for section header
                    processor_codes.update(codes)
                    logger.info(f"Found {len(codes)} processor codes in category list")
                elif 'memory' in text_lower[:200]:
                    memory_codes.update(codes)
                    logger.info(f"Found {len(codes)} memory codes in category list")
            
            logger.info(f"Category lists: {len(processor_codes)} processor codes, {len(memory_codes)} memory codes")
            
            # Extract activation features from chunks (no LLM for speed)
            activation_service = ActivationFeatureService(use_llm_descriptions=False, max_llm_calls=0)
            activation_service.processor_codes = processor_codes
            activation_service.memory_codes = memory_codes
            
            chunks = [{'text': hit['_source']['text'], 'metadata': hit['_source'].get('metadata', {})}
                     for hit in hits]
            
            features = activation_service.extract_features_from_chunks(chunks)
            
            if not features:
                # Provide context-aware response based on server type
                # Smaller systems (S/L series without E prefix) typically don't have activations
                is_small_system = server_model and (
                    server_model.startswith('S10') or
                    server_model.startswith('L10') or
                    server_model.startswith('S9') and len(server_model) == 4  # S922, S924, etc.
                )
                
                if is_small_system:
                    content = (
                        f"The IBM Power {server_model} is a scale-out system with fixed processor and memory configurations. "
                        f"These systems typically do not offer processor or memory activation features. "
                        f"All processors and memory are included in the base configuration."
                    )
                else:
                    content = (
                        f"I couldn't find any activation features in the sales manual for the IBM Power {server_model}. "
                        f"This could mean:\n"
                        f"• This model doesn't support processor/memory activations\n"
                        f"• The sales manual data needs to be re-ingested\n"
                        f"• The activation features are documented in a different section"
                    )
                
                return jsonify({
                    'success': True,  # Changed to True since this is valid information
                    'query_type': 'activation_lookup',
                    'content': content,
                    'server_model': server_model,
                    'features': [],
                    'summary': {
                        'total': 0,
                        'available': 0,
                        'discontinued': 0
                    },
                    'chunks_searched': len(hits),
                    'ai_services_used': ['watsonx_assistant', 'opensearch', 'activation_extractor'],
                    'processing_method': 'activation_feature_extraction'
                })
            
            # Generate natural language answer
            answer = activation_service.generate_activation_answer(features, prompt)
            summary = activation_service.format_activation_summary(features, prompt)
            
            # Extract source URL from chunk metadata (if available)
            source_url = None
            source_filename = None
            for hit in hits:
                metadata = hit['_source'].get('metadata', {})
                if metadata.get('source'):
                    source_url = metadata['source']
                    source_filename = metadata.get('filename') or metadata.get('source_filename')
                    break  # Use first available source
            
            # Build response with source information
            response_data = {
                'success': True,
                'content': answer,
                'query_type': 'activation_lookup',
                'server_model': server_model,
                'features': summary['features'],
                'categories': summary['categories'],
                'summary': summary['summary'],
                'chunks_found': len(hits),
                'ai_services_used': ['watsonx_assistant', 'opensearch', 'activation_extractor'],
                'processing_method': 'activation_feature_extraction'
            }
            
            # Add source information if available
            if source_url:
                response_data['source_url'] = source_url
                logger.info(f"Including source URL in activation response: {source_url}")
            if source_filename:
                response_data['source_filename'] = source_filename
            
            return jsonify(response_data)
        
        # Step 2.6: Handle physical feature queries (processors, memory - non-activation)
        elif query_type == 'physical_feature_lookup':
            logger.info("Handling as physical feature query")
            
            # Get server model from query intent
            server_model = query_intent.get('server_model')
            
            if not server_model:
                return jsonify({
                    'success': False,
                    'error': 'Could not identify server model in query',
                    'query_type': 'physical_feature_lookup',
                    'content': 'I understand you\'re asking about physical features, but I couldn\'t identify which IBM Power server you\'re referring to. Please specify the server model.'
                }), 400
            
            # Determine collection name
            from server_mtm_mapper import get_mtm_for_model
            server_mtm = get_mtm_for_model(server_model)
            
            if server_mtm:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{server_mtm.lower().replace('-', '_')}"
            else:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_power_{server_model.lower()}"
            
            logger.info(f"Looking for physical features in collection: {collection_name}")
            
            # Use vector search
            embeddings = get_embeddings()
            client = get_opensearch_client()
            index_name = _generate_index_name(collection_name)
            
            if not client.indices.exists(index=index_name):
                return jsonify({
                    'success': False,
                    'error': f'No sales manual data found for {server_model}',
                    'query_type': 'physical_feature_lookup',
                    'content': f'I don\'t have sales manual data for the IBM Power {server_model} yet.'
                }), 404
            
            # Generate query embedding
            query_vector = embeddings.embed_query(prompt)
            
            # Search for physical feature chunks from Feature Descriptions
            # Filter by section_type=feature_code and exclude activation keywords
            search_body = {
                "size": 100,
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metadata.section_type": "feature_code"}}
                        ],
                        "should": [
                            {"match": {"text": "processor"}},
                            {"match": {"text": "memory"}},
                            {"match": {"text": "core"}},
                            {"match": {"text": "GB"}},
                            {"match": {"text": "CDIMM"}},
                            {"match": {"text": "GHz"}}
                        ],
                        "must_not": [
                            {"match": {"text": "activation"}},
                            {"match": {"text": "activations"}},
                            {"match": {"text": "act "}}
                        ],
                        "minimum_should_match": 1
                    }
                },
                "sort": [
                    {"_score": {"order": "desc"}}
                ]
            }
            
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            
            logger.info(f"Found {len(hits)} potential physical feature chunks")
            
            # Get processor and memory feature code lists from "Features - Chargeable" section
            category_lists_query = {
                "size": 10,
                "_source": ["text"],
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"metadata.section_type": "content_section"}},
                            {"match": {"metadata.section_title": "Features - Chargeable"}}
                        ],
                        "should": [
                            {"match": {"text": "Memory"}},
                            {"match": {"text": "Processor"}}
                        ],
                        "minimum_should_match": 1
                    }
                }
            }
            
            category_response = client.search(index=index_name, body=category_lists_query)
            category_hits = category_response['hits']['hits']
            
            # Extract feature codes from the lists
            processor_codes = set()
            memory_codes = set()
            
            for hit in category_hits:
                text = hit['_source']['text']
                codes = re.findall(r'\(#([A-Z0-9]{4})\)', text)
                
                text_lower = text.lower()
                if 'processor' in text_lower[:200]:
                    processor_codes.update(codes)
                    logger.info(f"Found {len(codes)} processor codes in category list")
                elif 'memory' in text_lower[:200]:
                    memory_codes.update(codes)
                    logger.info(f"Found {len(codes)} memory codes in category list")
            
            logger.info(f"Category lists: {len(processor_codes)} processor codes, {len(memory_codes)} memory codes")
            
            # Extract physical features
            physical_service = PhysicalFeatureService()
            physical_service.processor_codes = processor_codes
            physical_service.memory_codes = memory_codes
            
            chunks = [{'text': hit['_source']['text'], 'metadata': hit['_source'].get('metadata', {})}
                     for hit in hits]
            
            features = physical_service.extract_features_from_chunks(chunks)
            
            if not features:
                return jsonify({
                    'success': True,
                    'content': f'I couldn\'t find any physical processor or memory features in the sales manual for the IBM Power {server_model}.',
                    'query_type': 'physical_feature_lookup',
                    'server_model': server_model,
                    'features': [],
                    'chunks_found': len(hits),
                    'ai_services_used': ['watsonx_assistant', 'opensearch', 'physical_feature_extractor'],
                    'processing_method': 'physical_feature_extraction'
                })
            
            # Generate answer
            answer = physical_service.generate_physical_feature_answer(features, prompt)
            
            # Extract source URL
            source_url = None
            source_filename = None
            for hit in hits:
                metadata = hit['_source'].get('metadata', {})
                if metadata.get('source'):
                    source_url = metadata['source']
                    source_filename = metadata.get('filename') or metadata.get('source_filename')
                    break
            
            response_data = {
                'success': True,
                'content': answer,
                'query_type': 'physical_feature_lookup',
                'server_model': server_model,
                'features': [f.to_dict() for f in features],
                'chunks_found': len(hits),
                'ai_services_used': ['watsonx_assistant', 'opensearch', 'physical_feature_extractor'],
                'processing_method': 'physical_feature_extraction'
            }
            
            if source_url:
                response_data['source_url'] = source_url
                logger.info(f"Including source URL in physical feature response: {source_url}")
            if source_filename:
                response_data['source_filename'] = source_filename
            
            return jsonify(response_data)
        
        # Step 3: For general RAG queries, retrieve relevant chunks first
        logger.info(f"Using full RAG pipeline for query (type: {query_type})")
        
        # Step 3.1: Determine collection name from query intent
        server_model = query_intent.get('server_model')
        collection_name = None
        
        if server_model:
            # Get MTM for the server model
            from server_mtm_mapper import get_mtm_for_model
            server_mtm = get_mtm_for_model(server_model)
            
            if server_mtm:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{server_mtm.lower().replace('-', '_')}"
                logger.info(f"Using collection for {server_model} ({server_mtm}): {collection_name}")
            else:
                collection_name = f"{OPENSEARCH_DB_PREFIX}_power_{server_model.lower()}"
                logger.info(f"Using generic collection for {server_model}: {collection_name}")
        else:
            # No server identified - ask user to specify
            return jsonify({
                'success': False,
                'error': 'Could not identify which server you are asking about',
                'content': 'I understand your question, but I need to know which IBM Power server you\'re asking about. Please specify the server model (e.g., E1080, S924, S1024).',
                'query_type': 'server_clarification_needed',
                'ai_services_used': ['watsonx_assistant'],
                'processing_method': 'nlp_intent_detection'
            }), 400
        
        # Step 3.2: Retrieve relevant chunks from OpenSearch
        embeddings = get_embeddings()
        client = get_opensearch_client()
        index_name = _generate_index_name(collection_name)
        
        if not client.indices.exists(index=index_name):
            return jsonify({
                'success': False,
                'error': f'No sales manual data found for {server_model}',
                'content': f'I don\'t have sales manual data for the IBM Power {server_model} yet. Please ensure the sales manual has been ingested.',
                'query_type': query_type,
                'ai_services_used': ['watsonx_assistant', 'opensearch'],
                'processing_method': 'rag_retrieval_failed'
            }), 404
        
        # Strip server/MTM tokens from the search query before hitting OpenSearch.
        # server_model and server_mtm are already resolved — they selected this
        # collection. Leaving them in the embedding/BM25 query dilutes the actual
        # topic signal (e.g. feature code #0010, memory, processor).
        # We strip the known exact values plus common surrounding phrases.
        strip_terms = []
        if server_mtm:
            strip_terms.append(re.escape(server_mtm))           # 9080-M9S
        if server_model:
            strip_terms.append(re.escape(server_model))         # E980
        # Also strip "IBM Power System", "IBM Power", "Power System" wrappers
        strip_terms += [
            r'IBM\s+Power\s+System',
            r'IBM\s+Power',
            r'Power\s+System',
        ]
        search_prompt = prompt
        for term in strip_terms:
            search_prompt = re.sub(term, '', search_prompt, flags=re.IGNORECASE)
        # Collapse multiple spaces left by stripping
        search_prompt = re.sub(r'\s{2,}', ' ', search_prompt).strip()
        logger.info(f"RAG search prompt (stripped): '{search_prompt}' (original: '{prompt[:80]}')")

        # Generate query embedding
        query_vector = embeddings.embed_query(search_prompt)

        # Retrieve chunks using hybrid search (with fallback to dense)
        k = 3  # Number of chunks to retrieve (reduced for faster LLM response)
        try:
            search_body = {
                "size": k * 2,  # Get more for potential reranking
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "hybrid": {
                        "queries": [
                            {
                                "knn": {
                                    "embedding": {
                                        "vector": query_vector,
                                        "k": k * 2
                                    }
                                }
                            },
                            {
                                "match": {"text": search_prompt}
                            }
                        ]
                    }
                }
            }
            
            response = client.search(index=index_name, body=search_body, params={"search_pipeline": "hybrid_pipeline"})
            hits = response['hits']['hits']
            logger.info(f"Hybrid search found {len(hits)} chunks")
        except Exception as search_error:
            # Fallback to dense search
            logger.warning(f"Hybrid search failed: {search_error}. Falling back to dense search.")
            search_body = {
                "size": k * 2,
                "_source": ["chunk_id", "text", "metadata"],
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": query_vector,
                            "k": k * 2
                        }
                    }
                }
            }
            response = client.search(index=index_name, body=search_body)
            hits = response['hits']['hits']
            logger.info(f"Dense fallback search found {len(hits)} chunks")
        
        # Apply reranking if we have chunks
        if len(hits) > 0:
            reranker = get_reranker_service()
            chunks = [{"text": hit["_source"].get("text", ""), "hit": hit} for hit in hits]
            reranked_chunks = reranker.rerank(prompt, chunks, top_k=k)
            reranked_hits = [chunk["hit"] for chunk in reranked_chunks]
            logger.info(f"Reranked to top {len(reranked_hits)} chunks")
        else:
            reranked_hits = []
            logger.warning("No chunks found for RAG query")
        
        # Extract source information from chunks
        source_url = None
        source_filename = None
        chunks_used = []
        
        for hit in reranked_hits:
            source = hit["_source"]
            metadata = source.get("metadata", {})
            
            # Get source URL from first chunk
            if not source_url and metadata.get('source'):
                source_url = metadata['source']
                source_filename = metadata.get('filename') or metadata.get('source_filename')
            
            # Collect chunk information for transparency
            chunks_used.append({
                'text': source.get("text", "")[:500] + "..." if len(source.get("text", "")) > 500 else source.get("text", ""),
                'score': float(hit.get("_score", 0)),
                'metadata': {
                    'section': metadata.get('section_title', 'Unknown'),
                    'section_type': metadata.get('section_type', 'Unknown')
                }
            })
        
        # Step 3.3: Build RAG prompt with context
        if not reranked_hits:
            # No relevant chunks found
            return jsonify({
                'success': True,
                'content': f'I couldn\'t find relevant information in the sales manual for the IBM Power {server_model} to answer your question. The sales manual may not contain this information, or it may need to be re-ingested.',
                'query_type': query_type,
                'server_model': server_model,
                'chunks_found': 0,
                'chunks_used': [],
                'ai_services_used': ['watsonx_assistant', 'opensearch'],
                'processing_method': 'rag_no_chunks_found'
            })
        
        # Build context from retrieved chunks
        context_parts = []
        for i, hit in enumerate(reranked_hits, 1):
            chunk_text = hit["_source"].get("text", "")
            context_parts.append(f"[Context {i}]\n{chunk_text}\n")
        
        context = "\n".join(context_parts)
        
        # Build RAG prompt
        rag_prompt = f"""You are an expert on IBM Power Systems enterprise servers. You are answering questions about IBM Power servers, which are high-performance enterprise computing systems used in data centers for mission-critical workloads.

IMPORTANT CONTEXT:
- IBM Power servers (like E1080, S1024, etc.) are enterprise-grade computing systems, NOT consumer appliances
- When the sales manual mentions "heat generation" or "BTU output", this refers to the thermal characteristics of the server hardware that data center operators need to plan for cooling infrastructure
- Power consumption specifications help customers plan electrical and cooling requirements for data center deployment

Context from IBM Power Sales Manual:
{context}

Question: {prompt}

Instructions:
- Answer based ONLY on the information in the context above
- Frame your answer in the context of enterprise server specifications and data center planning
- When discussing power/heat specifications, explain them as technical requirements for data center infrastructure
- Be specific and technical when appropriate
- If the context doesn't contain enough information to fully answer the question, say so
- Do not make up information not present in the context
- Cite specific details from the context when relevant

Answer:"""
        
        # Step 3.4: Generate response with LLM
        # Select backend by model parameter: 'granite', 'tinyllama', 'vllm', or 'ollama'
        model_lower = model.lower()
        if model_lower == 'tinyllama':
            llm_host = TINYLLAMA_HOST
            llm_port = TINYLLAMA_PORT
            llm_format = 'llamacpp'
            logger.info(f"Using TinyLlama (llama.cpp) at {llm_host}:{llm_port}")
        elif model_lower == 'vllm':
            llm_host = VLLM_HOST
            llm_port = VLLM_PORT
            llm_format = 'openai'
            logger.info(f"Using vLLM at {llm_host}:{llm_port}")
        elif model_lower == 'ollama':
            llm_host = OLLAMA_HOST
            llm_port = OLLAMA_PORT
            llm_format = 'ollama'
            logger.info(f"Using Ollama at {llm_host}:{llm_port}")
        else:
            llm_host = GRANITE_HOST
            llm_port = GRANITE_PORT
            llm_format = 'llamacpp'
            logger.info(f"Using Granite (llama.cpp) at {llm_host}:{llm_port}")

        logger.info(f"Generating RAG response with {len(reranked_hits)} chunks, format={llm_format}, temperature={temperature}, n_predict={n_predict}")

        # Build request based on API format
        if llm_format == 'ollama':
            # Ollama native API
            llm_url = f"http://{llm_host}:{llm_port}/api/chat"
            payload = {
                "model": os.environ.get('OLLAMA_MODEL', 'granite4:latest'),
                "messages": [{"role": "user", "content": rag_prompt}],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": n_predict
                }
            }
        elif llm_format == 'openai':
            # vLLM — OpenAI-compatible chat completions
            llm_url = f"http://{llm_host}:{llm_port}/v1/chat/completions"
            payload = {
                "model": "granite",
                "messages": [{"role": "user", "content": rag_prompt}],
                "temperature": temperature,
                "max_tokens": n_predict,
                "stream": stream
            }
        else:
            # llama.cpp native completions
            llm_url = f"http://{llm_host}:{llm_port}/completion"
            payload = {
                "prompt": rag_prompt,
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

        # Extract content from whichever format was used
        if llm_format == 'ollama':
            # Ollama /api/chat returns {"message": {"role": "assistant", "content": "..."}}
            content = result.get('message', {}).get('content', '')
            timings = {}
        elif llm_format == 'openai':
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            timings = {}
        else:
            # llama.cpp native
            content = result.get('content', '')
            timings = result.get('timings', {})

        # Build response with transparency
        return jsonify({
            'success': True,
            'content': content,
            'query_type': query_type,
            'server_model': server_model,
            'chunks_found': len(hits),
            'chunks_used': chunks_used,
            'source_url': source_url,
            'source_filename': source_filename,
            'model': model,
            'timings': timings,
            'llm_format': llm_format,
            'ai_services_used': ['watsonx_assistant', 'opensearch', 'reranker', 'llm'],
            'processing_method': 'full_rag_generation',
            'llm_model': model_lower
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

# Lightweight IBM page used to verify Selenium is fully ready after a cold start.
# Dynamic enough to exercise Chromium but much smaller than a full Sales Manual.
SCRAPER_PROBE_URL = "https://www.ibm.com/support/pages/ibm-power-announcements"

def _wait_for_scraper_ready(scraper_url, max_attempts=3, wait_seconds=10):
    """
    Ensure the Code Engine scraper is genuinely ready — not just the container,
    but Selenium/Chromium inside it.

    Strategy:
      1. Hit /health to wake the container (fast, no Selenium involved).
      2. Probe with a lightweight known-dynamic IBM page up to max_attempts times.
         A successful scrape confirms Chromium has fully initialised.

    Returns True if ready, False if all attempts failed (caller should still
    proceed — the real scrape has its own retry logic).
    """
    import time

    # Step 1: wake the container
    try:
        requests.get(f"{scraper_url}/health", timeout=30)
        logger.info(f"[Scraper] Container is up at {scraper_url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"[Scraper] Health check failed: {e} — container may still be starting")

    # Step 2: probe until Selenium is ready
    for attempt in range(1, max_attempts + 1):
        logger.info(f"[Scraper] Selenium readiness probe attempt {attempt}/{max_attempts} "
                    f"(waiting {wait_seconds}s before probe)...")
        time.sleep(wait_seconds)
        try:
            resp = requests.get(
                f"{scraper_url}/scrape",
                params={"url": SCRAPER_PROBE_URL, "wait": 5},
                timeout=60
            )
            if resp.status_code == 200 and resp.json().get("success"):
                logger.info(f"[Scraper] ✅ Selenium ready after probe attempt {attempt}")
                return True
            logger.warning(f"[Scraper] Probe attempt {attempt} returned success=False: "
                           f"{resp.json().get('error', 'unknown')}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"[Scraper] Probe attempt {attempt} failed: {e}")

    logger.warning("[Scraper] ⚠️  Scraper not confirmed ready after all probe attempts — "
                   "proceeding anyway, real scrape has its own retry logic")
    return False


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
        
        # Ensure scraper container AND Selenium are ready before the real scrape
        scraper_url = os.environ.get('SCRAPER_URL', 'http://host.docker.internal:5000')
        _wait_for_scraper_ready(scraper_url)
        
        logger.info(f"Calling scraper at {scraper_url}/scrape?url={sales_manual_url}")
        
        # Retry logic for transient failures (e.g., cold starts)
        max_retries = 3
        retry_delay = 5  # seconds
        scraper_data = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} for MTM {mtm}")
                    import time
                    time.sleep(retry_delay)
                
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
                    logger.warning(f"Scraper returned error for MTM {mtm} (attempt {attempt + 1}): {error_msg}")
                    last_error = error_msg
                    continue  # Retry
                
                # Success!
                logger.info(f"Scraping successful for MTM {mtm}, got {scraper_data.get('sections_count', 0)} sections")
                break
                
            except requests.exceptions.Timeout:
                error_msg = f"Scraper timeout for MTM {mtm} (attempt {attempt + 1})"
                logger.warning(error_msg)
                last_error = 'Timeout'
                if attempt == max_retries - 1:
                    # Final attempt failed
                    bulk_ingestion_state['failed'].append({
                        'server': mtm,
                        'error': 'Timeout after retries'
                    })
                    return jsonify({'error': error_msg}), 504
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to call scraper (attempt {attempt + 1}): {str(e)}"
                logger.warning(error_msg)
                last_error = str(e)
                if attempt == max_retries - 1:
                    # Final attempt failed
                    bulk_ingestion_state['failed'].append({
                        'server': mtm,
                        'error': str(e)
                    })
                    return jsonify({'error': error_msg}), 500
        
        # Check if we got valid data after retries
        if not scraper_data or not scraper_data.get('success'):
            error_msg = f"Scraper failed for MTM {mtm} after {max_retries} attempts: {last_error}"
            logger.error(error_msg)
            bulk_ingestion_state['failed'].append({
                'server': mtm,
                'error': last_error or 'Unknown error'
            })
            return jsonify({'error': error_msg}), 500
        
        # Now ingest the scraped content
        # Collection name based on MTM: mtm_9080_heu, mtm_9009_42a, etc.
        collection_name = f"mtm_{mtm.lower().replace('-', '_')}"
        
        logger.info(f"Ingesting scraped content into collection: {collection_name}")
        
        # Transform Code Engine scraper format to expected format
        # Code Engine returns: {"full_text": "...", ...}
        # Backend expects: {"success": true, "full_text": "...", ...}
        transformed_data = {
            'success': True,
            'url': sales_manual_url,
            'page_title': f"{server_name} Sales Manual",
            'server_model': server_model,
            'mtm': mtm,
            'full_text': scraper_data.get('full_text', ''),
            'sections': scraper_data.get('sections', []),  # Pass structured sections so chunker uses headings not inline refs
            'scraped_at': datetime.now().isoformat()
        }
        
        # Call the existing ingest-scraped-content endpoint
        ingest_response = requests.post(
            'http://localhost:8080/ingest-scraped-content',
            json=transformed_data,
            timeout=900  # 15 minute timeout for ingestion (chunking + embeddings takes time)
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
            total_processed = len(bulk_ingestion_state['completed']) + len(bulk_ingestion_state.get('skipped', [])) + len(bulk_ingestion_state['failed'])
            if total_processed >= bulk_ingestion_state['total']:
                bulk_ingestion_state['in_progress'] = False
                logger.info(f"Bulk ingestion complete: {len(bulk_ingestion_state['completed'])} succeeded, {len(bulk_ingestion_state.get('skipped', []))} skipped, {len(bulk_ingestion_state['failed'])} failed")


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
            'skipped': bulk_ingestion_state.get('skipped', []),
            'failed': bulk_ingestion_state['failed'],
            'total': bulk_ingestion_state['total'],
            'completed_count': len(bulk_ingestion_state['completed']),
            'skipped_count': len(bulk_ingestion_state.get('skipped', [])),
            'failed_count': len(bulk_ingestion_state['failed']),
            'started_at': bulk_ingestion_state['started_at'],
            'force_reingest': bulk_ingestion_state.get('force_reingest', False)
        }
        logger.info(f"[Bulk Ingestion Status] in_progress={status['in_progress']}, current={status['current_server']}, completed={status['completed_count']}, skipped={status['skipped_count']}, total={status['total']}")
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
    
    Supports intelligent skip logic:
    - Checks if collection exists with documents
    - Compares content hash to detect source changes
    - Skips unchanged collections (unless force=true)
    
    Includes scraper warm-up to avoid Code Engine cold start issues
    """
    try:
        # Handle empty body gracefully (frontend sends POST with no body)
        data = request.get_json(silent=True) or {}
        force_reingest = data.get('force', False)  # Force re-ingestion of all servers
        
        # Check if bulk ingestion is already in progress
        if bulk_ingestion_state['in_progress']:
            logger.warning("[Bulk Ingestion] Already in progress, rejecting new request")
            return jsonify({
                'error': 'Bulk ingestion already in progress',
                'in_progress': True,
                'current_server': bulk_ingestion_state['current_server'],
                'completed_count': len(bulk_ingestion_state['completed']),
                'total': bulk_ingestion_state['total']
            }), 409  # Conflict
        
        # Ensure scraper container AND Selenium are ready before bulk ingestion starts
        scraper_url = os.environ.get('SCRAPER_URL', 'http://host.docker.internal:5000')
        logger.info(f"[Bulk Ingestion] Waiting for scraper to be fully ready at {scraper_url}...")
        _wait_for_scraper_ready(scraper_url)
        
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
        bulk_ingestion_state['skipped'] = []
        bulk_ingestion_state['total'] = len(servers)
        bulk_ingestion_state['started_at'] = datetime.now().isoformat()
        bulk_ingestion_state['force_reingest'] = force_reingest
        
        # Helper function to check if collection needs re-ingestion
        def should_reingest(server):
            """Check if server collection needs re-ingestion based on content hash"""
            mtm = server['mtm']
            logger.info(f"[Skip Check] Starting skip check for {mtm}")
            
            if force_reingest:
                logger.info(f"[Skip Check] ❌ {mtm}: Force re-ingest enabled")
                return True, "forced"
            
            try:
                # Generate collection name and use it directly as index name
                from server_mtm_mapper import get_collection_name_for_mtm
                collection_name = get_collection_name_for_mtm(mtm)
                if not collection_name:
                    logger.warning(f"[Skip Check] ❌ {mtm}: No collection mapping found")
                    return True, "no_collection_mapping"
                
                logger.info(f"[Skip Check] {mtm}: Collection name = {collection_name}")
                
                # Generate hash-based index name (system uses MD5 hashing)
                index_name = _generate_index_name(collection_name)
                logger.info(f"[Skip Check] {mtm}: Hash-based index name = {index_name}")
                
                # Check if index exists
                client = get_opensearch_client()
                exists = client.indices.exists(index=index_name)
                logger.info(f"[Skip Check] {mtm}: Index exists = {exists}")
                
                if not exists:
                    logger.info(f"[Skip Check] ❌ {mtm}: Index {index_name} doesn't exist")
                    return True, "index_missing"
                
                # Get document count
                count_response = client.count(index=index_name)
                doc_count = count_response.get('count', 0)
                logger.info(f"[Skip Check] {mtm}: Document count = {doc_count}")
                
                if doc_count == 0:
                    logger.info(f"[Skip Check] ❌ {mtm}: Index {index_name} is empty")
                    return True, "index_empty"
                
                # Get a sample document to check content hash
                search_response = client.search(
                    index=index_name,
                    body={
                        "size": 1,
                        "query": {"match_all": {}},
                        "_source": ["metadata.content_hash", "metadata.ingestion_timestamp", "content_hash", "ingestion_timestamp"]
                    }
                )
                
                if search_response['hits']['total']['value'] == 0:
                    logger.warning(f"[Skip Check] ❌ {mtm}: No documents found in search")
                    return True, "no_documents"
                
                existing_doc = search_response['hits']['hits'][0]['_source']
                # Try both nested and flat structure
                existing_hash = existing_doc.get('content_hash') or existing_doc.get('metadata', {}).get('content_hash')
                logger.info(f"[Skip Check] {mtm}: Existing hash = {existing_hash[:8] if existing_hash else 'None'}...")
                
                if not existing_hash:
                    logger.info(f"[Skip Check] ❌ {mtm}: No content hash found in document")
                    return True, "no_hash"
                
                # Scrape current content to get new hash
                logger.info(f"[Skip Check] {mtm}: Scraping current content to compare hash...")
                scraper_url = os.environ.get('SCRAPER_URL', 'http://host.docker.internal:5000')
                scraper_response = requests.get(
                    f"{scraper_url}/scrape",
                    params={'url': server['url'], 'wait': 10},
                    timeout=120
                )
                
                if scraper_response.status_code != 200:
                    logger.warning(f"[Skip Check] ❌ {mtm}: Scraper failed with status {scraper_response.status_code}")
                    return True, "scraper_error"
                
                scraper_data = scraper_response.json()
                new_text = scraper_data.get('full_text', '')
                new_hash = hashlib.sha256(new_text.encode('utf-8')).hexdigest()
                logger.info(f"[Skip Check] {mtm}: New hash = {new_hash[:8]}...")
                
                if existing_hash == new_hash:
                    logger.info(f"[Skip Check] ✅ {mtm}: UNCHANGED - Hashes match, skipping ingestion")
                    return False, "unchanged"
                else:
                    logger.info(f"[Skip Check] ❌ {mtm}: CHANGED - Hashes differ (old: {existing_hash[:8]}..., new: {new_hash[:8]}...)")
                    return True, "content_changed"
                    
            except Exception as e:
                logger.error(f"[Skip Check] ❌ {mtm}: Exception during check: {type(e).__name__}: {str(e)}")
                logger.exception(e)  # Log full traceback
                return True, "check_error"
        
        # Start background thread to process servers
        def process_servers():
            for server in servers:
                try:
                    bulk_ingestion_state['current_server'] = f"{server['model']} ({server['mtm']})"
                    
                    # Check if re-ingestion is needed
                    needs_reingest, reason = should_reingest(server)
                    
                    if not needs_reingest:
                        bulk_ingestion_state['skipped'].append({
                            'mtm': server['mtm'],
                            'model': server['model'],
                            'reason': reason
                        })
                        logger.info(f"[Bulk Ingestion] ⏭️  Skipped {server['model']} ({server['mtm']})")
                        continue
                    
                    logger.info(f"[Bulk Ingestion] Processing MTM {server['mtm']} - {server['model']} (reason: {reason})")
                    
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
                        
                        # Note: completed/failed tracking is done in ingest_sales_manual()
                        # which appends the MTM (not model name) to avoid double-counting
                        if status_code == 200:
                            logger.info(f"[Bulk Ingestion] ✓ {server['model']} completed")
                        else:
                            logger.error(f"[Bulk Ingestion] ✗ {server['model']} failed")
                            
                except Exception as e:
                    logger.error(f"[Bulk Ingestion] Error processing {server['model']}: {e}")
            
            # Mark as complete
            bulk_ingestion_state['in_progress'] = False
            bulk_ingestion_state['current_server'] = None
            logger.info(f"[Bulk Ingestion] Complete: {len(bulk_ingestion_state['completed'])} succeeded, {len(bulk_ingestion_state['skipped'])} skipped, {len(bulk_ingestion_state['failed'])} failed")
        
        # Start thread
        import threading
        thread = threading.Thread(target=process_servers, daemon=True)
        thread.start()
        
        logger.info(f"Started bulk ingestion of {len(servers)} servers in background thread (force={force_reingest})")
        
        return jsonify({
            'success': True,
            'message': f'Bulk ingestion started for {len(servers)} servers (force={force_reingest})',
            'total': len(servers),
            'force_reingest': force_reingest
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
    
    # Check LLM service — Ollama exposes /api/version; llama.cpp exposes /health
    try:
        if os.environ.get('OLLAMA_HOST'):
            llm_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/version"
        else:
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
