# Run E1080 Activation Test - Direct Execution
# This script runs the test directly via oc exec without copying files

Write-Host "E1080 Activation Retrieval Test (Direct Execution)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

# Find the rag-backend pod
Write-Host "Finding rag-backend pod..." -ForegroundColor Yellow
$pod = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if (-not $pod) {
    Write-Host "Error: rag-backend pod not found!" -ForegroundColor Red
    Write-Host "Make sure the backend is deployed and running." -ForegroundColor Red
    exit 1
}

Write-Host "Found pod: $pod" -ForegroundColor Green
Write-Host ""

Write-Host "Running E1080 activation test..." -ForegroundColor Yellow
Write-Host "This will show:" -ForegroundColor Cyan
Write-Host "  1. What chunks are retrieved from OpenSearch" -ForegroundColor Cyan
Write-Host "  2. What the activation service extracts" -ForegroundColor Cyan
Write-Host "  3. What goes to the LLM (if used)" -ForegroundColor Cyan
Write-Host "  4. What comes back as the final answer" -ForegroundColor Cyan
Write-Host ""

# Create a temporary Python script file locally
$tempScript = @"
import os
import sys
import json
import logging
from opensearchpy import OpenSearch
from langchain_community.embeddings import HuggingFaceEmbeddings
from activation_feature_service import ActivationFeatureService

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def print_section(title):
    print('')
    print('=' * 80)
    print('  ' + title)
    print('=' * 80)
    print('')

def print_chunk_preview(chunk_text, max_lines=10):
    lines = chunk_text.split('\n')
    for i, line in enumerate(lines[:max_lines], 1):
        print('  {:3d}: {}'.format(i, line))
    if len(lines) > max_lines:
        print('  ... ({} more lines)'.format(len(lines) - max_lines))

print_section('E1080 ACTIVATION RETRIEVAL TEST')

# Connect to OpenSearch
print('Step 1: Connecting to OpenSearch...')
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)
print('Connected to OpenSearch at {}:{}'.format(OPENSEARCH_HOST, OPENSEARCH_PORT))

# Find E1080 collection
print('')
print('Step 2: Finding E1080 collection...')
indices = client.indices.get_alias(index='rag_*')

e1080_index = None
for index_name in indices.keys():
    search_result = client.search(
        index=index_name,
        body={
            'size': 1,
            'query': {
                'bool': {
                    'should': [
                        {'match': {'text': 'E1080'}},
                        {'match': {'text': '9080-HEX'}}
                    ]
                }
            }
        }
    )
    
    if search_result['hits']['total']['value'] > 0:
        e1080_index = index_name
        print('Found E1080 collection: {}'.format(index_name))
        break

if not e1080_index:
    print('E1080 collection not found!')
    print('')
    print('Available collections:')
    for index_name in indices.keys():
        doc_count = client.count(index=index_name)['count']
        print('  - {} ({} documents)'.format(index_name, doc_count))
    sys.exit(1)

# Search for activation chunks
print_section('Step 3: Searching for Activation Chunks')

query = 'What activation features are available for E1080?'
print('Query: {}'.format(query))
print('')

print('Generating query embedding...')
embeddings = HuggingFaceEmbeddings(
    model_name='sentence-transformers/all-MiniLM-L6-v2',
    model_kwargs={'device': 'cpu'}
)
query_vector = embeddings.embed_query(query)
print('Query embedding generated (dimension: {})'.format(len(query_vector)))

print('')
print('Searching OpenSearch for activation chunks...')
search_body = {
    'size': 20,
    '_source': ['chunk_id', 'text', 'metadata'],
    'query': {
        'bool': {
            'must': [
                {
                    'knn': {
                        'embedding': {
                            'vector': query_vector,
                            'k': 20
                        }
                    }
                }
            ],
            'should': [
                {'match': {'text': 'activation'}},
                {'match': {'text': 'activations'}},
                {'match': {'text': 'memory activation'}},
                {'match': {'text': 'processor activation'}}
            ],
            'minimum_should_match': 1
        }
    }
}

response = client.search(index=e1080_index, body=search_body)
hits = response['hits']['hits']

