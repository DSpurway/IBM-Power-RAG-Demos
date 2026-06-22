# Chunking Fix - Detailed Analysis and Solution

## Problem Summary

The RAG system was producing incorrect chunks with three main issues:

1. **Chunk 1 too short** - Only contained the section title "Technical description - Physical specifications IBM Power System E980 model M95"
2. **Chunk 2 wrong content** - Showed Features section text instead of Technical description content
3. **Chunk 3 metadata visible** - Text like "Description (Part 181/922)" appearing in chunk content

## Root Causes Identified

### 1. Flawed `_find_section()` Method (Line 406-429)

**Problem:**
```python
# Old regex pattern - too simplistic
pattern = rf'{re.escape(section_name)}\s*\n+(.*?)(?=\n\n[A-Z][a-z]+\s*\n|\Z)'
```

This pattern:
- Didn't handle hierarchical section structures properly
- Used `\n\n` as section boundary, which failed for nested content
- Captured too little content or stopped at wrong boundaries

**Solution:**
```python
# New pattern - handles hierarchical sections
pattern = rf'^{re.escape(section_name)}\s*$\n+(.*?)(?=\n^[A-Z][a-z\s]+$\n|\Z)'
```

This improved pattern:
- Uses `^` and `$` anchors for precise line matching
- Properly identifies major section headings
- Includes fallback pattern for edge cases

### 2. Aggressive Feature Code Removal (Line 427)

**Problem:**
```python
# Old code - removed ALL feature codes from ALL sections
section_text = re.sub(r'\(#[A-Z0-9]{4}\)[^\n]*\n', '', section_text)
```

This corrupted the Technical description section by removing legitimate content that happened to contain feature code patterns.

**Solution:**
- Removed this line entirely from `_find_section()`
- Created new `_clean_section_text()` method with smarter cleaning
- Only removes standalone feature code headings, not feature codes in context

### 3. No Metadata Cleaning

**Problem:**
- Scraped text contained metadata artifacts like "(Part 181/922)"
- These were being included in chunk text verbatim

**Solution:**
```python
def _clean_section_text(self, text: str) -> str:
    """Clean section text by removing metadata artifacts"""
    # Remove metadata patterns like "Description (Part 181/922)"
    text = re.sub(r'\(Part\s+\d+/\d+\)', '', text)
    
    # Remove standalone feature code references
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip lines that are ONLY a feature code heading
        if re.match(r'^\(#[A-Z0-9]{4}\)\s*-?\s*[A-Z][^\n]{0,50}$', line.strip()):
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    text = re.sub(r'\n{3,}', '\n\n', text)  # Clean excessive whitespace
    return text.strip()
```

## Changes Made

### File: `sales_manual_chunker.py`

#### 1. Updated `_extract_sections()` method (Line 324)
- Added call to `_clean_section_text()` after extracting each section
- Ensures all sections are cleaned before chunking

#### 2. Rewrote `_find_section()` method (Line 406)
- Improved regex pattern for better section boundary detection
- Added fallback pattern for edge cases
- Removed aggressive feature code removal that was corrupting content

#### 3. Added new `_clean_section_text()` method (Line 430)
- Removes metadata artifacts like "(Part X/Y)"
- Intelligently removes standalone feature code headings
- Preserves feature codes when they appear in context
- Cleans excessive whitespace

## Expected Results

After these fixes, the Technical description section should:

1. **Chunk 1** - Contain full "Physical specifications" content with dimensions, weights, etc.
2. **Chunk 2** - Contain actual Technical description content (not Features section)
3. **Chunk 3** - Have clean text without metadata artifacts like "(Part 181/922)"

## Testing Recommendations

1. Re-ingest the E980 Sales Manual
2. Query: "How much heat does the E980 create?"
3. Verify chunks show:
   - Complete physical specifications
   - Proper Technical description content
   - No metadata artifacts in text

## Technical Notes

- The chunker now properly respects hierarchical section structure
- Feature codes are still extracted separately via `_extract_feature_codes_from_sections()`
- Section text cleaning is applied consistently across all sections
- The fix maintains backward compatibility with existing chunk metadata structure

---

**Fixed by:** Bob AI Assistant  
**Date:** 2026-06-02  
**Files Modified:** `sales_manual_chunker.py`