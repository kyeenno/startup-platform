"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function ConnectSources() {
    const { projectId } = useParams();
    const { user, loading: authLoading } = useAuth();
    const [sources, setSources] = useState({
        google_analytics: false,
        stripe: false,
    });
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchConnections() {
            if (!user || !projectId) return;

            try {
                setLoading(true);
                setError(null);

                const { data, error } = await supabase
                    .from('projects')
                    .select('google_analytics, stripe')
                    .eq('project_id', projectId)
                    .single();

                if (error) throw error;

                if (data) {
                    setSources({
                        google_analytics: data.google_analytics || false,
                        stripe: data.stripe || false
                    });
                }
            } catch (err) {
                console.err("Error fetching projects:", err);
            } finally {
                setLoading(false);
            }
        }

        fetchConnections();
    }, [projectId, user]);

    const handleGoogleAnalyticsConnect = async () => {
        if (!user || !projectId || updating) return;
        
        setUpdating(true);
        try {
            // Get session token
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) throw new Error('Not authenticated');
    
            // Call backend directly to get auth URL
            const response = await fetch(`http://localhost:8000/google/auth-url?project_id=${projectId}`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json',
                },
            });
    
            const data = await response.json();
            
            if (data.auth_url) {
                // Redirect to Google OAuth
                window.location.href = data.auth_url;
            } else {
                throw new Error(data.message || 'Failed to get auth URL');
            }
        } catch (error) {
            console.error('Error connecting Google Analytics:', error);
            setError('Failed to connect Google Analytics');
        } finally {
            setUpdating(false);
        }
    };
    
    const handleStripeConnect = async () => {
        if (!user || !projectId || updating) return;
        
        setUpdating(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) throw new Error('Not authenticated');
    
            console.log('Making Stripe request...');
            
            const response = await fetch(`http://localhost:8000/stripe/auth-url?project_id=${projectId}`, {
                headers: {
                    'Authorization': `Bearer ${session.access_token}`,
                    'Content-Type': 'application/json',
                },
            });
    
            console.log('Stripe response status:', response.status);
            console.log('Stripe response ok:', response.ok);
            
            const data = await response.json();
            console.log('Stripe response data:', data);
            
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                throw new Error(data.message || 'Failed to get auth URL');
            }
        } catch (error) {
            console.error('Error connecting Stripe:', error);
            setError('Failed to connect Stripe');
        } finally {
            setUpdating(false);
        }
    };

    if (authLoading || loading) {
        return (
            <div className="p-6 max-w-2xl mx-auto">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-gray-700 rounded w-1/3"></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="h-48 bg-gray-700 rounded"></div>
                        <div className="h-48 bg-gray-700 rounded"></div>
                    </div>
                </div>
            </div>
        );
    }

    if (authLoading || loading) return <p>Loading...</p>;
    if (!user) return (
        <p>Please <Link href="/auth/signin" className="hover:underline">sign in</Link> to connect data sources.</p>
    );

    return (
        <div className="p-6 max-w-2xl mx-auto bg-white rounded-lg shadow-md m-4">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Connect Data Sources</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Google Analytics Card */}
                <div className="p-4 rounded-lg flex flex-col h-full border border-gray-300">
                    <div className="flex-grow">
                        <div className="flex items-center justify-center mb-4">
                            <Image
                                width={150}
                                height={0}
                                src="/ga-icon-white.png"
                                alt="Google Analytics logo"
                            />
                        </div>
                        
                        {/* Add this connection status display */}
                        {sources.google_analytics && (
                            <div className="mb-4 p-2 bg-green-100 text-green-700 rounded text-center text-sm">
                                ✅ Connected successfully
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleGoogleAnalyticsConnect}
                        disabled={updating}
                        className={`mt-auto w-full px-4 py-2 rounded font-medium ${updating
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        } transition-colors`}
                    >
                        {updating ? 'Connecting...' : sources.google_analytics ? 'Reconnect' : 'Connect'}
                    </button>
                </div>

                {/* Stripe Card */}
                <div className="p-4 rounded-lg flex flex-col h-full border border-gray-300">
                    <div className="flex-grow">
                        <div className="flex items-center justify-center mb-4">
                            <Image
                                width={150}
                                height={0}
                                src="/stripe-icon-purple.svg"
                                alt="Stripe logo"
                            />
                        </div>
                        
                        {/* Add this connection status display */}
                        {sources.stripe && (
                            <div className="mb-4 p-2 bg-green-100 text-green-700 rounded text-center text-sm">
                                ✅ Connected successfully
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleStripeConnect}
                        disabled={updating}
                        className={`mt-auto w-full px-4 py-2 rounded font-medium ${updating
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        } transition-colors`}
                    >
                        {updating ? 'Connecting...' : sources.stripe ? 'Reconnect' : 'Connect'}
                    </button>
                </div>
            </div>
        </div>
    );
}