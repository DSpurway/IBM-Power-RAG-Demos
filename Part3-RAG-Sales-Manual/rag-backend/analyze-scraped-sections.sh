#!/bin/bash
# Analyze how Feature descriptions and 0004 appear in scraped data

echo "====================================="
echo "  Scraped Sections Analysis"
echo "====================================="
echo ""

echo "Finding 'Feature descriptions' section:"
python -c "
import json
d = json.load(open('e980_scraped_response.json'))
sections = d.get('sections', [])

for i, s in enumerate(sections):
    title = s.get('title', '')
    if 'Feature description' in title:
        print(f'Index {i}: {title}')
        print(f'  Level: {s.get(\"level\")}')
        print(f'  Content length: {len(s.get(\"content\", []))} paragraphs')
        print()
"

echo ""
echo "Finding all sections with '0004' in title:"
python -c "
import json
d = json.load(open('e980_scraped_response.json'))
sections = d.get('sections', [])

for i, s in enumerate(sections):
    title = s.get('title', '')
    if '0004' in title:
        print(f'Index {i}: {title}')
        print(f'  Level: {s.get(\"level\")}')
        content = s.get('content', [])
        print(f'  Content: {len(content)} paragraphs, {sum(len(p) for p in content)} chars total')
        if content:
            print(f'  First 100 chars: {content[0][:100]}...')
        print()
"

echo ""
echo "Section sequence around 'Feature descriptions':"
python -c "
import json
d = json.load(open('e980_scraped_response.json'))
sections = d.get('sections', [])

# Find Feature descriptions index
feat_idx = None
for i, s in enumerate(sections):
    if 'Feature description' in s.get('title', ''):
        feat_idx = i
        break

if feat_idx:
    print(f'Feature descriptions is at index {feat_idx}')
    print()
    print('5 sections before:')
    for i in range(max(0, feat_idx-5), feat_idx):
        print(f'  {i}: {sections[i].get(\"title\", \"\")}')
    print()
    print('10 sections after:')
    for i in range(feat_idx+1, min(len(sections), feat_idx+11)):
        title = sections[i].get('title', '')
        print(f'  {i}: {title[:80]}')
"

echo ""
echo "====================================="

# Made with Bob
