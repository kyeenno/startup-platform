'use client';
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useRef, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Navbar() {
    const { user, loading } = useAuth();
    const [listOpen, setListOpen] = useState(false);
    const [projects, setProjects] = useState([]);
    const [projectsLoading, setProjectsLoading] = useState(true);
    const listRef = useRef(null);
    const router = useRouter();

    // Fetch projects data from Supabase
    useEffect(() => {
        async function fetchProjects() {
            if (user && user.id) {
                try {
                    setProjectsLoading(true);
                    console.log("user:", user.id);

                    const { data, error } = await supabase
                        .from('project_to_user')
                        .select(`
                            id,
                            project_id,
                            projects:projects(project_id, project_name)    
                        `)
                        // .select('*')
                        .eq('user_id', user.id);

                    if (error) throw error;

                    console.log("Joined projects data:", data);

                    // Structure the data
                    const structureProjects = data.map(item => {
                        if (!item.projects) {
                            console.log("Missing data:", item);
                            return null;
                        }

                        return {
                            // JSX component key
                            project_id: item.project_id,
                            // JSX component displayed project's name
                            project_name: item.projects.project_name
                        };
                    }).filter(Boolean);

                    setProjects(structureProjects || []);

                } catch (err) {
                    console.error('Error fetching prjcts:', err);
                } finally {
                    setProjectsLoading(false);
                    console.log("fetched");
                }
            } else {
                setProjects([]);
                setProjectsLoading(false);
            }
        }

        fetchProjects();
    }, [user]);

    // TODO: impelement dropdown closing & opening functionality
    // ...

    const projectSelect = (projectId) => {
        router.push(`/profile/projects/${projectId}`);
        setListOpen(false);
    };

    // Function for handling log out
    const handleLogout = async () => {
        try {
            await supabase.auth.signOut();
        } catch (err) {
            console.error("Error logging out with supabase auth", err);
        }
    };

    return (
        <div className="text-white px-4 py-2 mx-4 mt-4">
            <ul className="flex justify-between items-center px-6 py-3 gap-6">
                {loading ? (
                    <li>Loading...</li>
                ) : user ? (
                    <>
                    {/* Links for logged in users */}
                        <li className="mr-auto hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer">
                            <Link href="/profile/dashboard">Home</Link>
                        </li>
                        <li className="ml-auto cursor-pointer relative" ref={listRef}>
                            <button
                                onClick={() => setListOpen(!listOpen)}
                                className="flex items-center gap-1 hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer"
                                aria-haspopup="true"
                                aria-expanded={listOpen}
                            >
                                Projects
                                <svg
                                    className={`w-4 h-4 transition-transform ${listOpen ? 'rotate-180' : ''}`}
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            {listOpen && (
                                <div className="absolute left-0 mt-2 w-56 rounded-md bg-black shadow-lg border border-white z-10">
                                    <div className="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
                                        {projects.length > 0 ? (
                                            <>
                                                {/* Project list */}
                                                {projects.map(project => (
                                                    <a
                                                        key={project.project_id}
                                                        onClick={() => projectSelect(project.project_id)}
                                                        className="block px-4 py-2 text-sm hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer"
                                                        role="menuitem"
                                                    >
                                                        {project.project_name}
                                                    </a>
                                                ))}
                                                <div className="border-t border-white/10 my-1"></div>
                                            </>
                                        ) : (
                                            <p className="px-4 py-2 text-sm text-gray-300">No projects yet</p>
                                        )}
                                        {/* Create new project option */}
                                        <Link
                                            href="/profile/projects/new"
                                            className="block hover:text-gray-300 transition duration-150 ease-in-out px-4 py-2 text-sm"
                                            onClick={() => setListOpen(false)}
                                        >
                                            + Create New Project
                                        </Link>
                                    </div>
                                </div>
                            )}
                        </li>
                        <li className="hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer">
                            <Link href="/profile/plan">My Plan</Link>
                        </li>
                        <li>
                            <button className="border border-white bg-white h-3/4 px-4 py-1 rounded-lg hover:bg-black hover:text-white transition duration-150 ease-in-out cursor-pointer text-black" onClick={handleLogout}>Log out</button>
                        </li>
                    </>
                ) : (
                    <>
                        {/* Links for logged out users */}
                        <li className="hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer">
                            <Link href="/auth/signin">Sign in</Link>
                        </li>
                        <li className="hover:text-gray-300 transition duration-150 ease-in-out cursor-pointer">
                            <Link href="/auth/signup">Create an account</Link>
                        </li>
                    </>
                )}
            </ul>
        </div>
    );
}