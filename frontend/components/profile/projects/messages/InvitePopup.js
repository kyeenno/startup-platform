'use client';

import { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function InvitePopup({ projectId, userId }) {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);

    // TODO: implement checking if invited email is valid (exists in supabase)
    const invite = async (e) => {
        e.preventDefault();

        if (!email || !email.includes('@')) {
            setError('Please enter a valid email address');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const { error } = await supabase
                .from('project_invitations')
                .insert({
                    project_id: projectId,
                    invited_by: userId,
                    email: email,
                    status: 'pending',
                    created_at: new Date().toISOString()
                });

            if (error) throw error;

            setSuccess(true);
            setEmail('');

            setTimeout(() => {
                setSuccess(false);
            }, 2000);
        } catch (err) {
            console.error('Error sending invitation', err);
            setError(err.message || 'Failed to send invitation');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-6 max-w-md w-full bg-white rounded-lg shadow-md">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-semibold text-gray-900">Invite to Project</h3>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-500 text-red-700 px-4 py-3 rounded mb-4">
                    {error}
                </div>
            )}

            {success ? (
                <div className="bg-green-100 border border-green-500 text-green-700 px-4 py-3 rounded mb-4">
                    Invitation sent successfully!
                </div>
            ) : (
                <form onSubmit={invite}>
                    <div className="flex items-center space-x-4 mb-4">
                        <div className="flex-grow">
                            <input
                                type="email"
                                id="inviteEmail"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={loading}
                                className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
                                placeholder="Enter email address"
                                required
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className={`cursor-pointer px-4 py-2 rounded font-medium ${loading
                                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                : 'bg-blue-600 hover:bg-blue-700 text-white'
                            } transition-colors`}
                        >
                            {loading ? 'Sending...' : 'Send Invitation'}
                        </button>
                    </div>
                </form>
            )}
        </div>
    );
}