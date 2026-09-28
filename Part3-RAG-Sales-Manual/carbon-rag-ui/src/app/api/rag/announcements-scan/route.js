/**
 * Next.js API Route - Scan IBM Power Announcements
 */

export async function POST(request) {
  try {
    const backendUrl = process.env.RAG_BACKEND_URL || 'http://rag-backend:8080';
    
    const response = await fetch(`${backendUrl}/api/announcements/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }
    
    const data = await response.json();
    return Response.json(data, { status: 200 });
  } catch (error) {
    console.error('Error scanning announcements:', error);
    return Response.json(
      { error: error.message || 'Failed to scan announcements' },
      { status: 500 }
    );
  }
}
