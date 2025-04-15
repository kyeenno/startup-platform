'use client';
import Link from "next/link";
import { supabase } from '../../lib/supabaseClient';
import { useRouter } from "next/navigation";
import { useState } from "react";
import InputForm from "../ui/InputForm";
import Success from "./messages/Success";

const SignUp = () => {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [success, setSuccess] = useState(false);
    const [err, setErr] = useState({});

    // Submit form
    const submit = async (e) => {
        e.preventDefault();
        setErr({});

        try {
            const { data, error } = await supabase.auth.signUp({ email, password });
            if (error) throw error;

            // Set status if authenticated succesfully
            setSuccess(true);

            // Clear form fields
            setEmail('');
            setPassword('');

            // Redirect to the dashboard
            router.push('/dashboard');

        } catch (err) {
            setErr({ form: err.message });
        }
    };

    return success ? (
        <Success />
    ) : (
        <div className="m-8">
            <h1 className="text-center mb-8 text-xl text-white">Create an account</h1>
            <form className="w-sm mx-auto flex flex-col justify-center" onSubmit={submit}>
                <div>
                    <div className="mb-5">
                        <label htmlFor="email" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">Your email</label>
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
                        <label htmlFor="password" className="block mb-2 text-sm font-medium text-gray-900 dark:text-white">Your password</label>
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
                            Existing user? <Link href="/auth/signin" className="hover:underline hover:text-gray-300 transition duration-150 ease-in-out">Sign in instead.</Link>
                        </p>
                    </div>
                </div>
                <button type="submit" className="transition duration-150 ease-in-out cursor-pointer text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm w-full sm:w-auto px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800">Create</button>
            </form>
        </div>
    );
}

export default SignUp;