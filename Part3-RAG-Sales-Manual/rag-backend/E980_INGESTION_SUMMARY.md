# E980 Ingestion Test - Current Status

## Summary

We're setting up a clean test ingestion of E980 (MTM 9080-M9S) to validate the data quality before re-ingesting other servers.

## Current Situation

### ✅ What's Working

1. **Scraper Service** - `ibm-docs-scraper` (older version) is responding
   - URL: `https://ibm-docs-scraper.29bw00k1vhg4.eu-gb.codeengine.appdomain.cloud`
   - Health endpoint works
   - Saved in: `scraper-url.txt`

2. **Backend Service** - rag-backend is running
   - Pod: `rag-backend-7cc8577645-fncxr`
   - Route: `https://rag-backend-llm-on-techzone.apps.p1265.cecc.ihost.com`

3. **OpenSearch** - Database is accessible
   - Target collection: `rag_mtm_9080_m9s`
   - Currently does not exist (ready for fresh ingestion)

### ⚠️ Known Issues

1. **Enhanced Scraper Not Responding**
   - `ibm-docs-scraper-enhanced` exists but doesn't respond
   - May have deployment issues
   - **Decision**: Use the older `ibm-docs-scraper` for now

2. **Previous Scraper Test Returned 0 Characters**
   - Need to verify the scraper actually retrieves content
   - Will test with `test-scraper-endpoints.sh`

3. **Data Quality Concerns from Previous Ingestion**
   - Mixed MTMs in collections (E1050 + E1080 together)
   - Lifecycle table may pull in too much content
   - Need to validate E980 ingestion carefully

## Scripts Created

### 1. `get-scraper-url-simple.sh`
- Gets scraper URL from Code Engine
- No jq dependency
- Saves to `scraper-url.txt`

### 2. `test-scraper-endpoints.sh`
- Tests scraper health
- Tests actual scraping of E980 page
- Validates content quality
- Identifies which scraper is deployed

### 3. `test-e980-ingestion.sh`
- Complete end-to-end ingestion test
- Scrapes → Ingests → Validates
- Checks for:
  - Lifecycle table presence
  - Activation features
  - Mixed MTM contamination
  - Feature code extraction

## Next Steps

### Step 1: Test the Scraper
```bash
cd Part3-RAG-Sales-Manual/rag-backend
chmod +x test-scraper-endpoints.sh
./test-scraper-endpoints.sh
```

**Expected Result:**
- Response size > 10,000 bytes
- Contains "Product life cycle dates"
- Contains feature codes (#XXXX)

**If scraper returns 0 or very little content:**
- The simple scraper may not handle IBM docs pages well
- May need to fix/redeploy enhanced scraper
- Or investigate why it's not getting content

### Step 2: Run E980 Ingestion Test
```bash
chmod +x test-e980-ingestion.sh
./test-e980-ingestion.sh
```

**What to Validate:**
1. ✅ Lifecycle table found (not too much extra content)
2. ✅ Activation features found (10-20 expected for E980)
3. ✅ No mixed MTMs (should be 0)
4. ✅ Feature codes are E980-specific

### Step 3: If E980 Looks Good
- Document the correct process
- Re-ingest other servers using same method
- Clean up old mixed collections

### Step 4: If Issues Found
- Adjust scraper or chunking strategy
- Fix and retry E980
- Don't proceed to other servers until E980 is clean

## Key Questions to Answer

1. **Does the scraper retrieve full content?**
   - Test with `test-scraper-endpoints.sh`
   - Should see > 10KB of content

2. **Is the lifecycle table properly extracted?**
   - Should be in one chunk
   - Not pulling in excessive surrounding content

3. **Are activation features correctly identified?**
   - Only E980 features
   - No contamination from other MTMs

4. **Is the MTM-based collection naming working?**
   - Should create `rag_mtm_9080_m9s`
   - Not a hashed name

## Files to Review After Ingestion

1. **e980_scraped_response.json** - Raw scraper output
2. **OpenSearch collection** - Check document count and content
3. **Activation query results** - Verify features are correct

## Success Criteria

E980 ingestion is successful if:
- ✅ Collection `rag_mtm_9080_m9s` created
- ✅ 50-200 chunks created (reasonable for a sales manual)
- ✅ Lifecycle table found in 1-2 chunks
- ✅ 10-20 activation features found
- ✅ 0 references to other MTMs (9080-HEX, 9043-MRX, etc.)
- ✅ Activation query returns E980-specific features

## Current Blockers

1. **Need to verify scraper works** - Run `test-scraper-endpoints.sh`
2. **Enhanced scraper not responding** - May need to investigate/fix later

## Decision Point

After running `test-scraper-endpoints.sh`:

- **If scraper works well** → Proceed with E980 ingestion
- **If scraper returns little/no content** → Need to fix scraper first
  - Option A: Debug why enhanced scraper isn't responding
  - Option B: Fix simple scraper to handle IBM docs better
  - Option C: Use a different scraping approach

---

**Current Status**: Ready to test scraper with `test-scraper-endpoints.sh`

**Next Action**: Run scraper test to verify it retrieves E980 content properly