print('Found {} chunks from OpenSearch'.format(len(hits)))
print('')

print('Preview of retrieved chunks:')
for i, hit in enumerate(hits[:3], 1):
    print('')
    print('--- Chunk {} (Score: {:.4f}) ---'.format(i, hit['_score']))
    chunk_text = hit['_source']['text']
    print_chunk_preview(chunk_text, max_lines=10)

if len(hits) > 3:
    print('')
    print('... and {} more chunks'.format(len(hits) - 3))

# Extract activation features
print_section('Step 4: Extracting Activation Features')

chunks = [
    {
        'text': hit['_source']['text'],
        'metadata': hit['_source'].get('metadata', {})
    }
    for hit in hits
]

print('Processing {} chunks with ActivationFeatureService...'.format(len(chunks)))
print('(LLM disabled to avoid timeouts in test)')
print('')

service = ActivationFeatureService(use_llm_descriptions=False, max_llm_calls=0)
features = service.extract_features_from_chunks(chunks)

print('')
print('Extracted {} features'.format(len(features)))

if features:
    print('')
    print('First 5 features:')
    for i, feature in enumerate(features[:5], 1):
        print('')
        print('  Feature {}:'.format(i))
        print('    Code: #{}'.format(feature.feature_code))
        desc_preview = feature.description[:80] + '...' if len(feature.description) > 80 else feature.description
        print('    Description: {}'.format(desc_preview))
        print('    Status: {}'.format(feature.status))
        
        # Show excerpt that would be sent to LLM
        if i == 1:
            print('')
            print('  Excerpt for #{} (what would go to LLM):'.format(feature.feature_code))
            excerpt = service._extract_feature_excerpt(feature.feature_code, feature.chunk_text)
            print('  ' + '-' * 76)
            for line in excerpt.split('\n')[:5]:
                print('  {}'.format(line))
            print('  ' + '-' * 76)
else:
    print('')
    print('No activation features found!')

# Show summary
print_section('Step 5: Summary')

if features:
    summary = service.format_activation_summary(features, query)
    
    print('Statistics:')
    print('  Total Features: {}'.format(summary['summary']['total']))
    print('  Available: {}'.format(summary['summary']['available']))
    print('  Discontinued: {}'.format(summary['summary']['discontinued']))
    print('  By Category:')
    for category, count in summary['summary']['by_category'].items():
        print('    - {}: {}'.format(category, count))
    
    answer = service.generate_activation_answer(features, query)
    print('')
    print('')
    print('Formatted Answer (first 400 chars):')
    print('-' * 80)
    answer_preview = answer[:400] + '...' if len(answer) > 400 else answer
    print(answer_preview)
    print('-' * 80)
else:
    print('No features to summarize')

print_section('TEST COMPLETE')
print('Retrieved {} chunks, extracted {} features'.format(len(hits), len(features)))
"@

# Save to temp file
$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$tempScript | Out-File -FilePath $tempFile -Encoding UTF8

try {
    # Copy to pod
    Write-Host "Copying test script to pod..." -ForegroundColor Yellow
    oc cp $tempFile ${pod}:/tmp/test_e1080.py 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Could not copy file, trying direct execution..." -ForegroundColor Yellow
        # Try running directly with cat
        Get-Content $tempFile | oc exec -i $pod -- python
    } else {
        # Run the copied script
        oc exec $pod -- python /tmp/test_e1080.py
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Test encountered an error. Check the output above." -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
    Write-Host "Test completed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "What you saw:" -ForegroundColor Cyan
    Write-Host "  - Chunks retrieved from OpenSearch for E1080 activations" -ForegroundColor White
    Write-Host "  - Feature codes extracted (e.g., #EDAR, #ELCP)" -ForegroundColor White
    Write-Host "  - Descriptions from sales manual" -ForegroundColor White
    Write-Host "  - Availability status for each feature" -ForegroundColor White
    Write-Host "  - The excerpt that would be sent to LLM" -ForegroundColor White
    Write-Host ""
    Write-Host "Done!" -ForegroundColor Green
}
finally {
    # Clean up temp file
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# Made with Bob
