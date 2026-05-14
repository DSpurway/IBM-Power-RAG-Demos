# Activation Feature Query System

## Overview

The activation feature query system enables users to ask questions about processor and memory activation features in IBM Power Systems sales manuals. It uses vector search to find relevant chunks, then extracts structured information about feature codes and their availability status.

## How It Works

### Architecture

```
User Query: "What memory activations are available?"
     ↓
Query Classifier
     ↓
Activation Lookup Detected
     ↓
Vector Search (OpenSearch)
  - Find chunks containing "activation"
  - Get 20 candidates
     ↓
Activation Feature Service
  - Parse feature codes (#EMB7, etc.)
  - Extract descriptions
  - Detect "No longer available as of" dates
     ↓
Structured Response
  - List of features
  - Availability status
  - Categorization (processor/memory)
  - Natural language answer
```

### Key Components

#### 1. Query Classification (`query_classifier.py`)

New query type: `ACTIVATION_LOOKUP`

**Patterns detected:**
- "still sell/available/order activation"
- "processor/memory/cpu activation"
- "can I buy activation"
- "list activation"
- "show activation"

#### 2. Activation Feature Service (`activation_feature_service.py`)

**Main Classes:**

**`ActivationFeature`**
- Represents a single activation feature
- Properties:
  - `feature_code`: e.g., "EMB7"
  - `description`: Feature description
  - `discontinued_date`: Date if no longer available
  - `is_available`: Boolean status
  - `status`: Human-readable status string

**`ActivationFeatureService`**
- Extracts features from chunks
- Parses feature codes and dates
- Categorizes by type (processor/memory)
- Generates natural language answers

#### 3. Backend Integration (`app.py`)

New route handler for `activation_lookup` query type:
1. Performs vector search with activation keywords
2. Extracts features from retrieved chunks
3. Returns structured JSON response

## Example Queries

### Query 1: General Activation Availability
```
Query: "What processor activations are available for this server?"

Response:
{
  "success": true,
  "query_type": "activation_lookup",
  "answer": "I found 3 activation features: 2 currently available and 1 discontinued...",
  "features": [
    {
      "feature_code": "EFA1",
      "description": "Processor Activation",
      "is_available": true,
      "status": "Available"
    },
    {
      "feature_code": "EMB7",
      "description": "Memory Activations for #EMB6 or #EMBA",
      "is_available": false,
      "discontinued_date": "October 22, 2019",
      "status": "Discontinued (October 22, 2019)"
    }
  ],
  "summary": {
    "total": 3,
    "available": 2,
    "discontinued": 1
  }
}
```

### Query 2: Memory Activations
```
Query: "Can I still buy memory activations?"

Response includes:
- All memory activation features found
- Availability status for each
- Discontinued dates if applicable
```

### Query 3: List All Activations
```
Query: "List all activation features"

Response includes:
- Complete list of activation features
- Categorized by type (processor/memory/other)
- Summary statistics
```

## Feature Code Parsing

### Pattern Recognition

The service looks for feature codes in the format:
- `(#CODE)` - e.g., "(#EMB7)"
- `#CODE` - e.g., "#EMB7"

Where CODE is 4 alphanumeric characters.

### Discontinued Date Detection

Patterns recognized:
- "No longer available as of [Date]"
- "Discontinued as of [Date]"
- "Withdrawn as of [Date]"
- "No longer marketed as of [Date]"

Date format: "Month DD, YYYY" (e.g., "October 22, 2019")

### Example Chunk

```
(#EMB7) Memory Activations for #EMB6 or #EMBA
(No longer available as of October 22, 2019)

This feature makes available 512GB of DDR3/DDR4, POWER8 memory activations.

It must be ordered in quantities of 8 (providing a total of 4TB of memory activation).
```

**Extracted:**
- Feature Code: EMB7
- Description: "Memory Activations for #EMB6 or #EMBA"
- Discontinued Date: "October 22, 2019"
- Is Available: false

## Categorization

Features are automatically categorized based on keywords:

### Processor Activations
Keywords: processor, cpu, core, proc

### Memory Activations
Keywords: memory, ram, ddr

### Other
Any activation not matching above categories

## Response Format

### Success Response

