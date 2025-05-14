'use client';
import Link from "next/link";
import { supabase } from '../../../lib/supabaseClient';
import { useState } from "react";
import { useRouter } from "next/navigation";
import InputForm from "../../ui/InputForm";

const SignIn = () => {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [err, setErr] = useState({});

    const submit = async (e) => {
        e.preventDefault();
        setErr({});
        setLoading(true);

        try {
            const { data, error } = await supabase.auth.signInWithPassword({ email, password });
            if (error) throw error;

            // Redirect to the data source connection page
                router.push('/profile/dashboard');

        } catch (err) {
            console.error("Sign in error", err);
            setErr({ form: err.message });
            setLoading(false);
        }
    };

    return (
        <div>
            <h1 className="text-center mb-8 text-xl">Log in as an existing user</h1>
            <form className="w-sm mx-auto flex flex-col justify-center" onSubmit={submit}>
                <div>
                    <div className="mb-5">
                        <label htmlFor="email" className="block mb-2 text-sm font-medium text-white">Your email</label>
                        <InputForm
                            type="email"
                            id="email"
                            placeholder="johndoe@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div className="mb-5">
                        <label htmlFor="password" className="block mb-2 text-sm font-medium text-white">Your password</label>
                        <InputForm
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <div className="flex items-start mb-5">
                        <p className="text-gray-400">
                            Not a user? <Link href="/auth/signup" className="hover:underline hover:text-gray-300 transition duration-150 ease-in-out">Create an account.</Link>
                        </p>
                    </div>
                </div>
                <button type="submit" className="transition duration-150 ease-in-out cursor-pointer text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm w-full sm:w-auto px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">Submit</button>
            </form>
        </div>
    );
}

export default SignIn;