# Watson Assistant Clarification Handling

## Overview

Your Watson Assistant is smart! When a server name has multiple possible MTMs (like S924 could be different models), Watson asks for clarification by returning **options** for the user to choose from.

## How It Works

### Example Scenario

**User Query**: "When was the S924 announced?"

**Watson Response**:
- Intent: `Check_Date`
- Entity: `Server_Name` = "S924"
- Response Type: `option` (asking for clarification)
- Options:
  - "S924 (9009-42A) - 1-socket"
  - "S924 (9009-42G) - 2-socket"
  - "S924 (9009-42H) - 4-socket"

## Code Enhancement

The `watson_assistant_service.py` now includes:

### 1. `needs_clarification(analysis)` 
Checks if Watson is asking for clarification:
```python
if watson_service.needs_clarification(analysis):
    # Watson returned options - need user to choose
```

### 2. `extract_mtm_options(analysis)`
Extracts the MTM options Watson provides:
```python
options = watson_service.extract_mtm_options(analysis)
# Returns: [
#   {'label': 'S924 (9009-42A)', 'mtm': '9009-42A', 'value': {...}},
#   {'label': 'S924 (9009-42G)', 'mtm': '9009-42G', 'value': {...}},
#   ...
# ]
```

### 3. Enhanced `get_query_classification()`
Now returns clarification info:
```python
result = watson_service.get_query_classification(query)
# Returns:
# {
#   'success': True,
#   'query_type': 'table_lookup',
#   'needs_clarification': True,  # NEW!
#   'mtm_options': [...]  # NEW!
#   'entities': {...}
# }
```

## Integration with Backend

The backend can now handle clarification in two ways:

### Option 1: Return Options to User (Recommended)

When Watson needs clarification, return the options to the user:

```python
classification = watson_service.get_query_classification(query)

if classification.get('needs_clarification'):
    # Return options to user
    return jsonify({
        'success': True,
        'needs_clarification': True,
        'message': 'Multiple servers match your query. Please specify:',
        'options': classification.get('mtm_options'),
        'query_type': 'clarification_needed'
    })
```

**Frontend Response**:
```json
{
  "success": true,
  "needs_clarification": true,
  "message": "Multiple servers match your query. Please specify:",
  "options": [
    {"label": "S924 (9009-42A) - 1-socket", "mtm": "9009-42A"},
    {"label": "S924 (9009-42G) - 2-socket", "mtm": "9009-42G"},
    {"label": "S924 (9009-42H) - 4-socket", "mtm": "9009-42H"}
  ]
}
```

### Option 2: Use First Option (Fallback)

If you want automatic handling, use the first option:

```python
classification = watson_service.get_query_classification(query)

if classification.get('needs_clarification'):
    options = classification.get('mtm_options', [])
    if options:
        # Use first option as default
        mtm = options[0]['mtm']
        logger.info(f"Multiple MTMs found, using first: {mtm}")
        # Continue with table lookup using this MTM
```

## Testing Clarification

Test with queries that have multiple MTMs:

```bash
# Test S924 (has multiple models)
curl -X POST "http://$BACKEND_URL/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When was the S924 announced?"}'

# Expected: Watson returns options for clarification
```

## Watson Response Format

When Watson needs clarification, the response includes:

```json
{
  "output": {
    "intents": [
      {"intent": "Check_Date", "confidence": 0.98}
    ],
    "entities": [
      {"entity": "Server_Name", "value": "S924"}
    ],
    "generic": [
      {
        "response_type": "text",
        "text": "I found multiple S924 models. Which one do you mean?"
      },
      {
        "response_type": "option",
        "title": "Please select:",
        "options": [
          {
            "label": "S924 (9009-42A) - 1-socket",
            "value": {"input": {"text": "9009-42A"}}
          },
          {
            "label": "S924 (9009-42G) - 2-socket",
            "value": {"input": {"text": "9009-42G"}}
          }
        ]
      }
    ]
  }
}
```

## Benefits

1. **Accurate Results**: User gets exactly the server they meant
2. **Better UX**: Clear options instead of guessing
3. **Leverages Watson**: Uses Watson's built-in disambiguation
4. **Flexible**: Can handle automatically or ask user

## Implementation Status

✅ **Watson service enhanced** - Detects and extracts clarification options
✅ **Classification updated** - Returns `needs_clarification` flag
✅ **MTM extraction** - Parses MTMs from option labels
⏳ **Backend integration** - Ready to use when needed
⏳ **Frontend handling** - Can display options to user

## Next Steps

1. **Test** with ambiguous queries when build completes
2. **Decide** on handling strategy (return options vs auto-select)
3. **Implement** frontend display of options if needed
4. **Monitor** logs to see when clarification is triggered

## Example Log Output

When Watson needs clarification:
```
INFO:watson_assistant_service:Watson asking for clarification: Please select:
INFO:watson_assistant_service:Found MTM option: S924 (9009-42A) - 1-socket → 9009-42A
INFO:watson_assistant_service:Found MTM option: S924 (9009-42G) - 2-socket → 9009-42G
INFO:watson_assistant_service:Watson needs clarification: 2 options available
INFO:watson_assistant_service:Watson classification: type=table_lookup, confidence=0.980, entities={'server_model': 'S924', 'mtm': None, 'lifecycle_field': 'announced', 'mtm_options': [...]}, clarification=True
```

---

**Made with Bob** 🤖