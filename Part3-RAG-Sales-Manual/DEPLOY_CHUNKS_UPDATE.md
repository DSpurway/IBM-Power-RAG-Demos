# Deployment Guide - RAG Chunks Display & Prompt Enhancement

## Changes Summary

### Backend Changes (`rag-backend/app.py`)
1. **Enhanced RAG prompt** with better context about IBM Power servers
2. **Prevents misleading responses** like "E-1080 is a heater"
3. **Guides LLM** to frame answers as enterprise server specifications

### Frontend Changes (`carbon-rag-ui/src/app/sales-manual/page.js`)
1. **Added Layer wrapper** to source URL tile for consistent styling
2. **Added debug logging** to track response data

## Deployment Steps

### 1. Commit and Push Changes to GitHub

```bash
cd C:\Users\029878866\EMEA-AI-SQUAD\RAG-with-Notebook

# Check what files changed
git status

# Add the changed files
git add Part3-RAG-Sales-Manual/rag-backend/app.py
git add Part3-RAG-Sales-Manual/carbon-rag-ui/src/app/sales-manual/page.js
git add Part3-RAG-Sales-Manual/CHUNKS_DISPLAY_UPDATE.md
git add Part3-RAG-Sales-Manual/DEPLOY_CHUNKS_UPDATE.md

# Commit with descriptive message
git commit -m "Enhanced RAG: Add chunks display, improve LLM prompt for IBM Power context

- Frontend: Add Layer wrapper to source URL tile, add debug logging
- Backend: Enhance RAG prompt to provide IBM Power server context
- Prevents misleading responses (e.g., 'server is a heater')
- Guides LLM to frame answers as enterprise server specifications
- Adds transparency with chunks_used display in UI"

# Push to GitHub
git push origin main
```

### 2. Rebuild Backend on OpenShift

```bash
# Navigate to Part3 directory
cd Part3-RAG-Sales-Manual

# Rebuild backend with updated prompt
oc start-build rag-backend --from-dir=./rag-backend --follow

# Wait for build to complete, then check rollout
oc rollout status deployment/rag-backend
```

### 3. Rebuild Frontend on OpenShift

```bash
# Rebuild frontend with updated UI
oc start-build rag-frontend --from-dir=./carbon-rag-ui --follow

# Wait for build to complete, then check rollout
oc rollout status deployment/rag-frontend
```

### 4. Verify Deployment

```bash
# Check pod status
oc get pods | grep rag

# Check backend logs
oc logs -f deployment/rag-backend --tail=50

# Check frontend logs
oc logs -f deployment/rag-frontend --tail=50
```

### 5. Test the Changes

1. **Open the Sales Manual page** in your browser
2. **Open DevTools Console** (F12)
3. **Ask a test question**: "How much heat does a E1080 generate?"

**Expected Improved Response:**
```
The IBM Power E1080 server generates 1,800 watts (1.8 kW) of heat, which 
translates to approximately 6,480 BTU/hr. This thermal output is an important 
specification for data center operators to consider when planning cooling 
infrastructure and HVAC requirements for the server deployment.
```

**Instead of the old response:**
```
The E-1080 is a 1.8 kW (kilowatt) heater...
```

4. **Check Console Logs** for:
```javascript
[Query Response] {
  query_type: "rag",
  has_chunks: true,
  chunks_count: 5,
  has_source_url: true,
  source_url: "https://www.ibm.com/docs/...",
  source_filename: "IBM_Power_E1080.pdf"
}
```

5. **Verify UI displays:**
   - ✅ AI-generated answer (with improved context)
   - ✅ "Context Used (N chunks)" section
   - ✅ "Source:" section with clickable link

## Quick Rebuild Script

Create a script for easy deployment:

```bash
#!/bin/bash
# rebuild-rag-services.sh

echo "Rebuilding RAG Backend..."
oc start-build rag-backend --from-dir=./rag-backend --follow

echo "Waiting for backend rollout..."
oc rollout status deployment/rag-backend

echo "Rebuilding RAG Frontend..."
oc start-build rag-frontend --from-dir=./carbon-rag-ui --follow

echo "Waiting for frontend rollout..."
oc rollout status deployment/rag-frontend

echo "Deployment complete!"
echo "Check logs with:"
echo "  oc logs -f deployment/rag-backend"
echo "  oc logs -f deployment/rag-frontend"
```

Make it executable:
```bash
chmod +x rebuild-rag-services.sh
```

Run it:
```bash
./rebuild-rag-services.sh
```

## Rollback (if needed)

If something goes wrong:

```bash
# Rollback backend
oc rollout undo deployment/rag-backend

# Rollback frontend
oc rollout undo deployment/rag-frontend

# Check status
oc rollout status deployment/rag-backend
oc rollout status deployment/rag-frontend
```

## Testing Different Query Types

### 1. General RAG Query (should show chunks + improved response)
```
"How much heat does a E1080 generate?"
"What are the cooling requirements for S1024?"
"What is the power consumption of the E1180?"
```

### 2. Table Lookup (should show table data + source)
```
"When was the E1080 announced?"
"What is the withdrawal date for S924?"
```

### 3. Activation Features (should show structured features + source)
```
"What activation features does the E1080 have?"
"List the processor activations for S1024"
```

## Expected Improvements

### Before (Old Prompt)
- ❌ "The E-1080 is a 1.8 kW heater"
- ❌ Literal interpretation of technical specs
- ❌ No enterprise context

### After (Enhanced Prompt)
- ✅ "The IBM Power E1080 server generates 1.8 kW of heat"
- ✅ Explains specs in data center context
- ✅ Frames as enterprise server specifications
- ✅ Shows chunks used for transparency
- ✅ Provides source link for verification

## Troubleshooting

### Backend not updating?
```bash
# Force delete pod to trigger restart
oc delete pod -l app=rag-backend

# Check if new image is being used
oc describe deployment/rag-backend | grep Image
```

### Frontend not updating?
```bash
# Force delete pod to trigger restart
oc delete pod -l app=rag-frontend

# Check if new image is being used
oc describe deployment/rag-frontend | grep Image
```

### Chunks still not showing?
1. Check browser console for `[Query Response]` logs
2. Verify `has_chunks: true` in console
3. Check if server's sales manual is indexed
4. Try a different question

### Response still says "heater"?
1. Verify backend rebuild completed successfully
2. Check backend logs for the new prompt text
3. Force delete backend pod to ensure new code is running
4. Clear browser cache and reload page