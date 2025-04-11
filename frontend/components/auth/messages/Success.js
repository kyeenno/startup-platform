"use client";
import Link from "next/link";

export default function Success() {
    return (
        <div className="flex flex-col justify-center items-center">
            <p>{`We've sent a confirmation link to your email address. Please check your inbox and click the link to confirm your account.`}</p>
            <p>After confirming, you can <Link href="/auth/signin" className="underline hover:text-gray-400">sign in to proceed</Link>.</p>
        </div>
    );
}