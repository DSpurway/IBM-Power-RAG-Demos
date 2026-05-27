# Diagnose E1080 Collection Issues
# Shows what collections exist and what data they contain

Write-Host "E1080 Collection Diagnostic" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host ""

# Find the rag-backend pod
Write-Host "Finding rag-backend pod..." -ForegroundColor Yellow
$pod = oc get pods -l app=rag-backend -o jsonpath='{.items[0].metadata.name}' 2>$null

if (-not $pod) {
    Write-Host "Error: rag-backend pod not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Found pod: $pod" -ForegroundColor Green
Write-Host ""

# Create diagnostic script
$diagnosticScript = @"
import os
from opensearchpy import OpenSearch

# Connect to OpenSearch
OPENSEARCH_HOST = os.environ.get('OPENSEARCH_HOST', 'opensearch-service')
OPENSEARCH_PORT = int(os.environ.get('OPENSEARCH_PORT', '9200'))

client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_compress=True,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False
)

print('='*80)
print('  E1080 COLLECTION DIAGNOSTIC')
print('='*80)
print('')

# Get all indices
print('Step 1: Listing all collections...')
print('')
indices = client.indices.get_alias(index='rag_*')

print('Found {} collections:'.format(len(indices)))
for index_name in sorted(indices.keys()):
    doc_count = client.count(index=index_name)['count']
    print('  - {} ({} documents)'.format(index_name, doc_count))

print('')
print('='*80)
print('  Step 2: Checking for E1080 MTM-based collection')
print('='*80)
print('')

# E1080 should be in: rag_mtm_9080_hex
expected_collection = 'rag_mtm_9080_hex'
print('Expected collection for E1080 (MTM 9080-HEX): {}'.format(expected_collection))

if expected_collection in indices:
    doc_count = client.count(index=expected_collection)['count']
    print('Status: FOUND ({} documents)'.format(doc_count))
    
    # Sample a document
    sample = client.search(
        index=expected_collection,
        body={'size': 1, '_source': ['text', 'metadata']}
    )
    
    if sample['hits']['total']['value'] > 0:
        hit = sample['hits']['hits'][0]
        text_preview = hit['_source']['text'][:200]
        metadata = hit['_source'].get('metadata', {})
        print('')
        print('Sample document:')
        print('  Text preview: {}...'.format(text_preview))
        print('  Metadata: {}'.format(metadata))
else:
    print('Status: NOT FOUND')
    print('')
    print('This means E1080 data was not ingested with MTM-based naming.')

print('')
print('='*80)
print('  Step 3: Checking what MTMs are in each collection')
print('='*80)
print('')

for index_name in sorted(indices.keys()):
    print('Collection: {}'.format(index_name))
    
    # Search for MTM references in the text
    mtm_search = client.search(
        index=index_name,
        body={
            'size': 5,
            '_source': ['text'],
            'query': {
                'bool': {
                    'should': [
                        {'match': {'text': '9080-HEX'}},
                        {'match': {'text': 'E1080'}},
                        {'match': {'text': '9043-MRX'}},
                        {'match': {'text': 'E1050'}},
                        {'match': {'text': '9043-MRU'}},
                        {'match': {'text': 'E1150'}}
                    ]
                }
            }
        }
    )
    
    if mtm_search['hits']['total']['value'] > 0:
        mtms_found = set()
        for hit in mtm_search['hits']['hits']:
            text = hit['_source']['text']
            if '9080-HEX' in text or 'E1080' in text:
                mtms_found.add('E1080 (9080-HEX)')
            if '9043-MRX' in text or 'E1050' in text:
                mtms_found.add('E1050 (9043-MRX)')
            if '9043-MRU' in text or 'E1150' in text:
                mtms_found.add('E1150 (9043-MRU)')
        
        if mtms_found:
            print('  Contains: {}'.format(', '.join(sorted(mtms_found))))
        else:
            print('  Contains: Other data')
    else:
        print('  Contains: No Power server MTMs found')
    
    print('')

print('='*80)
print('  DIAGNOSIS SUMMARY')
print('='*80)
print('')

if expected_collection in indices:
    print('GOOD: E1080 has its own MTM-based collection')
    print('Collection: {}'.format(expected_collection))
else:
    print('ISSUE: E1080 does not have MTM-based collection')
    print('')
    print('Possible causes:')
    print('  1. E1080 was ingested with old hashed naming (not MTM-based)')
    print('  2. E1080 data is mixed with other MTMs in a shared collection')
    print('  3. E1080 has not been ingested yet')
    print('')
    print('Solution:')
    print('  Re-ingest E1080 sales manual to create proper MTM-based collection')
    print('  Expected collection name: {}'.format(expected_collection))
"@

# Save to temp file and run
$tempFile = [System.IO.Path]::GetTempFileName() + ".py"
$diagnosticScript | Out-File -FilePath $tempFile -Encoding UTF8

try {
    Write-Host "Running diagnostic..." -ForegroundColor Yellow
    Write-Host ""
    
    # Try to copy and run
    oc cp $tempFile ${pod}:/tmp/diagnose.py 2>&1 | Out-Null
    
    if ($LASTEXITCODE -ne 0) {
        # Fallback: pipe directly
        Get-Content $tempFile | oc exec -i $pod -- python
    } else {
        oc exec $pod -- python /tmp/diagnose.py
    }
    
    Write-Host ""
    Write-Host "Diagnostic complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. If E1080 collection exists (rag_mtm_9080_hex), it's properly set up" -ForegroundColor White
    Write-Host "  2. If not, you need to re-ingest E1080 with MTM-based naming" -ForegroundColor White
    Write-Host "  3. If data is mixed, you may need to clean up old collections" -ForegroundColor White
}
finally {
    Remove-Item $tempFile -ErrorAction SilentlyContinue
}

# Made with Bob
