import { NextResponse } from 'next/server';
import { createRouteHandlerClient } from '@supabase/auth-helpers-nextjs';
import { cookies } from 'next/headers';

export async function GET(request) {
  try {
    console.log("Google Analytics auth URL endpoint hit");
    const { searchParams } = new URL(request.url);
    const projectId = searchParams.get('project_id');

    if (!projectId) return NextResponse.json({ error: 'Missing project ID' }, { status: 404 });

    // Get cookies
    const cookieStore = cookies();
    const supabase = createRouteHandlerClient({ cookies: () => cookieStore });

    // Get session
    const { data: { session } } = await supabase.auth.getSession();

    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // Call your backend service for Google Analytics
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const endpoint = `${backendUrl}/google/auth-url?project_id=${projectId}`;
    console.log('Backend endpoint:', endpoint);

    try {
      const response = await fetch(endpoint, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error('Failed to parse data as JSON:', error);
    }
    
    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Error getting Google Analytics auth URL:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}