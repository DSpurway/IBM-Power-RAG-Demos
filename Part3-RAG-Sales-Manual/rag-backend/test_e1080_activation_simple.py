#!/usr/bin/env python3
"""
Simple test to understand E1080 activation retrieval flow
Shows exactly what is retrieved, extracted, and sent to LLM
"""

import os
import sys
import json
import logging
from opensearchpy import OpenSearch
from langchain_community.embeddings import HuggingFaceEmbeddings

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from activation_feature_service import ActivationFeatureService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'localhost')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))
OPENSEARCH_USERNAME = os.environ.get('OPENSEARCH_USERNAME', 'admin')
OPENSEARCH_PASSWORD = os.environ.get('OPENSEARCH_PASSWORD', 'admin')

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_chunk_preview(chunk_text, max_lines=15):
    """Print first N lines of chunk text"""
    lines = chunk_text.split('\n')
    for i, line in enumerate(lines[:max_lines], 1):
        print(f"  {i:3d}: {line}")
    if len(lines) > max_lines:
        print(f"  ... ({len(lines) - max_lines} more lines)")

def main():
    """Run the simple E1080 activation test"""
    
    print_section("E1080 ACTIVATION RETRIEVAL TEST")
    
    # Step 1: Connect to OpenSearch
    print("Step 1: Connecting to OpenSearch...")
    client = OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
        http_compress=True,
        use_ssl=False,
        http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
        verify_certs=False,
        ssl_show_warn=False
    )
    print(f"✓ Connected to OpenSearch at {OPENSEARCH_HOST}:{OPENSEARCH_PORT}")
    
    # Step 2: Find E1080 collection
    print("\nStep 2: Finding E1080 collection...")
    indices = client.indices.get_alias(index="rag_*")
    
    e1080_index = None
    for index_name in indices.keys():
        # Check if this index contains E1080 data
        search_result = client.search(
            index=index_name,
            body={
                "size": 1,
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"text": "E1080"}},
                            {"match": {"text": "9080-HEX"}},
                            {"match": {"metadata.mtm": "E1080"}}
                        ]
                    }
                }
            }
        )
        
        if search_result['hits']['total']['value'] > 0:
            e1080_index = index_name
            print(f"✓ Found E1080 collection: {index_name}")
            break
    
    if not e1080_index:
        print("✗ E1080 collection not found!")
        print("\nAvailable collections:")
        for index_name in indices.keys():
            doc_count = client.count(index=index_name)['count']
            print(f"  - {index_name} ({doc_count} documents)")
        return
    
    # Step 3: Search for activation chunks
    print_section("Step 3: Searching for Activation Chunks")
    
    query = "What activation features are available for E1080?"
    print(f"Query: {query}\n")
    
    # Initialize embeddings
    print("Generating query embedding...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )
    query_vector = embeddings.embed_query(query)
    print(f"✓ Query embedding generated (dimension: {len(query_vector)})")
    
    # Search for activation-related chunks
    print("\nSearching OpenSearch for activation chunks...")
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
                    {"match": {"text": "activation"}},
                    {"match": {"text": "activations"}},
                    {"match": {"text": "memory activation"}},
                    {"match": {"text": "processor activation"}}
                ],
                "minimum_should_match": 1
            }
        }
    }
    
    response = client.search(index=e1080_index, body=search_body)
    hits = response['hits']['hits']
    
    print(f"✓ Found {len(hits)} chunks from OpenSearch\n")
    
    # Show first 3 chunks
    print("Preview of retrieved chunks:")
    for i, hit in enumerate(hits[:3], 1):
        print(f"\n--- Chunk {i} (Score: {hit['_score']:.4f}) ---")
        chunk_text = hit['_source']['text']
        print_chunk_preview(chunk_text, max_lines=10)
    
    if len(hits) > 3:
        print(f"\n... and {len(hits) - 3} more chunks")
    
    # Step 4: Extract activation features
    print_section("Step 4: Extracting Activation Features")
    
    # Prepare chunks for activation service
    chunks = [
        {
            'text': hit['_source']['text'],
            'metadata': hit['_source'].get('metadata', {})
        }
        for hit in hits
    ]
    
    print(f"Processing {len(chunks)} chunks with ActivationFeatureService...")
    print("(max_llm_calls=1 to show line-by-line behavior)\n")
    
    # Create service with LLM disabled first to see manual extraction
    print("--- WITHOUT LLM (Manual Extraction) ---")
    service_no_llm = ActivationFeatureService(use_llm_descriptions=False, max_llm_calls=0)
    features_no_llm = service_no_llm.extract_features_from_chunks(chunks)
    
    print(f"\n✓ Extracted {len(features_no_llm)} features (manual extraction)")
    for i, feature in enumerate(features_no_llm[:5], 1):
        print(f"\n  Feature {i}:")
        print(f"    Code: #{feature.feature_code}")
        print(f"    Description: {feature.description[:100]}...")
        print(f"    Status: {feature.status}")
    
    # Now with LLM enabled (1 call only)
    print("\n\n--- WITH LLM (AI-Enhanced Descriptions) ---")
    print("Note: Only first feature will use LLM to avoid timeouts\n")
    
    service_with_llm = ActivationFeatureService(use_llm_descriptions=True, max_llm_calls=1)
    features_with_llm = service_with_llm.extract_features_from_chunks(chunks)
    
    print(f"\n✓ Extracted {len(features_with_llm)} features (with LLM enhancement)")
    
    # Show what was sent to LLM for the first feature
    if features_with_llm:
        first_feature = features_with_llm[0]
        print(f"\n  First Feature (LLM-enhanced):")
        print(f"    Code: #{first_feature.feature_code}")
        print(f"    Description: {first_feature.description}")
        print(f"    Status: {first_feature.status}")
        
        # Show the excerpt that was sent to LLM
        print(f"\n  Excerpt sent to LLM for #{first_feature.feature_code}:")
        excerpt = service_with_llm._extract_feature_excerpt(
            first_feature.feature_code,
            first_feature.chunk_text
        )
        print("  " + "-"*76)
        for line in excerpt.split('\n'):
            print(f"  {line}")
        print("  " + "-"*76)
    
    # Step 5: Show final formatted output
    print_section("Step 5: Final Formatted Output")
    
    summary = service_with_llm.format_activation_summary(features_with_llm, query)
    answer = service_with_llm.generate_activation_answer(features_with_llm, query)
    
    print("Summary Statistics:")
    print(f"  Total Features: {summary['summary']['total']}")
    print(f"  Available: {summary['summary']['available']}")
    print(f"  Discontinued: {summary['summary']['discontinued']}")
    print(f"  By Category:")
    for category, count in summary['summary']['by_category'].items():
        print(f"    - {category}: {count}")
    
    print("\n\nFormatted Answer (first 500 chars):")
    print("-" * 80)
    print(answer[:500])
    if len(answer) > 500:
        print(f"\n... ({len(answer) - 500} more characters)")
    print("-" * 80)
    
    # Step 6: Save detailed results
    print_section("Step 6: Saving Detailed Results")
    
    output_file = "e1080_activation_test_results.json"
    results = {
        "query": query,
        "collection": e1080_index,
        "chunks_retrieved": len(hits),
        "features_found": len(features_with_llm),
        "summary": summary,
        "features": [f.to_dict() for f in features_with_llm],
        "sample_chunks": [
            {
                "score": hit['_score'],
                "text_preview": hit['_source']['text'][:500],
                "metadata": hit['_source'].get('metadata', {})
            }
            for hit in hits[:3]
        ]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Detailed results saved to: {output_file}")
    
    print_section("TEST COMPLETE")
    print("Summary:")
    print(f"  - Retrieved {len(hits)} chunks from OpenSearch")
    print(f"  - Extracted {len(features_with_llm)} activation features")
    print(f"  - {summary['summary']['available']} available, {summary['summary']['discontinued']} discontinued")
    print(f"  - Results saved to {output_file}")
    print("\nYou can now review the JSON file for complete details.")

if __name__ == "__main__":
    main()

# Made with Bob
