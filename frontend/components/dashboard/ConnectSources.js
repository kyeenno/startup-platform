"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";
import Image from "next/image";

export default function ConnectSources() {
    const { user, loading: authLoading } = useAuth();
    const [sources, setSources] = useState({
        google_analytics: false,
        stripe: false,
    });
    const [loading, setLoading] = useState(true);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        if (user) {
            fetchSources(user.id);
            setLoading(false);
        } else if (!authLoading) {
            setLoading(false);
        }
    }, [user, authLoading]);

    const fetchSources = async (userId) => {
        try {
            const response = await fetch(`http://localhost:8000/api/user/connected-sources?userId=${userId}`);
            if (response.ok) {
                const data = await response.json();
                setSources(data.source);
            }
        } catch (err) {
            console.error("Error fetching srces:", err);
        }
    };

    const connectGA = () => {
        if (user) {
            window.location.href = `http://localhost:8000/api/connect/google-analytics?userId=${user.id}`;
        }
    };

    const connectStripe = () => {
        if (user) {
            window.location.href = `http://localhost:8000/api/connect/stripe?userId=${user.id}`;
        }
    };

    // Validate if the user is logged in
    if (authLoading || loading) return <p>Loading...</p>;
    if (!user) return (
        <p>Please <Link href="/auth/signin" className="hover:underline">sign in</Link> to connect data sources.</p>
    );

    return (
        <div className="p-6 max-w-2xl mx-auto text-center">
            <h2 className="text-2xl font-bold text-white mb-6">Connect Data Sources</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Google Analytics Card */}
                    <div className="p-4 rounded-lg flex flex-col h-full border border-white/30 rounded-lg">
                        <div className="flex-grow">
                            <div className="flex items-center justify-center mb-4">
                                <Image 
                                    width={150}
                                    height={0}
                                    src="/ga-icon-white.png"
                                    alt="Google Analytics logo"
                                />
                            <div className={`rounded-full w-3 h-3 ${sources.google_analytics ? 'bg-green-500' : 'bg-red-500'}`}></div>
                        </div>
                    </div>

                    <button
                        onClick={connectGA}
                        className="mt-auto w-full bg-[#2563EB] hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {sources.google_analytics ? 'Reconnect' : 'Connect'}
                    </button>
                </div>

                {/* Stripe Card */}
                <div className="border border-white/30 rounded-lg p-4 rounded-lg flex flex-col h-full">
                    <div className="flex-grow">
                        <div className="flex items-center justify-center mb-4">
                            <Image 
                                width={150}
                                height={0}
                                src="/stripe-icon-purple.svg"
                                alt="Google Analytics logo"
                            />
                        <div className={`rounded-full w-3 h-3 ${sources.google_analytics ? 'bg-green-500' : 'bg-red-500'}`}></div>
                        </div>
                    </div>

                    <button
                        onClick={connectStripe}
                        className="mt-auto w-full bg-[#2563EB] hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {sources.google_analytics ? 'Reconnect' : 'Connect'}
                    </button>
                </div>
            </div>
        </div>
    );
}