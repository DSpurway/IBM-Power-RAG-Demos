# Future Enhancements

## Overview

This document outlines potential improvements to the RAG Sales Manual system based on usage patterns and user feedback.

## 1. Automatic Daily Update Checks

### Current Behavior
- Skip logic is triggered manually when user clicks "Load All Documents"
- System scrapes each server, calculates hash, compares with stored hash
- Skips unchanged servers, re-ingests changed ones
- Takes ~15-25 seconds per server to check (scraping + hash calculation)

### Proposed Enhancement

**Automatic daily check on page load with smart notification:**

```
User opens Sales Manual page
    ↓
Frontend checks: "Last update check timestamp"
    ↓
If > 24 hours since last check:
    ↓
Backend: Quick hash check for all 26 servers
    ↓
Compare new hashes with stored hashes
    ↓
If changes detected:
    ↓
Show notification: "3 servers have updates available"
    ↓
User clicks "Update Now" button
    ↓
Re-ingest only the changed servers
```

### Benefits

✅ **Proactive**: Users know when updates are available  
✅ **Efficient**: Only checks once per day  
✅ **Non-intrusive**: Doesn't auto-update, just notifies  
✅ **Fast**: Only re-ingests changed servers  
✅ **Transparent**: Shows which servers changed  

### Implementation Plan

#### Backend Changes

**New API Endpoint: `/api/check-for-updates`**

```python
@app.route('/api/check-for-updates', methods=['GET'])
def check_for_updates():
    """
    Check all servers for content changes without re-ingesting
    Returns list of servers with updates available
    """
    servers_with_updates = []
    
    for server in ALL_SERVERS:
        # Quick scrape to get current content
        current_content = scrape_server(server['url'])
        current_hash = calculate_hash(current_content)
        
        # Get stored hash from OpenSearch
        stored_hash = get_stored_hash(server['mtm'])
        
        # Compare
        if current_hash != stored_hash:
            servers_with_updates.append({
                'mtm': server['mtm'],
                'model': server['model'],
                'name': server['name'],
                'old_hash': stored_hash[:8],
                'new_hash': current_hash[:8]
            })
    
    return jsonify({
        'success': True,
        'last_checked': datetime.now().isoformat(),
        'updates_available': len(servers_with_updates),
        'servers': servers_with_updates
    })
```

**Store last check timestamp:**

```python
# In-memory or Redis cache
last_update_check = {
    'timestamp': None,
    'servers_with_updates': []
}
```

#### Frontend Changes

**On page load (Sales Manual page):**

```javascript
useEffect(() => {
    // Check if we should run update check
    const lastCheck = localStorage.getItem('lastUpdateCheck');
    const now = Date.now();
    const oneDayMs = 24 * 60 * 60 * 1000;
    
    if (!lastCheck || (now - parseInt(lastCheck)) > oneDayMs) {
        checkForUpdates();
    }
}, []);

async function checkForUpdates() {
    try {
        const response = await fetch('/api/check-for-updates');
        const data = await response.json();
        
        localStorage.setItem('lastUpdateCheck', Date.now().toString());
        
        if (data.updates_available > 0) {
            setUpdateNotification({
                show: true,
                count: data.updates_available,
                servers: data.servers
            });
        }
    } catch (error) {
        console.error('Update check failed:', error);
    }
}
```

**Update notification UI:**

```jsx
{updateNotification.show && (
    <InlineNotification
        kind="info"
        title="Updates Available"
        subtitle={`${updateNotification.count} servers have new content`}
        actions={
            <>
                <Button size="sm" onClick={handleUpdateNow}>
                    Update Now
                </Button>
                <Button size="sm" kind="ghost" onClick={handleDismiss}>
                    Dismiss
                </Button>
            </>
        }
    />
)}
```

**Show which servers changed:**

```jsx
<Modal open={showUpdateDetails}>
    <ModalHeader>
        <h3>Servers with Updates</h3>
    </ModalHeader>
    <ModalBody>
        <DataTable
            rows={updateNotification.servers}
            headers={[
                { key: 'model', header: 'Server' },
                { key: 'name', header: 'Name' },
                { key: 'mtm', header: 'MTM' }
            ]}
        />
    </ModalBody>
    <ModalFooter>
        <Button kind="secondary" onClick={handleCancel}>
            Cancel
        </Button>
        <Button onClick={handleUpdateSelected}>
            Update Selected Servers
        </Button>
    </ModalFooter>
</Modal>
```

### Configuration Options

**Environment variables:**

```bash
# How often to check for updates (hours)
UPDATE_CHECK_INTERVAL=24

# Enable/disable automatic checks
AUTO_UPDATE_CHECK_ENABLED=true

# Check on page load or scheduled background job
UPDATE_CHECK_MODE=on_page_load  # or 'scheduled'
```

### Alternative: Scheduled Background Job

Instead of checking on page load, run a scheduled job:

