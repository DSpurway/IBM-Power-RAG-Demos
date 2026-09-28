/**
 * Next.js API Route - Ingest IBM Power Announcements
 */

export async function POST(request) {
  try {
    const backendUrl = process.env.RAG_BACKEND_URL || 'http://rag-backend:8080';
    const body = await request.json().catch(() => ({}));
    
    const response = await fetch(`${backendUrl}/api/announcements/ingest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    
    const data = await response.json();
    return Response.json(data, { status: 200 });
  } catch (error) {
    console.error('Error ingesting announcements:', error);
    return Response.json(
      { error: error.message || 'Failed to ingest announcements' },
      { status: 500 }
    );
  }
}
