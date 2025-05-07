"use client";
import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";
import Image from "next/image";

export default function ConnectSources() {
    const { user, loading: authLoading } = useAuth();
    // const [sources, setSources] = useState({
    //     google_analytics: false,
    //     stripe: false,
    // });
    const [loading, setLoading] = useState(true);
    // const [connected, setConnected] = useState(false);

    useEffect(() => {
        if (user) {
            // fetchSources(user.id);
            setLoading(false);
        } else if (!authLoading) {
            setLoading(false);
        }
    }, [user, authLoading]);

    // const fetchSources = async (userId) => {
    //     try {
    //         const response = await fetch(`http://localhost:8000/api/user/connected-sources?userId=${userId}`);
    //         if (response.ok) {
    //             const data = await response.json();
    //             setSources(data.source);

    //             // Check if any sources are connected
    //             const connectedSources = Object.values(data.source).some(val => val === true);
    //             setConnected(connectedSources);
    //         }
    //     } catch (err) {
    //         console.error("Error fetching srces:", err);
    //     }
    // };

    // const connectGA = () => {
    //     if (user) {
    //         window.location.href = `http://localhost:8000/api/connect/google-analytics?userId=${user.id}`;
    //     }
    // };

    // const connectStripe = () => {
    //     if (user) {
    //         window.location.href = `http://localhost:8000/api/connect/stripe?userId=${user.id}`;
    //     }
    // };

    // Check connection status after user has been redirected back to Connect Sources page
    // useEffect(() => {
    //     // Set URL params
    //     const urlParams = new URLSearchParams(window.location.search);
    //     const status = urlParams.get('status');
    //     const source = urlParams.get('source');

    //     if (status === 'success' && source) {
    //         // Update source state if connected
    //         setSources(prev => ({
    //             ...prev,
    //             [source]: true
    //         }));
    //         setConnected(true);

    //         // Remove params
    //         window.history.replaceState({}, document.title, window.location.pathname);
    //     }
    // }, []);

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
                        </div>
                    </div>

                    <button
                        // onClick={connectGA}
                        className="mt-auto w-full bg-[#2563EB] hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {/* {sources.google_analytics ? 'Reconnect' : 'Connect'} */}
                        Connect
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
                        </div>
                    </div>

                    <button
                        // onClick={connectStripe}
                        className="mt-auto w-full bg-[#2563EB] hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {/* {sources.stripe ? 'Reconnect' : 'Connect'} */}
                        Connect
                    </button>
                </div>
            </div>
        </div>
    );
}