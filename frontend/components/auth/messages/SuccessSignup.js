import Link from "next/link";

export default function SuccessSignup() {
    return (
    <div className="w-sm mx-auto flex flex-col justify-center">
        <div className="bg-black border border-gray-300 rounded-lg text-center p-6">
            <h2 className="text-2xl font-bold mb-4">Sign Up Successful!</h2>
            <p className="mb-4">Please check your email to confirm your account.</p>
            {/* <Link 
                href="/auth/signin"
                className="hover:underline text-gray-400 transition duration-150 ease-in-out"
            >
                Go to Sign In
            </Link> */}
        </div>
    </div>
    );
};