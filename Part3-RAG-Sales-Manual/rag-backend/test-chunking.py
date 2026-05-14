#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify lifecycle table extraction
"""

import re
import sys

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Sample text with lifecycle table (similar to what we scrape)
sample_text = """
Product life cycle dates

| Type Model | Announced | Available | Marketing Withdrawn | Service Discontinued |
|---|---|---|---|---|
| 9080-HEX | 2021-09-14 | 2021-10-01 | - | - |

Abstract

This is the abstract section that should NOT be included in the lifecycle table chunk.

Highlights

More content here that should be separate.
"""

# Test the new pattern
table_pattern = r'Product\s+life\s*cycle\s+dates\s*\n+((?:\|[^\n]+\|\n?)+)'
match = re.search(table_pattern, sample_text, re.IGNORECASE)

if match:
    table_rows = match.group(1).strip()
    table_text = "Product life cycle dates\n" + table_rows
    
    print("✓ Table extracted successfully!")
    print(f"\nExtracted text ({len(table_text)} characters):")
    print("=" * 60)
    print(table_text)
    print("=" * 60)
    
    # Verify it doesn't include Abstract or other sections
    if "Abstract" in table_text:
        print("\n✗ ERROR: Table includes Abstract section!")
    else:
        print("\n✓ Table does NOT include Abstract section")
    
    if "Highlights" in table_text:
        print("✗ ERROR: Table includes Highlights section!")
    else:
        print("✓ Table does NOT include Highlights section")
        
    # Check size
    if len(table_text) < 300:
        print(f"\n✓ Table size is reasonable: {len(table_text)} characters")
    else:
        print(f"\n⚠ WARNING: Table might be too large: {len(table_text)} characters")
else:
    print("✗ ERROR: Could not extract table!")

# Made with Bob
