"use client";
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function ConnectSources() {
    const { projectId } = useParams();
    const { user, loading: authLoading, session } = useAuth();
    const [sources, setSources] = useState({
        google_analytics: false,
        stripe: false,
    });
    const [loading, setLoading] = useState(true);
    const [updating, setUpdating] = useState(false);
    const [error, setError] = useState(null);
    const [message, setMessage] = useState(null);

    const fetchConnections = useCallback(async () => {
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
            console.error("Error fetching projects:", err);
            setError("Failed to load connection status");
        } finally {
            setLoading(false);
        }
    }, [user, projectId]);

    useEffect(() => {
        fetchConnections();
    }, [fetchConnections]);

    useEffect(() => {
        // Handle redirect from OAuth process
        if (typeof window !== 'undefined') {
            const params = new URLSearchParams(window.location.search);
            const connection = params.get('connection');
            const message = params.get('message');
            
            if (connection === 'success') {
                // Show success message and refresh connection status
                setMessage({ type: 'success', text: 'Connection successful!' });
                // Refresh your connections data
                fetchConnections();
            } else if (connection === 'error') {
                // Show error message
                setError(message || 'Connection failed');
            }
            
            // Clear the URL parameters
            if (connection) {
                const url = new URL(window.location);
                url.search = '';
                window.history.replaceState({}, '', url);
            }
        }
    }, [fetchConnections]);

    async function connectGoogleAnalytics() {
        if (!user || !projectId) return;

        try {
            setUpdating(true);
            setError(null);

            console.log("Connecting Google Analytics for project:", projectId);
            console.log("Session token:", session?.access_token ? "Present" : "Missing");

            // Add projectId to the request URL
            const response = await fetch(`/api/google/auth-url?project_id=${projectId}`, {
                headers: {
                    'Authorization': `Bearer ${session?.access_token || ''}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log("Response status:", response.status);
            
            const data = await response.json();
            console.log("Response data:", data);

            if (!response.ok) {
                throw new Error(data.message || 'Failed to get Google Auth URL');
            }

            // Redirect to Google OAuth page
            if (data.auth_url) {
                console.log("Redirecting to Google OAuth:", data.auth_url);
                window.location.href = data.auth_url;
            } else {
                throw new Error('No auth URL returned');
            }

        } catch (err) {
            console.error("Error connecting Google Analytics:", err);
            setError(err.message || 'An unknown error occurred');
        } finally {
            setUpdating(false);
        }
    }

    async function connectStripe() {
        if (!projectId || !user) return;

        try {
            setUpdating(true);
            setError(null);

            console.log("Connecting Stripe for project:", projectId);
            console.log("Session token:", session?.access_token ? "Present" : "Missing");

            // Call your backend to get Stripe Auth URL
            const response = await fetch(`/api/stripe/auth-url?project_id=${projectId}`, {
                headers: {
                    'Authorization': `Bearer ${session?.access_token || ''}`,
                    'Content-Type': 'application/json'
                }
            });

            console.log("Stripe auth response status:", response.status);
            
            const data = await response.json();
            console.log("Stripe auth response data:", data);

            if (!response.ok) {
                throw new Error(data.message || 'Failed to get Stripe Auth URL');
            }

            // Redirect to Stripe OAuth page
            if (data.auth_url) {
                console.log("Redirecting to Stripe OAuth:", data.auth_url);
                window.location.href = data.auth_url;
            } else {
                throw new Error('No auth URL returned');
            }

        } catch (err) {
            console.error("Error connecting Stripe:", err);
            setError(err.message || 'An unknown error occurred');
        } finally {
            setUpdating(false);
        }
    }

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

    if (!user) return (
        <p>Please <Link href="/auth/signin" className="hover:underline">sign in</Link> to connect data sources.</p>
    );

    return (
        <div className="p-6 max-w-2xl mx-auto bg-white rounded-lg shadow-md m-4">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Connect Data Sources</h2>
            {error && (
                <div className="mb-6 p-3 bg-red-100 text-red-700 rounded border border-red-300">
                    {error}
                </div>
            )}
            {message && message.type === 'success' && (
                <div className="mb-6 p-3 bg-green-100 text-green-700 rounded border border-green-300">
                    {message.text}
                </div>
            )}
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
                    </div>

                    <button
                        onClick={connectGoogleAnalytics}
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
                    </div>

                    <button
                        onClick={connectStripe}
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