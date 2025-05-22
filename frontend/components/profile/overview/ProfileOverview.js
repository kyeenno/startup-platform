'use client';

import { useState, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function ProfileOverview() {
    const { user } = useAuth();
    const [profile, setProfile] = useState(null);
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const router = useRouter();

    useEffect(() => {
        async function fetchUserData() {
            if (!user) {
                setLoading(false);
                return;
            }

            try {
                setLoading(true);

                // Fetch user email data
                const { data: authUser, error: authError } = await supabase.auth.getUser();

                if (authError) throw authError;

                // Fetch user name & surname data
                const { data: userInfo, error: userInfoError } = await supabase
                    .from('user_info')
                    .select('user_name, user_surname')
                    .eq('user_id', user.id)
                    .single();

                if (userInfoError) throw userInfoError;

                // Update profile data
                setProfile({
                    email: authUser.user.email,
                    name: userInfo.user_name || 'Name',
                    surname: userInfo.user_surname || 'Surname'
                });

                // Fetch user's projects
                const { data: projectData, error: projectError } = await supabase
                    .from('project_to_user')
                    .select(`
                        project_id,
                        projects:projects(
                            project_id,
                            project_name,
                            created_at
                        )
                    `)
                    .eq('user_id', user.id)
                    .order('projects(created_at)', { ascending: false });

                if (projectError) throw projectError;

                // Transform projects data
                const formattedProjects = projectData
                    .map(item => item.projects)
                    .filter(Boolean);

                setProjects(formattedProjects);
            } catch (err) {
                console.error('Error fetching profile data:', err);
                setError('Failed to load profile data');
            } finally {
                setLoading(false);
            }
        }

        fetchUserData();
    }, [user]);

    if (loading) {
        return (
            <div className="container mx-auto py-10 max-w-5xl">
                <div className="animate-pulse">
                    <div className="h-32 bg-gray-700 rounded-lg mb-6"></div>
                    <div className="h-8 bg-gray-700 rounded w-1/3 mb-4"></div>
                    <div className="h-4 bg-gray-700 rounded mb-2"></div>
                    <div className="h-4 bg-gray-700 rounded w-2/3 mb-6"></div>
                    <div className="h-64 bg-gray-700 rounded-lg"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="container mx-auto py-10 max-w-5xl"></div>
        );
    }

    return (
        <div className="container mx-auto py-10 max-w-5xl text-gray-900">
            {/* Profile Header */}
            <div className="bg-white p-6 rounded-lg shadow-md mb-6">
                <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
                    <div>
                        <h1 className="text-2xl font-bold text-gray-900">
                            {profile?.name && profile?.surname
                            ? `${profile.name} ${profile.surname}`
                            : user?.email?.split('@')[0] || 'User'}
                        </h1>
                        <p className="text-gray-500">{profile?.email}</p>
                    </div>
                </div>
            </div>

            {/* Projects Section */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">Your Projects</h2>
                    <Link
                        href="/profile/projects/new"
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors"
                    >
                        Create Project
                    </Link>
                </div>

                {projects.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {projects.map((project) => (
                            <Link
                                key={project.project_id}
                                href={`/profile/projects/${project.project_id}`}
                                className="block bg-white hover:bg-gray-100 p-5 rounded-lg transition-colors shadow-md"
                            >
                                <p className="font-bold text-md mb-2 text-gray-900">{project.project_name}</p>
                                <div className="text-xs text-gray-500">
                                    Created: {new Date(project.created_at).toLocaleDateString()}
                                </div>
                            </Link>
                        ))}
                    </div>
                ) : (
                    <div className="bg-gray-100 border border-gray-300 p-8 rounded-lg text-center">
                        <p className="text-gray-500 mb-4">{`You haven't created any projects yet.`}</p>
                        <Link
                            href="/profile/projects/new"
                            className="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm transition-colors"
                        >
                            Create Your First Project
                        </Link>
                    </div>
                )}
            </div>
        </div>
    );
}