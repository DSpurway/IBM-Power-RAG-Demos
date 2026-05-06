/**
 * Next.js API Route - Bulk Ingestion of All Sales Manuals
 * Triggers ingestion of all 26 IBM Power server Sales Manuals
 * This is a long-running operation that will take several hours
 */

// IBM Power server configuration - Same as in sales-manual/page.js
// Ordered by processor generation (POWER11, POWER10, POWER9)
// Within each generation: Enterprise first, then Scale-out, then others (largest numbers first)
const IBM_POWER_SERVERS = [
  // POWER11 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest)
  { model: "E1180", name: "IBM Power E1180", processor: "POWER11" },
  { model: "E1150", name: "IBM Power E1150", processor: "POWER11" },
  { model: "S1124", name: "IBM Power S1124", processor: "POWER11" },
  { model: "S1122", name: "IBM Power S1122", processor: "POWER11" },
  // POWER10 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest), then Linux (largest to smallest)
  { model: "E1080", name: "IBM Power E1080", processor: "POWER10" },
  { model: "E1050", name: "IBM Power E1050", processor: "POWER10" },
  { model: "S1024", name: "IBM Power S1024", processor: "POWER10" },
  { model: "S1022", name: "IBM Power S1022", processor: "POWER10" },
  { model: "S1014", name: "IBM Power S1014", processor: "POWER10" },
  { model: "S1012", name: "IBM Power S1012", processor: "POWER10" },
  { model: "L1024", name: "IBM Power L1024", processor: "POWER10" },
  { model: "L1022", name: "IBM Power L1022", processor: "POWER10" },
  // POWER9 Servers - Enterprise first (largest to smallest), then Scale-out (largest to smallest), then others (largest to smallest)
  { model: "E980", name: "IBM Power System E980", processor: "POWER9" },
  { model: "E950", name: "IBM Power System E950", processor: "POWER9" },
  { model: "S924", name: "IBM Power System S924", processor: "POWER9" },
  { model: "S924-G", name: "IBM Power System S924", processor: "POWER9" },
  { model: "S922", name: "IBM Power System S922", processor: "POWER9" },
  { model: "S922-G", name: "IBM Power System S922", processor: "POWER9" },
  { model: "S914", name: "IBM Power System S914", processor: "POWER9" },
  { model: "S914-G", name: "IBM Power System S914", processor: "POWER9" },
  { model: "H924", name: "IBM Power System H924", processor: "POWER9" },
  { model: "H922", name: "IBM Power System H922", processor: "POWER9" },
  { model: "IC922", name: "IBM Power System IC922", processor: "POWER9" },
  { model: "L922", name: "IBM Power System L922", processor: "POWER9" },
  { model: "LC922", name: "IBM Power System LC922", processor: "POWER9" },
  { model: "LC921", name: "IBM Power System LC921", processor: "POWER9" },
];

export async function POST(request) {
  try {
    const backendUrl = process.env.RAG_BACKEND_URL || 'http://rag-backend:8080';
    
    console.log(`[Bulk Ingestion API] Calling backend to start bulk ingestion`);
    
    // Call the backend's bulk ingestion endpoint
    // The backend will handle all the looping and processing
    const response = await fetch(`${backendUrl}/api/start-bulk-ingestion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || 'Failed to start bulk ingestion');
    }
    
    const data = await response.json();
    
    console.log(`[Bulk Ingestion API] Backend started bulk ingestion: ${data.message}`);
    
    return Response.json(data, {
      status: 200,
      headers: {
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
      }
    });
  } catch (error) {
    console.error('[Bulk Ingestion API] Error:', error);
    return Response.json(
      { 
        error: error.message || 'Failed to start bulk ingestion',
        total: IBM_POWER_SERVERS.length,
        started: [],
        failed: []
      },
      { status: 500 }
    );
  }
}

// Made with Bob