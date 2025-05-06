'use client';
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";

export default function Navbar() {
    const { user, loading } = useAuth();

    const handleLogout = async () => {
        try {
            await supabase.auth.signOut();
        } catch (err) {
            console.error("Error logging out with supabase auth", err);
        }
    };

    return (
        <div className="text-white px-4 py-2 mx-4 mt-4">
            <div className="bg-[#131615] backdrop-blur-sm bg-[#2a4d69] border border-white/30 rounded-2xl shadow-md">
                <ul className="flex justify-between px-6 py-3 gap-6">
                    {/* Always visible links */}
                    <li className="mr-auto hover:underline transition duration-150 ease-in-out cursor-pointer">
                        <Link href="/">Home</Link>
                    </li>
                    
                    {/* Conditional links based on auth state */}
                    {loading ? (
                        <li>Loading...</li>
                    ) : user ? (
                        <>
                            {/* Links for logged in users */}
                            <li className="hover:underline transition duration-150 ease-in-out cursor-pointer">
                                <Link href="/dashboard">Dashboard</Link>
                            </li>
                            <li className="hover:underline transition duration-150 ease-in-out cursor-pointer">
                                <Link href="/connect">Connect Data</Link>
                            </li>
                            <li className="hover:underline transition duration-150 ease-in-out cursor-pointer">
                                <button onClick={handleLogout}>Log out</button>
                            </li>
                        </>
                    ) : (
                        <>
                            {/* Links for logged out users */}
                            <li className="hover:underline transition duration-150 ease-in-out cursor-pointer">
                                <Link href="/auth/signin">Sign in</Link>
                            </li>
                            <li className="hover:underline transition duration-150 ease-in-out cursor-pointer">
                                <Link href="/auth/signup">Create an account</Link>
                            </li>
                        </>
                    )}
                </ul>      
            </div>

        </div>
    );
}