```python
# Using APScheduler or similar
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def scheduled_update_check():
    """Run daily at 2 AM"""
    results = check_for_updates()
    
    # Store results for frontend to retrieve
    redis_client.set('pending_updates', json.dumps(results))
    
    # Optional: Send email notification
    if results['updates_available'] > 0:
        send_email_notification(results)

scheduler.add_job(
    scheduled_update_check,
    'cron',
    hour=2,
    minute=0
)
scheduler.start()
```

### Testing Plan

1. **Mock server changes**: Modify a test server's content
2. **Verify detection**: Check that hash comparison works
3. **Test notification**: Ensure UI shows update available
4. **Test selective update**: Update only changed servers
5. **Verify skip logic**: Unchanged servers still skipped

## 2. HEAD Request Optimization

### Current Behavior
- Full scrape (~10-20 seconds) to get content for hash calculation
- Even if content hasn't changed

### Proposed Enhancement

**Check Last-Modified header first:**

```python
def quick_change_check(url):
    """
    Check if content changed using HTTP HEAD request
    Much faster than full scrape
    """
    response = requests.head(url, timeout=5)
    last_modified = response.headers.get('Last-Modified')
    
    # Compare with stored last-modified timestamp
    stored_timestamp = get_stored_timestamp(url)
    
    if last_modified == stored_timestamp:
        return False  # No change, skip scraping
    else:
        return True   # Possible change, do full scrape
```

**Benefits:**
- Reduces check time from ~15-25 seconds to ~1-2 seconds per server
- Total check time: ~30-60 seconds for all 26 servers (vs ~7-11 minutes)

**Caveat:**
- Not all servers provide accurate Last-Modified headers
- Fallback to hash comparison if header not available

## 3. Parallel Update Checking

### Current Behavior
- Servers checked sequentially
- Total time: 26 servers × 15 seconds = ~7 minutes

### Proposed Enhancement

**Check multiple servers in parallel:**

```python
import concurrent.futures

def check_all_servers_parallel():
    """Check all servers in parallel"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(check_server, server): server 
            for server in ALL_SERVERS
        }
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            server = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error checking {server['mtm']}: {e}")
        
        return results
```

**Benefits:**
- Reduces total check time from ~7 minutes to ~2 minutes
- Better user experience

## 4. Email Notifications

### Proposed Enhancement

**Send email when updates are detected:**

```python
def send_update_notification(updates):
    """Send email notification about available updates"""
    subject = f"{len(updates)} IBM Power Server Updates Available"
    
    body = f"""
    The following servers have updated Sales Manuals:
    
    {format_server_list(updates)}
    
    Log in to update: https://your-rag-ui-url.com
    """
    
    send_email(
        to=ADMIN_EMAIL,
        subject=subject,
        body=body
    )
```

## 5. Update History Tracking

### Proposed Enhancement

**Track when each server was last updated:**

```python
# Store in OpenSearch or separate database
update_history = {
    'mtm': '9009-42A',
    'model': 'S924',
    'updates': [
        {
            'timestamp': '2026-05-27T10:00:00Z',
            'old_hash': 'abc123...',
            'new_hash': 'def456...',
            'document_count': 47,
            'changes_detected': 'content_changed'
        }
    ]
}
```

**UI to show update history:**
- When was each server last updated?
- How often do servers get updated?
- Which servers change most frequently?

## 6. Selective Server Monitoring

### Proposed Enhancement

**Allow users to choose which servers to monitor:**

```javascript
// UI to select servers for monitoring
<Checkbox
    labelText="Monitor this server for updates"
    id={`monitor-${server.mtm}`}
    checked={monitoredServers.includes(server.mtm)}
    onChange={(checked) => toggleMonitoring(server.mtm, checked)}
/>
```

**Benefits:**
- Faster checks (only monitor relevant servers)
- Reduced scraper load
- Customizable per user/organization

## Implementation Priority

### High Priority
1. ✅ **Automatic daily update checks** - Most valuable, reasonable effort
2. ✅ **HEAD request optimization** - Easy win, significant speedup

### Medium Priority
3. **Parallel checking** - Good improvement, moderate complexity
4. **Update history tracking** - Useful for analytics

### Low Priority
5. **Email notifications** - Nice to have, requires email setup
6. **Selective monitoring** - Advanced feature, lower demand

## Next Steps

1. **Gather feedback**: Validate these enhancements with users
2. **Prototype**: Build proof-of-concept for automatic checks
3. **Test**: Verify performance and reliability
4. **Deploy**: Roll out incrementally
5. **Monitor**: Track usage and effectiveness

## Related Documentation

- [SKIP_LOGIC_DOCUMENTATION.md](SKIP_LOGIC_DOCUMENTATION.md) - Current skip logic
- [BULK_INGESTION_ENHANCEMENT.md](BULK_INGESTION_ENHANCEMENT.md) - Bulk ingestion features

---

**Created**: 2026-05-27  
**Status**: Proposed enhancements for future implementation