# Watson Assistant Integration Guide

## Overview

This RAG system now includes **Watson Assistant** integration for enhanced Natural Language Processing (NLP). Watson Assistant provides superior intent classification and entity extraction compared to regex-based approaches, especially for complex queries about IBM Power systems.

## Benefits

### 1. **Superior Intent Classification**
- Better understanding of user intent (lifecycle queries, feature lookups, general questions)
- Handles variations in phrasing naturally
- Learns from interactions over time

### 2. **Enhanced Entity Extraction**
- Accurately identifies server models (E1180, S924, etc.)
- Extracts MTMs (Machine Type-Models like 9080-HEU)
- Recognizes feature codes and lifecycle fields
- Handles synonyms and abbreviations

### 3. **Improved User Experience**
- More accurate query routing
- Faster responses for table lookup queries
- Better handling of ambiguous questions
- Support for follow-up questions

## Architecture

```
User Query
    ↓
Watson Assistant (if enabled)
    ├─→ Intent Classification
    ├─→ Entity Extraction
    └─→ Confidence Score
    ↓
Query Classifier (with Watson results)
    ├─→ TABLE_LOOKUP (lifecycle dates)
    ├─→ METADATA_LOOKUP (feature codes)
    └─→ RAG (general questions)
    ↓
Appropriate Handler
```

## Configuration

### Environment Variables

Add these to your deployment configuration:

```bash
# Watson Assistant Configuration
WATSON_ASSISTANT_API_KEY=your-api-key-here
WATSON_ASSISTANT_URL=https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/your-instance-id
WATSON_ASSISTANT_ID=your-assistant-id-here  # Optional, can be configured in Watson
```

### Your Current Credentials

Based on your information:
- **API Key**: `Y-WtqYpU77yrcm7bs2xHqVKjzm9d6gLUh_4o-B0CChGJ`
- **URL**: `https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/c6a8deb1-c724-4ad3-ac1d-660144bf8792`

### OpenShift Deployment

Update your deployment YAML or use `oc set env`:

```bash
# Set Watson Assistant credentials
oc set env deployment/rag-backend \
  WATSON_ASSISTANT_API_KEY="Y-WtqYpU77yrcm7bs2xHqVKjzm9d6gLUh_4o-B0CChGJ" \
  WATSON_ASSISTANT_URL="https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/c6a8deb1-c724-4ad3-ac1d-660144bf8792"

# Restart the deployment
oc rollout restart deployment/rag-backend
```

## Watson Assistant Setup

### Required Intents

Configure these intents in your Watson Assistant:

1. **product_announcement**
   - Examples: "When was the E1180 announced?", "announcement date for S924"
   
2. **product_availability**
   - Examples: "When did the E1180 become available?", "availability date"
   
3. **product_withdrawal**
   - Examples: "When was the S924 withdrawn?", "withdrawal date"
   
4. **end_of_support**
   - Examples: "When did we stop supporting the S924?", "end of support date"
   
5. **feature_availability**
   - Examples: "Is feature EFA1 still available?", "can I order feature code EFA1?"

### Required Entities

Configure these entities:

1. **@server_model**
   - Pattern: `E\d{4}|S\d{3,4}|L\d{3,4}|H\d{3,4}`
   - Examples: E1180, S924, S1024, L922, H922
   
2. **@mtm**
   - Pattern: `\d{4}-[A-Z0-9]{3}`
   - Examples: 9080-HEU, 9009-42A, 9223-42H
   
3. **@feature_code**
   - Pattern: `[A-Z0-9]{4}`
   - Examples: EFA1, EPEX, EPEY

### Training Examples

Add these training examples to improve accuracy:

```
Intent: end_of_support
- When did we stop supporting the S924?
- When did support end for the E1180?
- What is the end of support date for the S1024?
- Is the S924 still supported?
- When was support discontinued for the L922?

Intent: product_announcement
- When was the E1180 announced?
- What is the announcement date for the S1024?
- When did IBM announce the S924?

Intent: product_withdrawal
- When was the S924 withdrawn?
- What is the withdrawal date for the E1180?
- When did the S1024 go end of life?
```

