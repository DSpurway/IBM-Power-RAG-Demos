# RAG Chunking and Metadata Extraction Enhancements

## Overview
Enhanced the RAG backend to better handle IBM Power Sales Manual documentation, specifically optimized for:
1. Product lifecycle tables
2. Feature code descriptions with withdrawal dates
3. Structured attribute information

## Changes Made

### 1. Web Scraper Enhancements (`web_scraper.py`)

#### Table Preservation
- **New Function**: `html_table_to_markdown(table)`
  - Converts HTML tables to Markdown format
  - Preserves table structure in text-friendly format
  - Example output:
    ```markdown
    | Type Model | Announced | Available | Marketing Withdrawn | Service Discontinued |
    |---|---|---|---|---|
    | 9080-HEU | 2025-07-08 | 2025-07-25 | - | - |
    ```

#### Metadata Extraction
- **New Function**: `extract_withdrawal_dates(text)`
  - Extracts dates from patterns like:
    - "No Longer Available as of December 31, 2024"
    - "Marketing Withdrawn: January 15, 2025"
    - "(For China and South Korea - No Longer Available as of October 31, 2025)"
  - Returns structured data with type, date, and location

- **New Function**: `extract_feature_codes(text)`
  - Extracts feature codes like `(#EFA1)` or `(EFA1)`
  - Captures associated attributes:
    - Minimum/Maximum required values
    - CSU status (Yes/No)
    - Withdrawal dates specific to the feature
  - Example extraction:
    ```python
    {
        'code': 'EFA1',
        'description': '1 GB Memory Activation (Upgrade from P8)',
        'attributes': {
            'withdrawal_dates': [...],
            'minimum_required': 0,
            'maximum_allowed': 65536,
            'csu': True
        }
    }
    ```

#### Enhanced Content Extraction
- Tables are now converted to Markdown before text extraction
- Prevents duplicate extraction of table content
- Maintains table structure for better LLM comprehension

### 2. Docling Configuration Updates (`docling_config.py`)

#### Increased Chunk Size
- **Previous**: 768 tokens with 50 token overlap
- **New**: 1024 tokens with 100 token overlap
- **Rationale**:
  - Better accommodates multi-row tables
  - Keeps feature code descriptions with all attributes together
  - Reduces fragmentation of related information
  - 1024 tokens ≈ 750-800 words

#### Table Support
- `ENABLE_TABLES = true` (already enabled)
- Docling's table structure extraction with cell matching
- Preserves table semantics during PDF processing

### 3. Hierarchical Chunker (`hierarchical_chunker.py`)

No changes needed - already supports:
- Metadata preservation in chunks
- Hierarchical context (chapter/section/subsection)
- Custom metadata fields from web scraper

## Use Cases Addressed

### Use Case 1: Product Lifecycle Queries
**Question**: "When was the IBM Power E1180 announced?"

**How it works**:
1. Table is preserved in Markdown format
2. Chunk contains full table with all dates
3. LLM can easily parse structured table data
4. Metadata includes extracted dates for filtering

### Use Case 2: Feature Withdrawal Status
**Question**: "Is feature code EFA1 still available?"

**How it works**:
1. Feature code extracted with withdrawal dates
2. Metadata includes: `withdrawal_dates: [{type: 'withdrawal', date: 'December 31, 2024'}]`
3. LLM can check current date against withdrawal date
4. Location-specific dates preserved (e.g., China, South Korea)

### Use Case 3: Feature Attributes
**Question**: "What is the maximum allowed for feature EFA1?"

**How it works**:
1. Feature code attributes extracted: `maximum_allowed: 65536`
2. Full context preserved in chunk
3. Structured metadata enables precise answers

## Testing Recommendations

### 1. Table Extraction Test
```python
from web_scraper import IBMDocsScraper

scraper = IBMDocsScraper()
result = scraper.scrape_url('https://www.ibm.com/docs/en/announcements/...')

# Check for Markdown tables in content
assert '|' in result['content']
assert '---' in result['content']  # Table separator
```

### 2. Withdrawal Date Test
```python
# Check metadata extraction
assert 'withdrawal_dates' in result['metadata']
dates = result['metadata']['withdrawal_dates']
assert len(dates) > 0
assert 'date' in dates[0]
assert 'type' in dates[0]
```

### 3. Feature Code Test
```python
# Check feature code extraction
assert 'feature_codes' in result['metadata']
codes = result['metadata']['feature_codes']
assert len(codes) > 0
assert 'code' in codes[0]
assert 'attributes' in codes[0]
```

### 4. Chunk Size Test
```python
from hierarchical_chunker import chunk_with_hierarchy
from docling_converter import convert_pdf

doc = convert_pdf('path/to/sales_manual.pdf')
chunks = chunk_with_hierarchy(doc)

# Verify chunks can accommodate tables
large_chunks = [c for c in chunks if len(c['text']) > 800]
assert len(large_chunks) > 0  # Should have some large chunks for tables
```

## Deployment Notes

### Environment Variables
No new environment variables required. Existing variables can override defaults:
- `DOCLING_CHUNK_SIZE=1024` (new default)
- `DOCLING_CHUNK_OVERLAP=100` (new default)
- `ENABLE_TABLES=true` (already default)

### Backward Compatibility
- All changes are backward compatible
- Existing chunks will continue to work
- New chunks will have enhanced metadata
- Re-indexing recommended to get full benefits

### Performance Impact
- Slightly larger chunks (1024 vs 768 tokens)
- More metadata per chunk
- Minimal impact on search performance
- Better answer quality for structured content

## Future Enhancements

### Potential Improvements
1. **Table-specific embeddings**: Separate embedding strategy for tables
2. **Date-aware search**: Filter by date ranges in queries
3. **Feature code index**: Dedicated index for feature codes
4. **Multi-language support**: Handle location-specific dates better
5. **Table cell search**: Enable searching within specific table columns

### Monitoring
- Track chunk size distribution
- Monitor metadata extraction success rate
- Measure answer quality for table-based queries
- Log feature code extraction coverage

## References
- Docling Documentation: https://github.com/DS4SD/docling
- LangChain Text Splitters: https://python.langchain.com/docs/modules/data_connection/document_transformers/
- Markdown Table Syntax: https://www.markdownguide.org/extended-syntax/#tables

---
**Created**: 2026-05-06  
**Author**: Bob (AI Assistant)  
**Version**: 1.0