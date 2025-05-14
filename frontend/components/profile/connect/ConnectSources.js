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
                    </div>

                    <button
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