## Fallback Behavior

The system is designed with graceful degradation:

1. **Watson Available & Configured**: Uses Watson for classification and entity extraction
2. **Watson Unavailable**: Falls back to regex-based classification
3. **Watson Low Confidence**: Uses regex as backup
4. **No Watson Credentials**: Runs in regex-only mode

This ensures the system always works, even without Watson Assistant.

## Testing

### Test Watson Integration

```bash
# Check if Watson is enabled
curl -X POST http://rag-backend-route/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "When did we stop supporting the S924?"}'

# The response will include query_type and source information
```

### Expected Behavior

**With Watson (High Confidence)**:
```json
{
  "query_type": "table_lookup",
  "source": "watson_assistant",
  "confidence": 0.95,
  "server_model": "S924",
  "lifecycle_field": "end_of_support"
}
```

**Without Watson (Regex Fallback)**:
```json
{
  "query_type": "table_lookup",
  "source": "regex",
  "server_model": "S924",
  "lifecycle_field": "end_of_support"
}
```

## Monitoring

Check logs for Watson Assistant activity:

```bash
# View Watson Assistant usage
oc logs -f deployment/rag-backend | grep -i watson

# Expected log messages:
# INFO:query_classifier:Watson Assistant integration available
# INFO:query_classifier:Watson Assistant enabled for query classification
# INFO:query_classifier:Watson classified as TABLE_LOOKUP (conf: 0.95)
```

## Troubleshooting

### Watson Not Working

1. **Check credentials**:
   ```bash
   oc get deployment/rag-backend -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="WATSON_ASSISTANT_API_KEY")].value}'
   ```

2. **Check logs**:
   ```bash
   oc logs deployment/rag-backend | grep -i "watson\|error"
   ```

3. **Test API directly**:
   ```bash
   curl -X POST "https://api.eu-gb.assistant.watson.cloud.ibm.com/v2/assistants/YOUR_ASSISTANT_ID/sessions?version=2021-11-27" \
     -u "apikey:YOUR_API_KEY"
   ```

### Common Issues

**Issue**: "Watson Assistant not configured"
- **Solution**: Set WATSON_ASSISTANT_API_KEY and WATSON_ASSISTANT_URL environment variables

**Issue**: "Failed to create Watson Assistant session"
- **Solution**: Check API key is valid and URL is correct
- **Solution**: Ensure WATSON_ASSISTANT_ID is set if using a specific assistant

**Issue**: Low confidence scores
- **Solution**: Add more training examples to Watson Assistant
- **Solution**: Review and improve intent definitions

## Performance Impact

- **Watson API Call**: ~100-300ms per query
- **Regex Fallback**: <1ms per query
- **Caching**: Session reuse reduces overhead
- **Timeout**: 15 seconds (configurable)

The system caches Watson sessions to minimize API calls and improve performance.

## Cost Considerations

Watson Assistant pricing is based on:
- Monthly Active Users (MAU)
- API calls
- Plan tier (Lite, Plus, Enterprise)

For development/testing, the Lite plan provides:
- 10,000 API calls/month
- Sufficient for moderate testing

## Next Steps

1. **Configure Watson Assistant** with intents and entities
2. **Set environment variables** in OpenShift
3. **Test the integration** with sample queries
4. **Monitor performance** and adjust confidence thresholds
5. **Train Watson** with real user queries for better accuracy

## Benefits for MTM Matching

Watson Assistant is particularly valuable for:
- **Synonym handling**: "Power E1180" = "E1180" = "IBM Power System E1180"
- **MTM extraction**: Recognizes "9080-HEU" format
- **Context understanding**: "stop supporting" = "end of support"
- **Multi-entity queries**: "When was the E1180 (9080-HEU) announced?"

This makes it ideal for your use case of matching queries to MTMs and sales manuals!

---

**Made with Bob** 🤖