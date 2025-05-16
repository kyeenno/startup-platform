"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import Image from "next/image";
import { useRouter, useParams, useSearchParams } from "next/navigation";

export default function ConnectSources() {
    const params = useParams();
    const router = useRouter();
    const searchParams = useSearchParams();
    const { user, loading: authLoading, session } = useAuth();
    const [sources, setSources] = useState({
        google_analytics: false,
        stripe: false,
    });
    const [loading, setLoading] = useState(false);
    const [updating, setUpdating] = useState(false);
    const [error, setError] = useState(null);

    const projectId =
        params?.projectId ||
        searchParams?.get('project_id') ||
        (typeof router.query === 'object' ? router.query.project_id : null);

    console.log('Project ID param:', projectId);

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

    const connectGA = async () => {
        if (!user || !projectId) return;

        try {
            setUpdating(true);
            console.log('Projects:', `${projectId}`);

            const { data: sessionData } = await supabase.auth.getSession();
            if (!sessionData?.session) {
                throw new Error("No active session");
            }

            // Calling the API route
            const response = await fetch(`/api/google-analytics/auth-url?project_id=${projectId}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${sessionData.session.access_token}`,
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();
            console.log('Auth data received:', data);

            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                console.log("No auth URL");
            }
        } catch (error) {
            console.error('Error connecting:', error);
            setError(`${error.message}`);
        } finally {
            setUpdating(false);
        }
    };

    console.log({
        "params": params,
        "searchParams": Object.fromEntries([...searchParams]),
        "projectId": projectId
    });

    if (authLoading || loading) {
        return (
            <div className="p-6 max-w-2xl mx-auto">
                <div className="animate-pulse space-y-4">
                    <div className="h-8 bg-gray-700 rounded w-1/3"></div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="h-48 bg-gray-700 rounded"></div>
                        <div className="h-48 bg-gray-700 rounded"></div>
                        <p className="text-xs text-gray-500">
                            {projectId ? `Connected to project: ${projectId}` : "No project selected"}
                        </p>
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
                    </div>

                    <button
                        onClick={connectGA}
                        disabled={updating}
                        className={`mt-auto w-full px-4 py-2 rounded font-medium ${updating
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                            } transition-colors`}
                    >
                        {updating ? 'Updating...' : sources.google_analytics ? 'Reconnect' : 'Connect'}
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
                        disabled={updating}
                        className={`mt-auto w-full px-4 py-2 rounded font-medium ${updating
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                            } transition-colors`}
                    >
                        {updating ? 'Updating...' : sources.stripe ? 'Reconnect' : 'Connect'}
                    </button>
                </div>
            </div>
        </div>
    );
}