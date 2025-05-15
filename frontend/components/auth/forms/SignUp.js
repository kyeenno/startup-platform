'use client';
import Link from "next/link";
import { supabase } from '../../../lib/supabaseClient';
import { useRouter } from "next/navigation";
import { useState } from "react";
import InputForm from "../../ui/InputForm";
import Success from "../messages/Success";

const SignUp = () => {
    const router = useRouter();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [surname, setSurname] = useState('');
    const [success, setSuccess] = useState(false);
    const [err, setErr] = useState({});

    // Submit form
    const submit = async (e) => {
        e.preventDefault();
        setErr({});

        try {

            if (!email || !password || !name || !surname) {
                setErr({ form: "All fields are required" });
                return;
            }

            const { data, error } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: {
                        first_name: name,
                        last_name: surname
                    }
                }
            });

            if (error) throw error;

            // Store data in the Supabase table
            if (data?.user) {
                const { error: profileError } = await supabase
                    .from('user_info')
                    .insert({
                        user_id: data.user.id,
                        user_name: name,
                        user_surname: surname,
                    });

                if (profileError) throw profileError;
            }

            // Set status if authenticated succesfully
            setSuccess(true);

            // Clear form fields
            setEmail('');
            setPassword('');
            setName('');
            setSurname('');

            // Redirect to the dashboard
            router.push('/profile/dashboard');

        } catch (err) {
            console.error("Error", err);
            setErr({ form: err.message });
        }
    };

    return success ? (
        <Success />
    ) : (
        <div className="flex min-h-full flex-col justify-center px-6 py-12 lg:px-8 w-screen">
            <div className="sm:mx-auto sm:w-full sm:max-w-sm">
                <h2 className="mt-10 text-center text-2xl/9 font-bold tracking-tight text-gray-900">Create an account</h2>
            </div>

            <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-sm">
                <form className="space-y-6" onSubmit={submit}>
                    <div>
                        <label htmlFor="name" className="block text-sm/6 font-medium text-gray-900">First Name</label>
                        <div className="mt-2">
                            <input
                                type="text"
                                name="name"
                                id="name"
                                placeholder="John"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                required
                                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-700 sm:text-sm/6"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="surname" className="block text-sm/6 font-medium text-gray-900">Last Name</label>
                        <div className="mt-2">
                            <input
                                type="text"
                                name="surname"
                                id="surname"
                                placeholder="Doe"
                                value={surname}
                                onChange={(e) => setSurname(e.target.value)}
                                required
                                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-700 sm:text-sm/6"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="email" className="block text-sm/6 font-medium text-gray-900">Email address</label>
                        <div className="mt-2">
                            <input
                                type="email"
                                name="email"
                                id="email"
                                placeholder="johndoe@example.com"
                                autoComplete="email"
                                required
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-700 sm:text-sm/6"
                            />
                        </div>
                    </div>

                    <div>
                        <label htmlFor="password" className="block text-sm/6 font-medium text-gray-900">Password</label>
                        <div className="mt-2">
                            <input
                                type="password"
                                name="password"
                                id="password"
                                autoComplete="new-password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="block w-full rounded-md bg-white px-3 py-1.5 text-base text-gray-900 outline-1 -outline-offset-1 outline-gray-300 placeholder:text-gray-400 focus:outline-2 focus:-outline-offset-2 focus:outline-blue-700 sm:text-sm/6"
                            />
                        </div>
                    </div>

                    {err.form && (
                        <div className="py-2 text-red-500">
                            {err.form}
                        </div>
                    )}

                    <div>
                        <button
                            type="submit"
                            className="transition duration-150 ease-in-out cursor-pointer text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm w-full px-5 py-2.5 text-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
                        >
                            Create
                        </button>
                    </div>
                </form>

                <p className="mt-10 text-center text-sm/6 text-gray-500">
                    Existing user?
                    <Link href="/auth/signin" className="font-semibold text-blue-700 hover:text-blue-600"> Sign in instead.</Link>
                </p>
            </div>
        </div>
    );
}

export default SignUp;