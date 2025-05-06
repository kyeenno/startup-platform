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
    const [name, setName] = useState('');
    const [surname, setSurname] = useState('');
    const [success, setSuccess] = useState(false);
    const [err, setErr] = useState({});

    // Submit form
    const submit = async (e) => {
        e.preventDefault();
        setErr({});

        try {
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
                        user_id: data.user_id,
                        user_name: name,
                        user_surname: surname,
                        email: email
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
            router.push('/dashboard');

        } catch (err) {
            setErr({ form: err.message });
        }
    };

    return success ? (
        <Success />
    ) : (
        <div>
            <h1 className="text-center mb-8 text-xl text-white">Create an account</h1>
            <form className="w-sm mx-auto flex flex-col justify-center" onSubmit={submit}>
                <div>
                    <div className="mb-5">
                        <label htmlFor="name" className="block mb-2 text-sm font-medium text-white">Your email</label>
                        <InputForm
                            type="text"
                            id="name"
                            placeholder="John"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            required
                        />
                    </div>
                    <div className="mb-5">
                        <label htmlFor="surname" className="block mb-2 text-sm font-medium text-white">Your email</label>
                        <InputForm
                            type="text"
                            id="surname"
                            placeholder="Doe"
                            value={surname}
                            onChange={(e) => setSurname(e.target.value)}
                            required
                        />
                    </div>
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