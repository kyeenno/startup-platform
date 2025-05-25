'use client';

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";

export default function AcceptPopup() {
    const { user } = useAuth();
    const [invitations, setInvitations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentId, setCurrentId] = useState(null);


    useEffect(() => {
        async function fetchInvitations() {
            if (!user) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);

                const { data: { user: authUser } } = await supabase.auth.getUser();

                const { data, error } = await supabase
                    .from('project_invitations')
                    .select(`
                            id,
                            project_id,
                            email,
                            status,
                            projects:projects(project_name)
                        `)
                    .eq('email', authUser.email.toLowerCase())
                    .eq('status', 'pending');

                if (error) throw error;

                setInvitations(data || []);

            } catch (error) {
                console.error('error fetching invitations:', error);
                setError('Failed to load invitations');
            } finally {
                setLoading(false);
            }
        }

        fetchInvitations();
    }, [user]);

    const accept = async (invitationId, projectId) => {
        setCurrentId(invitationId);

        try {
            // Assign the project to user
            const { error: insertError } = await supabase
                .from('project_to_user')
                .insert({
                    user_id: user.id,
                    project_id: projectId
                });

            if (insertError) throw insertError;

            // Update invitation status
            const { error: updateError } = await supabase
                .from('project_invitations')
                .update({ status: 'accepted' })
                .eq('id', invitationId);

            if (updateError) throw updateError;

            // Remove updated (accepted) invitations
            setInvitations(invitations.filter(val => val.id !== invitationId));
        } catch (error) {
            console.error('Error accepting invitation:', error);
            setError('Failed to accept invitation');
        } finally {
            setCurrentId(null);
        }
    };

    const decline = async (invitationId) => {
        setCurrentId(invitationId);

        try {
            const { error } = await supabase
                .from('project_invitations')
                .update({ status: 'declined' })
                .eq('id', invitationId);

            if (error) throw error;

            // Remove updated (declined) invitations
            setInvitations(invitations.filter(val => val.id !== invitationId));
        } catch (error) {
            console.error('Error declining invitation:', error);
            setError('Failed to decline invitation');
        } finally {
            setCurrentId(null);
        }
    };

    if (loading) {
        return <div className="animate-pulse h-16 bg-gray-200 rounded my-4"></div>;
    }

    if (invitations.length === 0) {
        return (
            <div className="text-[#111827] py-2">
                <p className="p-4 bg-[#FAFAFA] border border-gray-300 rounded-lg flex flex-col sm:flex-row sm:items-center sm:justify-between">No Invitations!</p>
            </div>
        );
    }

    return (
        <div className="text-[#111827] px-4 py-2 m-4">
            <h2 className="text-xl font-semibold text-[#111827] mb-4">Pending Invitations</h2>

            <div className="space-y-3">
                {invitations.map((invitation) => (
                    <div
                        key={invitation.id}
                        className="p-4 bg-[#FAFAFA] border border-gray-300 rounded-lg flex flex-col sm:flex-row sm:items-center sm:justify-between"
                    >
                        <div className="mb-3 sm:mb-0">
                            <p className="text-[#111827] font-medium">
                                Invitation to join: <span className="text-[#2563EB]">{invitation.projects.project_name}</span>
                            </p>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => decline(invitation.id)}
                                disabled={currentId === invitation.id}
                                className="px-4 py-2 bg-transparent border border-gray-300 text-[#111827] hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
                            >
                                Decline
                            </button>

                            <button
                                onClick={() => accept(invitation.id, invitation.project_id)}
                                disabled={currentId === invitation.id}
                                className="px-4 py-2 bg-[#2563EB] hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50"
                            >
                                {currentId === invitation.id ? 'Processing...' : 'Accept'}
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}