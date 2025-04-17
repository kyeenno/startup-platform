"use client";
import Link from "next/link";

export default function HomePage() {
  return (
    <div className="m-8 gap-2 text-white">
      <h1 className="text-center mt-8 text-5xl text-white">Routes</h1>
      <p className="mb-8">{`This is the default "/" route.`}</p>
      <div>
        <Link href="/auth/signup" className="hover:underline">Go to Sign Up page</Link>
        <br />
        <Link href="/auth/signin" className="hover:underline">Go to Sign In page</Link>
        <br />
        <Link href="/dashboard" className="hover:underline">Go to Dashboard</Link>
        <br />
        <Link href="/connect" className="hover:underline">Go to Connect Sources</Link>
        <br />
      </div>
    </div>
  );
}
