"use client";
import { useAuth } from "@/contexts/AuthContext";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  // Optional auto-redirect to dashboard if already logged in
  useEffect(() => {
    if (user) {
      router.push("/profile/dashboard");
    }
  }, [user, router]);

  return (
    <div className="min-h-screen bg-[#131615] text-white flex justify-center items-center">
      <div className="mx-auto px-4 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl font-bold mb-8">Welcome to Datlee</h1>
          
          <p className="text-xl mb-12">
            Smart notifications that alert you about important changes in your business data.
            Customize frequency and specificity to focus on what matters.
          </p>
          
            <div className="space-x-4">
              {loading ? (
                <div className="animate-pulse">Loading...</div>
              ) : user ? (
                <Link 
                  href="/profile/dashboard" 
                  className="bg-[#63ace5] hover:bg-[#4b86b4] text-white px-8 py-3 rounded-lg font-medium transition-colors"
                >
                  Go to Dashboard
                </Link>
              ) : (
                <>
                  <Link 
                    href="/auth/signin" 
                    className="bg-[#2563EB] hover:bg-[#2563EB] text-white px-8 py-3 rounded-lg transition-colors"
                  >
                    Sign In
                  </Link>
                  
                  <Link 
                    href="/auth/signup" 
                    className="border border-white hover:bg-white hover:text-[#2563EB] px-8 py-3 rounded-lg transition-colors"
                  >
                    Create Account
                  </Link>
                </>
              )}
            </div>
        </div>
      </div>
    </div>
  );
}