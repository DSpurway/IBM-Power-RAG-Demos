import hashlib
import os

OPENSEARCH_DB_PREFIX = os.getenv('OPENSEARCH_DB_PREFIX', 'rag')
mtm = '9080-HEU'
collection_name = f'{OPENSEARCH_DB_PREFIX}_mtm_{mtm.lower().replace("-", "_")}'
hash_part = hashlib.md5(collection_name.encode()).hexdigest()
index_name = f'{OPENSEARCH_DB_PREFIX}_{hash_part}'

print(f'OPENSEARCH_DB_PREFIX: {OPENSEARCH_DB_PREFIX}')
print(f'MTM: {mtm}')
print(f'Collection: {collection_name}')
print(f'Hash: {hash_part}')
print(f'Index: {index_name}')

# Made with Bob
