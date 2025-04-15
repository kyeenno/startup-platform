"use client";
import { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import Image from "next/image";

export default function ConnectSources() {
    const [user, setUser] = useState(null);
    const [sources, setSources] = useState({
        google_analytics: false,
        stripe: false,
    });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const getUser = async () => {
            const { data } = await supabase.auth.getSession();
            if (data?.session?.user) {
                setUser(data.session.user);
                fetchSources(data.session.user.id);
            }

            setLoading(false);
        };
        getUser();
    }, []);

    const fetchSources = async (userId) => {
        const response = await fetch(`http://localhost:8000/api/user/connected-sources?userId=${userId}`);
        if (response.ok) {
            const data = await response.json();
            setSources(data.source);
        }
    };

    const connectGA = () => {
        window.location.href = `http://localhost:8000/api/connect/google-analytics?userId=${user.id}`;
    };

    const connectStripe = () => {
        window.location.href = `http://localhost:8000/api/connect/stripe?userId=${user.id}`;
    };

    // if (!loading) return <p>Loading...</p>;
    // if (!user) return (
    //     <p>Please <Link href="/auth/signin" className="hover:underline">sign in</Link> to connect data sources.</p>
    // );

    return (
        <div className="p-6 max-w-2xl mx-auto text-center">
            <h2 className="text-2xl font-bold text-white mb-6">Connect Your Data Sources</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Google Analytics Card */}
                    <div className="bg-gray-700 p-4 rounded-lg flex flex-col h-full">
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
                        className="mt-auto w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {sources.google_analytics ? 'Reconnect' : 'Connect'} Google Analytics
                    </button>
                </div>

                {/* Stripe Card */}
                <div className="bg-gray-700 p-4 rounded-lg flex flex-col h-full">
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
                        onClick={connectGA}
                        className="mt-auto w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded transition-colors"
                    >
                        {sources.google_analytics ? 'Reconnect' : 'Connect'} Google Analytics
                    </button>
                </div>
            </div>
        </div>
    );
}