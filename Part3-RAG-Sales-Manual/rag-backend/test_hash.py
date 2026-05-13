import hashlib

OPENSEARCH_DB_PREFIX = 'rag'

# Test a few MTMs
mtms = ['9080-HEU', '9043-MRU', '9824-42A', '9080-HEX']

print("Testing collection name hashing:")
print("=" * 60)

for mtm in mtms:
    collection_name = f'{OPENSEARCH_DB_PREFIX}_mtm_{mtm.lower().replace("-", "_")}'
    hash_part = hashlib.md5(collection_name.encode()).hexdigest()
    index_name = f'{OPENSEARCH_DB_PREFIX}_{hash_part}'
    print(f'MTM: {mtm:12} -> Index: {index_name}')

print("\nNow check if any of these match the indices you see in OpenSearch")

# Made with Bob
