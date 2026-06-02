/**
 * Next.js API Route - Proxy for RAG Backend Ingest Sales Manual
 * Forwards individual server ingestion requests to backend
 */

// Increase timeout for scraping and ingestion (can take 5-10 minutes)
export const maxDuration = 600; // 10 minutes

export async function POST(request) {
  try {
    const body = await request.json();
    
    console.log('[Ingest API] Forwarding request to backend:', {
      mtm: body.mtm,
      server_model: body.server_model
    });
    
    // Use internal OpenShift service name
    const backendUrl = process.env.RAG_BACKEND_URL || 'http://rag-backend:8080';
    
    // Forward request to backend
    const response = await fetch(`${backendUrl}/api/ingest-sales-manual`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Ingest API] Backend error:', response.status, errorText);
      return Response.json(
        { error: `Backend error: ${response.status} - ${errorText}` },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    console.log('[Ingest API] Success:', data);
    
    return Response.json(data, { status: 200 });
  } catch (error) {
    console.error('[Ingest API] Error:', error);
    return Response.json(
      { error: error.message || 'Failed to ingest' },
      { status: 500 }
    );
  }
}

// Made with Bob

// Made with Bob
