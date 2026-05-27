#!/bin/bash
# Check if fallback feature extraction is being used

echo "====================================="
echo "  Check Fallback Feature Extraction"
echo "====================================="
echo ""

echo "Checking if scraped data has 'sections' field:"
python -c "
import json
d = json.load(open('e980_scraped_response.json'))
sections = d.get('sections', [])
print(f'Sections found: {len(sections)}')
print(f'Sections is: {type(sections)}')
if sections:
    print('Chunker will use structured sections (NOT fallback)')
else:
    print('Chunker will use fallback plain text extraction')
"

echo ""
echo "Checking chunker logic:"
grep -n "if sections:" sales_manual_chunker.py
grep -n "fallback" sales_manual_chunker.py

echo ""
echo "====================================="

# Made with Bob