```json
{
  "success": true,
  "query_type": "activation_lookup",
  "answer": "Natural language answer...",
  "features": [
    {
      "feature_code": "EMB7",
      "description": "Memory Activations...",
      "discontinued_date": "October 22, 2019",
      "is_available": false,
      "status": "Discontinued (October 22, 2019)",
      "metadata": {}
    }
  ],
  "categories": {
    "processor": [...],
    "memory": [...],
    "other": [...]
  },
  "summary": {
    "total": 5,
    "available": 3,
    "discontinued": 2,
    "by_category": {
      "processor": 2,
      "memory": 3,
      "other": 0
    }
  },
  "results": [{
    "content": "Natural language answer...",
    "metadata": {
      "source": "sales_manual",
      "total_features": 5,
      "available_features": 3,
      "discontinued_features": 2
    },
    "score": 1.0
  }],
  "count": 5,
  "classification": {...},
  "activation_lookup": true
}
```

### Error Response

```json
{
  "success": false,
  "error": "No activation features found in the sales manual",
  "query_type": "activation_lookup",
  "classification": {...},
  "chunks_searched": 20
}
```

## Testing

### Test Script

Use the provided PowerShell test script:

```powershell
cd Part3-RAG-Sales-Manual/rag-backend
.\test-activation-query.ps1 -BackendUrl "http://localhost:8080" -Collection "ibm_power_s1022"
```

### Manual Testing

```bash
# Test activation query
curl -X POST http://localhost:8080/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What processor activations are available?",
    "collection_name": "ibm_power_s1022",
    "k": 10
  }'
```

## Integration with Watson Assistant

The activation query system can be enhanced with Watson Assistant:

1. **Intent Recognition**: Watson can better identify activation-related intents
2. **Entity Extraction**: Extract server models and feature types
3. **Clarification**: Ask follow-up questions if needed

Example Watson intent: `#activation_inquiry`

## Advantages Over Full RAG

### Why Not Use RAG for Activation Queries?

1. **Structured Data**: Activation features have a clear structure (code, description, date)
2. **Accuracy**: Direct extraction is more reliable than LLM generation
3. **Speed**: No LLM call needed for simple lookups
4. **Consistency**: Always returns the same structured data
5. **Completeness**: Can list ALL activation features, not just relevant ones

### When to Use RAG Instead

- Complex questions requiring reasoning
- Questions about relationships between features
- Questions requiring synthesis of multiple sources
- Questions about feature usage or recommendations

## Future Enhancements

### Potential Improvements

1. **Feature Relationships**: Parse "must be ordered with" dependencies
2. **Quantity Constraints**: Extract min/max quantities
3. **Regional Availability**: Parse "not supported in China and Korea"
4. **Pricing Information**: Extract CSU (Customer Setup) details
5. **Ordering Rules**: Parse MES (Manufacturing Engineering Specification) rules

### Example Enhanced Feature

```python
{
  "feature_code": "EMB7",
  "description": "Memory Activations...",
  "is_available": false,
  "discontinued_date": "October 22, 2019",
  "dependencies": ["EMB6", "EMBA"],
  "quantity_rules": {
    "minimum": 0,
    "maximum": 64,
    "must_order_in_multiples_of": 8
  },
  "regional_restrictions": ["China", "Korea"],
  "csu_eligible": true,
  "order_types": ["Supported"]
}
```

## Troubleshooting

### No Features Found

**Possible causes:**
1. Sales manual not loaded into collection
2. Activation features not in the manual
3. Chunks not properly indexed

**Solutions:**
- Verify collection exists: `GET /api/collections`
- Check chunk count: `GET /api/search` with simple query
- Review logs for parsing errors

### Incorrect Classification

**Possible causes:**
1. Query doesn't match activation patterns
2. Watson Assistant not configured

**Solutions:**
- Add more specific keywords: "processor activation", "memory activation"
- Check query classifier patterns in `query_classifier.py`
- Enable Watson Assistant for better intent recognition

### Missing Discontinued Dates

**Possible causes:**
1. Date format not recognized
2. Different wording in manual

**Solutions:**
- Check `DISCONTINUED_PATTERNS` in `activation_feature_service.py`
- Add new patterns if needed
- Review chunk text for actual wording

## Related Documentation

- [Query Classifier](query_classifier.py) - Query type detection
- [Table Lookup Service](table_lookup_service.py) - Similar structured lookup for lifecycle dates
- [Hybrid Query Strategy](HYBRID_QUERY_STRATEGY.md) - Overall query routing architecture

---

**Created**: 2026-05-14  
**Status**: Implemented and ready for testing  
**Next Steps**: Test with real sales manual data, gather user feedback