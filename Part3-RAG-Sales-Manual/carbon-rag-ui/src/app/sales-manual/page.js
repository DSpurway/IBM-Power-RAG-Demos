'use client';
import {
  Breadcrumb,
  BreadcrumbItem,
  Button,
  Tabs,
  Tab,
  TabList,
  TabPanels,
  TabPanel,
  Grid,
  Column,
  TextArea,
  Tile,
  Loading,
  InlineNotification,
  DataTable,
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableHeader,
  TableBody,
  TableCell,
  Tag,
  OverflowMenu,
  OverflowMenuItem,
  Modal,
  TextInput,
  ProgressBar,
  Select,
  SelectItem,
  Layer,
  AILabel,
  AILabelContent,
} from '@carbon/react';
import {
  Checkmark,
  WarningAlt,
  Renew,
  View,
  TrashCan,
} from '@carbon/icons-react';
import React, { useState, useEffect } from 'react';
import FeaturesView from '../../components/FeaturesView';

// IBM Power server configuration - Ordered by processor generation (POWER11, POWER10, POWER9)
// Within each generation: Enterprise first, then Scale-out, then others (Linux, High-performance, etc.)
// Generation is indicated by the number in model name: E1150=Power11, E1050=Power10, E950=Power9
const IBM_POWER_SERVERS = [
  // POWER11 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest)
  { model: "E1180", name: "IBM Power E1180", mtm: "9080-HEU", processor: "POWER11", url: "https://www.ibm.com/docs/en/announcements/family-908005-power-e1180-enterprise-server-9080-heu", category: "Enterprise" },
  { model: "E1150", name: "IBM Power E1150", mtm: "9043-MRU", processor: "POWER11", url: "https://www.ibm.com/docs/en/announcements/family-904302-power-e1150-enterprise-midrange-technology-based-server-9043-mru", category: "Enterprise" },
  { model: "S1124", name: "IBM Power S1124", mtm: "9824-42A", processor: "POWER11", url: "https://www.ibm.com/docs/en/announcements/family-982402-power-s1124-9824-42a", category: "Scale-out" },
  { model: "S1122", name: "IBM Power S1122", mtm: "9824-22A", processor: "POWER11", url: "https://www.ibm.com/docs/en/announcements/family-982401-power-s1122-9824-22a", category: "Scale-out" },
  // POWER10 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest), then Linux (largest to smallest)
  { model: "E1080", name: "IBM Power E1080", mtm: "9080-HEX", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-e1080-enterprise-server", category: "Enterprise" },
  { model: "E1050", name: "IBM Power E1050", mtm: "9043-MRX", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-e1050-enterprise-midrange-technology-based-server", category: "Enterprise" },
  { model: "S1024", name: "IBM Power S1024", mtm: "9105-42A", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-s1024-9105-42a", category: "Scale-out" },
  { model: "S1022", name: "IBM Power S1022", mtm: "9105-22A", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-s1022-9105-22a", category: "Scale-out" },
  { model: "S1014", name: "IBM Power S1014", mtm: "9105-41B", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-s1014-9105-41b", category: "Scale-out" },
  { model: "S1012", name: "IBM Power S1012", mtm: "9028-21B", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/family-9028-01-power-s1012", category: "Scale-out" },
  { model: "L1024", name: "IBM Power L1024", mtm: "9786-42H", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-l1024-9786-42h", category: "Linux-only" },
  { model: "L1022", name: "IBM Power L1022", mtm: "9786-22H", processor: "POWER10", url: "https://www.ibm.com/docs/en/announcements/power-l1022-9786-22h", category: "Linux-only" },
  // POWER9 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest), then others (High-performance, Intensive-compute, Linux - largest to smallest)
  { model: "E980", name: "IBM Power System E980", mtm: "9080-M9S", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-e980-9080-m9s", category: "Enterprise" },
  { model: "E950", name: "IBM Power System E950", mtm: "9040-MR9", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-e950-9040-mr9", category: "Enterprise" },
  { model: "S924", name: "IBM Power System S924", mtm: "9009-42A", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42a", category: "Scale-out" },
  { model: "S924-G", name: "IBM Power System S924", mtm: "9009-42G", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s924-9009-42g", category: "Scale-out" },
  { model: "S922", name: "IBM Power System S922", mtm: "9009-22A", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22a", category: "Scale-out" },
  { model: "S922-G", name: "IBM Power System S922", mtm: "9009-22G", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s922-9009-22g", category: "Scale-out" },
  { model: "S914", name: "IBM Power System S914", mtm: "9009-41A", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41a", category: "Scale-out" },
  { model: "S914-G", name: "IBM Power System S914", mtm: "9009-41G", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-s914-9009-41g-2023-10-24", category: "Scale-out" },
  { model: "H924", name: "IBM Power System H924", mtm: "9223-42S", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-h924-9223-42s-2023-10-24", category: "High-performance" },
  { model: "H922", name: "IBM Power System H922", mtm: "9223-22S", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-h922-9223-22s-2023-10-24", category: "High-performance" },
  { model: "IC922", name: "IBM Power System IC922", mtm: "9183-22X", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-ic922-9183-22x-2021-12-14", category: "Intensive-compute" },
  { model: "L922", name: "IBM Power System L922", mtm: "9008-22L", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-l922-9008-22l", category: "Linux-only" },
  { model: "LC922", name: "IBM Power System LC922", mtm: "9006-22P", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-system-lc922-9006-22p", category: "Linux-only" },
  { model: "LC921", name: "IBM Power System LC921", mtm: "9006-12P", processor: "POWER9", url: "https://www.ibm.com/docs/en/announcements/power-systems-lc921-9006-12p", category: "Linux-only" },
];

export default function SalesManualPage() {
  const [activeTab, setActiveTab] = useState(0);
  
  // Server management state
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedServer, setSelectedServer] = useState(null);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  
  // Bulk ingestion progress state
  const [bulkIngestionInProgress, setBulkIngestionInProgress] = useState(false);
  const [bulkIngestionStatus, setBulkIngestionStatus] = useState(null);
  const [bulkIngestionStarted, setBulkIngestionStarted] = useState(false); // Track if we've seen it start
  
  // Query state
  const [queryText, setQueryText] = useState('');
  const [queryResults, setQueryResults] = useState(null);
  const [queryLoading, setQueryLoading] = useState(false);
  const [selectedClarification, setSelectedClarification] = useState('');

  // Load server status on mount and check for ongoing bulk ingestion
  useEffect(() => {
    const initializePage = async () => {
      // First, load server status
      await loadServerStatus();
      
      // Then check if bulk ingestion is in progress
      await checkBulkIngestionStatus();
    };
    
    initializePage();
  }, []);

  // Check if bulk ingestion is currently in progress (on page load)
  const checkBulkIngestionStatus = async () => {
    try {
      const response = await fetch('/api/rag/bulk-ingestion-status');
      if (!response.ok) return;
      
      const status = await response.json();
      console.log('[Page Load] Bulk ingestion status:', status);
      
      // If bulk ingestion is in progress, resume polling
      if (status.in_progress) {
        console.log('[Page Load] Bulk ingestion in progress, resuming polling');
        setBulkIngestionInProgress(true);
        setBulkIngestionStatus(status);
        setBulkIngestionStarted(true);
        const skippedCount = status.skipped_count || 0;
        const progressMsg = skippedCount > 0
          ? `Bulk ingestion in progress: ${status.completed_count} completed, ${skippedCount} skipped (unchanged), ${status.total - status.completed_count - skippedCount - status.failed_count} remaining`
          : `Bulk ingestion in progress: ${status.completed_count} of ${status.total} completed`;
        setError(progressMsg);
        
        // Start polling
        setTimeout(pollBulkIngestionStatus, 2000);
      }
    } catch (err) {
      console.error('[Page Load] Error checking bulk ingestion status:', err);
    }
  };

  const loadServerStatus = async () => {
    setLoading(true);
    setError('');
    
    try {
      // Get collections from backend (now returns MTM-based collection metadata with doc counts)
      const response = await fetch('/api/rag/collections');
      if (!response.ok) throw new Error('Failed to load collections');
      
      const data = await response.json();
      const collectionsMap = data.collections_map || {};
      const collectionsDetails = data.collections_details || {};
      
      console.log('[Page Load] Collections data:', { collectionsMap, collectionsDetails });
      
      // Match servers with their indexed status
      // Backend now returns a map of MTM -> index_name and detailed info with doc counts
      const serversWithStatus = IBM_POWER_SERVERS.map(server => {
        const isIndexed = server.mtm in collectionsMap;
        const collectionName = `mtm_${server.mtm.toLowerCase().replace(/-/g, '_')}`;
        const details = collectionsDetails[server.mtm];
        
        return {
          ...server,
          collectionName: collectionName,
          indexName: isIndexed ? collectionsMap[server.mtm] : null,
          status: isIndexed ? 'indexed' : 'not-indexed',
          lastUpdated: isIndexed ? new Date().toISOString() : null,
          contentHash: null,
          documentCount: details ? details.document_count : 0
        };
      });
      
      setServers(serversWithStatus);
      
      // Count indexed vs not-indexed
      const indexedCount = serversWithStatus.filter(s => s.status === 'indexed').length;
      const notIndexedCount = serversWithStatus.filter(s => s.status === 'not-indexed').length;
      const totalDocs = serversWithStatus.reduce((sum, s) => sum + (s.documentCount || 0), 0);
      
      console.log(`[Page Load] Server status: ${indexedCount} indexed (${totalDocs} total docs), ${notIndexedCount} not indexed`);
      
      // Show helpful message if nothing is indexed
      if (indexedCount === 0 && notIndexedCount > 0) {
        setError('No servers indexed yet. Click "Load All Documents" to start bulk ingestion.');
      } else if (notIndexedCount > 0) {
        setError(`${indexedCount} servers indexed (${totalDocs} documents), ${notIndexedCount} not indexed. You can load individual servers or use "Load All Documents".`);
      } else {
        setError(`All ${indexedCount} servers indexed successfully! Total: ${totalDocs} documents.`);
      }
    } catch (err) {
      console.error('Error loading server status:', err);
      setError(err.message);
      // Initialize with default status
      setServers(IBM_POWER_SERVERS.map(s => ({
        ...s,
        collectionName: `mtm_${s.mtm.toLowerCase().replace(/-/g, '_')}`,
        status: 'unknown',
        lastUpdated: null,
        contentHash: null,
        documentCount: 0
      })));
    } finally {
      setLoading(false);
    }
  };

  // Poll bulk ingestion status
  const pollBulkIngestionStatus = async () => {
    try {
      // Call through Next.js API route, not directly to backend
      const response = await fetch('/api/rag/bulk-ingestion-status');
      
      if (!response.ok) {
        console.error('Failed to fetch bulk ingestion status');
        // Continue polling even on error
        if (bulkIngestionInProgress) {
          setTimeout(pollBulkIngestionStatus, 10000);
        }
        return;
      }
      
      const status = await response.json();
      console.log('[Bulk Ingestion] Status update:', status);
      setBulkIngestionStatus(status);
      
      // Track if we've seen the ingestion actually start
      if (status.in_progress) {
        setBulkIngestionStarted(true);
      }
      
      // Continue polling if:
      // 1. Backend says it's in progress, OR
      // 2. We haven't seen it start yet (give backend thread time to initialize)
      if (status.in_progress || !bulkIngestionStarted) {
        setTimeout(pollBulkIngestionStatus, 10000); // Poll every 10 seconds
      } else {
        // Ingestion complete (we've seen it start and now it's finished)
        setBulkIngestionInProgress(false);
        setLoading(false);
        
        // Show completion message
        const skippedCount = status.skipped_count || 0;
        if (status.failed_count > 0) {
          setError(`Bulk ingestion completed with errors. ${status.completed_count} succeeded, ${skippedCount} skipped (unchanged), ${status.failed_count} failed.`);
        } else if (skippedCount > 0) {
          setError(`Bulk ingestion completed! ${status.completed_count} re-ingested, ${skippedCount} skipped (unchanged).`);
        } else {
          setError(`Bulk ingestion completed successfully! All ${status.completed_count} servers indexed.`);
        }
        
        // Reload server status
        await loadServerStatus();
      }
    } catch (err) {
      console.error('Error polling bulk ingestion status:', err);
      // Continue polling even on error
      if (bulkIngestionInProgress) {
        setTimeout(pollBulkIngestionStatus, 10000);
      }
    }
  };

  const handleLoadAllDocuments = async () => {
    setLoading(true);
    setBulkIngestionInProgress(true);
    setBulkIngestionStatus(null);
    setBulkIngestionStarted(false); // Reset the started flag
    setError('Starting bulk ingestion of all 26 servers... This will take several hours.');
    
    try {
      // Call bulk ingest endpoint
      const response = await fetch('/api/rag/ingest-all-sales-manuals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || 'Failed to start bulk ingestion');
      }
      
      const data = await response.json();
      console.log('[Bulk Ingestion] Started:', data);
      
      // Set initial status to show progress tile immediately
      setBulkIngestionStatus({
        in_progress: true,
        current_server: 'Initializing...',
        completed: [],
        skipped: [],
        failed: [],
        total: data.total || 26,
        completed_count: 0,
        skipped_count: 0,
        failed_count: 0,
        started_at: new Date().toISOString()
      });
      
      setError(`Bulk ingestion started! Processing ${data.total} servers. Status updates will appear below.`);
      
      // Start polling for progress immediately (backend thread starts quickly)
      setTimeout(pollBulkIngestionStatus, 2000); // Start polling after 2 seconds
    } catch (err) {
      console.error('[Bulk Ingestion] Error starting:', err);
      setError(`Error starting bulk ingestion: ${err.message}`);
      setLoading(false);
      setBulkIngestionInProgress(false);
      setBulkIngestionStarted(false);
    }
  };

  const handleIngestServer = async (server) => {
    setLoading(true);
    setError(`Ingesting ${server.mtm} (${server.model})... This may take 5-10 minutes.`);
    
    try {
      // Call scraper endpoint with MTM-based parameters
      const response = await fetch('/api/rag/ingest-sales-manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mtm: server.mtm,
          server_model: server.model,
          server_name: server.name,
          processor: server.processor,
          url: server.url
        })
      });
      
      if (!response.ok) throw new Error('Failed to ingest server documentation');
      
      const data = await response.json();
      setError(`${server.mtm} ingested successfully! ${data.indexed || 0} documents indexed.`);
      
      // Reload server status
      await loadServerStatus();
    } catch (err) {
      setError(`Error ingesting ${server.mtm}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckForUpdates = async (server) => {
    setLoading(true);
    setError(`Checking ${server.model} for updates...`);
    
    try {
      // Calculate hash of current Sales Manual page
      const response = await fetch('/api/rag/check-updates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: server.url,
          currentHash: server.contentHash
        })
      });
      
      if (!response.ok) throw new Error('Failed to check for updates');
      
      const data = await response.json();
      if (data.hasUpdates) {
        setError(`${server.model} has updates available! Re-ingest to get latest content.`);
      } else {
        setError(`${server.model} is up to date.`);
      }
    } catch (err) {
      setError(`Error checking updates for ${server.model}: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (server) => {
    setSelectedServer(server);
    setShowDetailsModal(true);
  };

  const handleQuery = async () => {
    if (!queryText.trim()) return;
    
    setQueryLoading(true);
    setError('');
    setSelectedClarification(''); // Reset clarification selection
    
    try {
      const response = await fetch('/api/rag/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          collection_name: 'sales_manuals',
          prompt: queryText,
          top_k: 3
        })
      });
      
      if (!response.ok) throw new Error('Failed to query');
      
      const data = await response.json();
      setQueryResults(data);
    } catch (err) {
      setError(`Query error: ${err.message}`);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleClarificationSelect = async (value) => {
    if (!value) return;
    
    setSelectedClarification(value);
    setQueryLoading(true);
    setError('');
    
    try {
      // Determine what type of clarification this is based on the current query results
      const clarificationType = queryResults.query_type;
      let requestBody = {
        collection_name: 'sales_manuals',
        prompt: queryText,
        top_k: 3
      };
      
      // Add the clarification value based on type
      if (clarificationType === 'mtm_clarification_needed') {
        // User selected an MTM - send it as server_mtm parameter
        requestBody.server_mtm = value;
      } else if (clarificationType === 'server_clarification_needed') {
        // User selected a server model - send it as server_model parameter
        requestBody.server_model = value;
      } else if (clarificationType === 'lifecycle_clarification_needed') {
        // User selected a lifecycle field - send it as lifecycle_field parameter
        requestBody.lifecycle_field = value;
      }
      
      // Re-submit query with the selected clarification
      const response = await fetch('/api/rag/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) throw new Error('Failed to query');
      
      const data = await response.json();
      setQueryResults(data);
    } catch (err) {
      setError(`Query error: ${err.message}`);
    } finally {
      setQueryLoading(false);
    }
  };

  // DataTable headers
  const headers = [
    { key: 'model', header: 'Model' },
    { key: 'name', header: 'Server Name' },
    { key: 'mtm', header: 'MTM' },
    { key: 'processor', header: 'Processor' },
    { key: 'category', header: 'Category' },
    { key: 'status', header: 'Status' },
    { key: 'documentCount', header: 'Docs' },
    { key: 'actions', header: 'Actions' },
  ];

  // Format rows for DataTable
  const rows = servers.map((server, idx) => ({
    id: `${idx}`,
    model: server.model,
    name: server.name,
    mtm: server.mtm,
    processor: server.processor,
    category: server.category,
    status: server.status,
    documentCount: server.documentCount,
    actions: server,
  }));

  return (
    <Grid className="rag-page" fullWidth>
      <Column lg={16} md={8} sm={4} className="rag-page__banner">
        <Breadcrumb noTrailingSlash aria-label="Page navigation">
          <BreadcrumbItem>
            <a href="/">Home</a>
          </BreadcrumbItem>
        </Breadcrumb>
        <h1 className="rag-page__heading">IBM Power Sales Manual RAG</h1>
      </Column>

      <Column lg={16} md={8} sm={4} className="rag-page__r2">
        <Tabs selectedIndex={activeTab} onChange={({ selectedIndex }) => setActiveTab(selectedIndex)}>
          <TabList className="tabs-group" aria-label="Sales Manual tabs" contained>
            <Tab>Manage Source Documents</Tab>
            <Tab>Query Documentation</Tab>
          </TabList>
          
          <TabPanels>
            {/* Tab 1: Manage Servers */}
            <TabPanel>
              <Grid className="tabs-group-content">
                <Column lg={16}>
                  <Tile className="tile-spacing">
                    <h3>IBM Power Server Documentation Management</h3>
                    <p className="description-text">
                      Manage Sales Manual documentation for 26 IBM Power servers (POWER9, POWER10, POWER11).
                      Each server's documentation is scraped from IBM Docs and indexed for RAG queries.
                    </p>
                    
                    {error && (
                      <InlineNotification
                        kind={error.startsWith('Error') || error.startsWith('Failed') ? 'error' : 'info'}
                        title={error.startsWith('Error') ? 'Error' : 'Status'}
                        subtitle={error}
                        onCloseButtonClick={() => setError('')}
                        className="section-spacing"
                      />
                    )}
                    
                    {/* Bulk Ingestion Progress */}
                    {bulkIngestionInProgress && bulkIngestionStatus && (
                      <Layer withBackground>
                        <Tile className="progress-tile">
                          <h4 className="progress-tile__heading">Bulk Ingestion Progress</h4>
                          <p className="progress-tile__text">
                            <strong>Current Server:</strong> {bulkIngestionStatus.current_server || 'Starting...'}
                          </p>
                          <p className="progress-tile__text">
                            <strong>Progress:</strong> {bulkIngestionStatus.completed_count} completed
                            {bulkIngestionStatus.skipped_count > 0 && `, ${bulkIngestionStatus.skipped_count} skipped`}
                            {bulkIngestionStatus.failed_count > 0 && `, ${bulkIngestionStatus.failed_count} failed`}
                            {' '}of {bulkIngestionStatus.total}
                          </p>
                          <ProgressBar
                            label="Ingestion Progress"
                            value={bulkIngestionStatus.completed_count + (bulkIngestionStatus.skipped_count || 0)}
                            max={bulkIngestionStatus.total}
                            helperText={`${Math.round(((bulkIngestionStatus.completed_count + (bulkIngestionStatus.skipped_count || 0)) / bulkIngestionStatus.total) * 100)}% complete`}
                          />
                          {bulkIngestionStatus.completed && bulkIngestionStatus.completed.length > 0 && (
                            <details className="progress-details">
                              <summary className="progress-details__summary">
                                Completed Servers ({bulkIngestionStatus.completed.length})
                              </summary>
                              <div className="progress-details__content">
                                {bulkIngestionStatus.completed.join(', ')}
                              </div>
                            </details>
                          )}
                          {bulkIngestionStatus.skipped && bulkIngestionStatus.skipped.length > 0 && (
                            <details className="progress-details">
                              <summary className="progress-details__summary" style={{color: '#0f62fe'}}>
                                Skipped Servers ({bulkIngestionStatus.skipped.length}) - Content Unchanged
                              </summary>
                              <div className="progress-details__content">
                                {bulkIngestionStatus.skipped.map(s => s.mtm || s).join(', ')}
                              </div>
                            </details>
                          )}
                          {bulkIngestionStatus.failed && bulkIngestionStatus.failed.length > 0 && (
                            <details className="progress-details">
                              <summary className="progress-details__summary progress-details__content--failed">
                                Failed Servers ({bulkIngestionStatus.failed.length})
                              </summary>
                              <div className="progress-details__content progress-details__content--failed">
                                {bulkIngestionStatus.failed.join(', ')}
                              </div>
                            </details>
                          )}
                        </Tile>
                      </Layer>
                    )}
                    
                    <div className="button-group">
                      <Button
                        onClick={loadServerStatus}
                        disabled={loading || bulkIngestionInProgress}
                      >
                        {loading ? 'Loading...' : 'Refresh Status'}
                      </Button>
                      <Button
                        kind="primary"
                        onClick={handleLoadAllDocuments}
                        disabled={loading || bulkIngestionInProgress}
                      >
                        {bulkIngestionInProgress ? 'Ingestion in Progress...' : 'Load All Documents'}
                      </Button>
                    </div>
                    
                    <DataTable rows={rows} headers={headers}>
                      {({ rows, headers, getTableProps, getHeaderProps, getRowProps }) => (
                        <TableContainer>
                          <Table {...getTableProps()}>
                            <TableHead>
                              <TableRow>
                                {headers.map((header) => (
                                  <TableHeader key={header.key} {...getHeaderProps({ header })}>
                                    {header.header}
                                  </TableHeader>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {rows.map((row) => {
                                const server = servers[parseInt(row.id)];
                                return (
                                  <TableRow key={row.id} {...getRowProps({ row })}>
                                    {row.cells.map((cell) => {
                                      if (cell.info.header === 'status') {
                                        return (
                                          <TableCell key={cell.id}>
                                            {server.status === 'indexed' && (
                                              <Tag type="green" size="sm">Indexed</Tag>
                                            )}
                                            {server.status === 'not-indexed' && (
                                              <Tag type="gray" size="sm">Not Indexed</Tag>
                                            )}
                                            {server.status === 'unknown' && (
                                              <Tag type="red" size="sm">Unknown</Tag>
                                            )}
                                          </TableCell>
                                        );
                                      }
                                      if (cell.info.header === 'actions') {
                                        return (
                                          <TableCell key={cell.id}>
                                            <OverflowMenu size="sm" flipped>
                                              <OverflowMenuItem
                                                itemText="View Details"
                                                onClick={() => handleViewDetails(server)}
                                              />
                                              <OverflowMenuItem
                                                itemText={server.status === 'indexed' ? 'Re-ingest' : 'Ingest'}
                                                onClick={() => handleIngestServer(server)}
                                                disabled={loading}
                                              />
                                              {server.status === 'indexed' && (
                                                <OverflowMenuItem
                                                  itemText="Check for Updates"
                                                  onClick={() => handleCheckForUpdates(server)}
                                                  disabled={loading}
                                                />
                                              )}
                                            </OverflowMenu>
                                          </TableCell>
                                        );
                                      }
                                      return <TableCell key={cell.id}>{cell.value}</TableCell>;
                                    })}
                                  </TableRow>
                                );
                              })}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      )}
                    </DataTable>
                  </Tile>
                </Column>
              </Grid>
            </TabPanel>
            
            {/* Tab 2: Query Documentation */}
            <TabPanel>
              <Grid className="tabs-group-content">
                <Column lg={16}>
                  <Tile className="tile-spacing">
                    <h3>Query IBM Power Documentation</h3>
                    <p className="description-text">
                      Ask questions about IBM Power servers using our <strong>Hybrid AI System</strong>:
                    </p>
                    <ul className="list-text">
                      <li><strong>watsonx Assistant</strong> - Natural language understanding and intent detection</li>
                      <li><strong>OpenSearch Vector DB</strong> - Semantic search with preserved table structures</li>
                      <li><strong>Granite LLM</strong> - Generative AI for complex queries requiring synthesis</li>
                    </ul>
                    <p className="helper-text">
                      <em>Note: Simple data lookups (like lifecycle dates) are answered directly from structured tables without using the LLM, providing faster and more accurate responses.</em>
                    </p>
                    
                    <TextArea
                      labelText="Your Question"
                      placeholder="e.g., What are the key features of the IBM Power E1180?"
                      value={queryText}
                      onChange={(e) => setQueryText(e.target.value)}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          if (queryText.trim()) {
                            handleQuery();
                          }
                        }
                      }}
                      rows={3}
                      className="section-spacing"
                      helperText="Press Enter to submit, Shift+Enter for new line"
                    />
                    
                    <Button
                      onClick={handleQuery}
                      disabled={queryLoading || !queryText.trim()}
                    >
                      {queryLoading ? 'Querying...' : 'Ask Question'}
                    </Button>
                    
                    {queryResults && (
                      <div className="answer-section">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                          <AILabel size="sm">
                            <AILabelContent>
                              <div>
                                <p className="secondary">AI Generated</p>
                                <p className="secondary">Hybrid AI Response</p>
                              </div>
                            </AILabelContent>
                          </AILabel>
                        </div>
                        
                        {/* AI Services Attribution */}
                        {queryResults.ai_services_used && queryResults.ai_services_used.length > 0 && (
                          <div className="ai-services">
                            <div className="ai-services__tags">
                              <span className="ai-services__label">AI Services:</span>
                              {queryResults.ai_services_used.map((service, idx) => {
                                // Map service names to display names and colors
                                const serviceConfig = {
                                  'watsonx_assistant': { label: 'watsonx Assistant', type: 'blue' },
                                  'opensearch': { label: 'OpenSearch Vector DB', type: 'teal' },
                                  'llm': { label: queryResults.llm_model === 'granite' ? 'Granite LLM' : 'TinyLlama', type: 'purple' }
                                };
                                const config = serviceConfig[service] || { label: service, type: 'gray' };
                                return (
                                  <Tag key={idx} type={config.type} size="sm">
                                    {config.label}
                                  </Tag>
                                );
                              })}
                            </div>
                            <div className="processing-method">
                              <Tag type="outline" size="sm">
                                {queryResults.processing_method === 'nlp_intent_detection' && 'NLP Intent Detection'}
                                {queryResults.processing_method === 'hybrid_table_lookup' && 'Hybrid: Direct Table Lookup (No LLM)'}
                                {queryResults.processing_method === 'full_rag_generation' && 'Full RAG with LLM Generation'}
                              </Tag>
                            </div>
                          </div>
                        )}
                        
                        {/* Check if clarification is needed */}
                        {queryResults.clarification_options && queryResults.clarification_options.length > 0 ? (
                          <div>
                            <Layer withBackground>
                              <Tile className="clarification-tile">
                                <p>{queryResults.content}</p>
                              </Tile>
                            </Layer>
                            <Select
                              id="clarification-select"
                              labelText="Please select an option:"
                              value={selectedClarification}
                              onChange={(e) => handleClarificationSelect(e.target.value)}
                              className="clarification-select"
                            >
                              <SelectItem value="" text="Choose an option..." />
                              {queryResults.clarification_options.map((opt, idx) => (
                                <SelectItem key={idx} value={opt.value} text={opt.label} />
                              ))}
                            </Select>
                          </div>
                        ) : (
                          <>
                            {/* Display Features with detail view - for both activation and physical feature queries */}
                            {(queryResults.query_type === 'activation_lookup' || queryResults.query_type === 'physical_feature_lookup') && queryResults.features ? (
                              <>
                                {/* Display source URL if available */}
                                {queryResults.source_url && (
                                  <Tile className="source-tile">
                                    <h5 className="source-tile__heading">Source:</h5>
                                    <a
                                      href={queryResults.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="source-tile__link"
                                    >
                                      {queryResults.source_filename || queryResults.source_url}
                                    </a>
                                    <p className="source-tile__helper">
                                      Click to verify this information in the original IBM Sales Manual
                                    </p>
                                  </Tile>
                                )}
                                
                                <FeaturesView
                                  features={queryResults.features}
                                  serverModel={queryResults.server_model || selectedServer?.model || 'Unknown Server'}
                                />
                              </>
                            ) : (
                              <>
                                {/* Standard answer display for non-activation queries */}
                                <Layer withBackground>
                                  <Tile className="answer-tile">
                                    <div
                                      style={{ whiteSpace: 'pre-line' }}
                                      dangerouslySetInnerHTML={{ __html: queryResults.content || queryResults.answer }}
                                    />
                                  
                                    {/* Show response time for table lookups */}
                                    {queryResults.response_time_ms && (
                                      <div className="response-time">
                                        Response time: {queryResults.response_time_ms}ms
                                      </div>
                                    )}
                                  </Tile>
                                </Layer>
                                
                                {/* Display table data if available (for table lookups) */}
                                {queryResults.table_data && (
                                  <Layer withBackground>
                                    <Tile className="table-tile">
                                      <h5 className="table-tile__heading">Lifecycle Table from Sales Manual:</h5>
                                      <pre className="table-tile__content">
                                        {queryResults.table_data}
                                      </pre>
                                    </Tile>
                                  </Layer>
                                )}
                                
                                {/* Display source URL if available */}
                                {queryResults.source_url && (
                                  <Tile className="source-tile">
                                    <h5 className="source-tile__heading">Source:</h5>
                                    <a
                                      href={queryResults.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="source-tile__link"
                                    >
                                      {queryResults.source_filename || queryResults.source_url}
                                    </a>
                                    <p className="source-tile__helper">
                                      Click to verify this information in the original IBM Sales Manual
                                    </p>
                                  </Tile>
                                )}
                              </>
                            )}
                          </>
                        )}
                        
                        {queryResults.sources && (
                          <div style={{ marginTop: '1rem' }}>
                            <h5>Sources:</h5>
                            {queryResults.sources.map((source, idx) => (
                              <Tile key={idx} style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                                {source}
                              </Tile>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </Tile>
                </Column>
              </Grid>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </Column>
      
      {/* Server Details Modal */}
      <Modal
        open={showDetailsModal}
        onRequestClose={() => setShowDetailsModal(false)}
        modalHeading={selectedServer ? `${selectedServer.model} Details` : 'Server Details'}
        passiveModal
      >
        {selectedServer && (
          <div>
            <p className="details-modal__text"><strong>Full Name:</strong> {selectedServer.name}</p>
            <p className="details-modal__text"><strong>MTM:</strong> {selectedServer.mtm}</p>
            <p className="details-modal__text"><strong>Processor:</strong> {selectedServer.processor}</p>
            <p className="details-modal__text"><strong>Category:</strong> {selectedServer.category}</p>
            <p className="details-modal__text"><strong>Status:</strong> {selectedServer.status}</p>
            <p className="details-modal__text"><strong>Document Count:</strong> {selectedServer.documentCount}</p>
            <p className="details-modal__text"><strong>Last Updated:</strong> {selectedServer.lastUpdated || 'Never'}</p>
            <p className="details-modal__text"><strong>Content Hash:</strong> {selectedServer.contentHash || 'Not calculated'}</p>
            <p className="details-modal__text"><strong>Sales Manual URL:</strong></p>
            <a href={selectedServer.url} target="_blank" rel="noopener noreferrer" className="details-modal__link">
              {selectedServer.url}
            </a>
          </div>
        )}
      </Modal>
    </Grid>
  );
}

// Made with Bob
