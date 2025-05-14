'use client';

import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function NewProject() {
    const [name, setName] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const { user } = useAuth();
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!name.trim()) {
            setError('Please set a name for your project!');
            return;
        }

        if (!user) {
            setError('Please log in before proceeding');
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const { data, error: creatingError } = await supabase
                .from('projects')
                .insert({
                    project_name: name.trim(),
                    user_id: user.id,
                    created_at: new Date().toISOString()
                })
                .select()
                .single();

            if (creatingError) throw creatingError;
            console.log('Project:', data);

            const { error: relationError } = await supabase
                .from('project_to_user')
                .insert({
                    project_id: data.project_id,
                    user_id: user.id
                });

            if (relationError) throw relationError;

            setSuccess(true);

            setTimeout(() => {
                router.push(`/profile/projects/${data.project_id}`);
            }, 1500);
        } catch (err) {
            console.error('Error creating project:', error);
            setError(err.message || 'Failed to create project');
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="container mx-auto py-10 max-w-5xl bg-white p-6 m-4 rounded-lg shadow-md">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">Create a New Project</h1>
            <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                    <label htmlFor="projectName" className="block text-sm font-medium text-gray-700 mb-2">Project Name</label>
                    <input
                        type="text"
                        id="projectName"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                        placeholder="Enter project name"
                        required
                    />
                </div>
                <div className="flex justify-end">
                    <button
                        type="submit"
                        disabled={submitting}
                        className={`px-4 py-2 rounded-md font-medium ${submitting
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700 text-white'
                        } transition-colors`}
                    >
                        {submitting ? 'Creating...' : 'Create Project'}
                    </button>
                </div>
            </form>
        </div>
    );
}