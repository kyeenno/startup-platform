"use client";

import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import InvitePopup from "./messages/InvitePopup";
import ConnectSources from "@/components/profile/connect/ConnectSources";

export default function ProjectOverview() {
  const { projectId } = useParams();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchProjects() {
      if (!user || !projectId) {
        setLoading(false);
        return;
      }

      try {
        const { data, error } = await supabase
          .from("projects")
          .select("*")
          .eq("project_id", projectId)
          .single();

        if (error) throw error;

        setProject(data);
      } catch (err) {
        console.error("Error fetching data:", err);
        setError("Failed to load project data!");
      } finally {
        setLoading(false);
        console.log("Projects fetched successfully (ProjectOverview.js)");
      }
    }

    fetchProjects();
  }, [projectId, user]);

  if (loading) {
    return (
      <div className="container mx-auto py-10 max-w-5xl text-white text-center">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-700 rounded w-1/4 mx-auto mb-4"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2 mx-auto mb-2"></div>
          <div className="h-4 bg-gray-700 rounded w-1/3 mx-auto"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-10 max-w-5xl text-white">
        <div className="bg-red-900/50 border border-red-500 text-red-300 p-4 rounded-lg">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="container mx-auto py-10 max-w-5xl text-white">
        <div className="bg-yellow-900/50 border border-yellow-500 text-yellow-300 p-4 rounded-lg">
          <p>{`Project not found or you don't have access to this project.`}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container flex flex-col items-center mx-auto py-10 max-w-5xl text-gray-900">
      <div className="text-[#111827] px-4 py-2 m-4">
        <h1 className="text-3xl text-center font-bold mb-6 text-[#111827]">
          {project.project_name}
        </h1>
        <div>
          <InvitePopup projectId={projectId} userId={user?.id} />
          <ConnectSources />
        </div>
      </div>
    </div>
  );
}
