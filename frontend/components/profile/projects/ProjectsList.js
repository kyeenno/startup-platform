'use client';

import { useEffect, useState } from 'react';
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";

export default function UserData() {
  const { user, loading: authLoading } = useAuth();
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchUserData() {
      if (!user) {
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError(null);
        
        const { data: userData, error } = await supabase
          .from("user_info")
          .select("*")
          .eq('user_id', user.id);
        
        if (error) throw error;
        
        setData(userData);
        
      } catch (err) {
        console.error(`Error fetching data from ${tableName}:`, err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchUserData();
  }, [user]);

  // Default renderer for the data
  const defaultRenderer = (item, index) => {
    return (
      <div key={index}>
        {Object.entries(item).map(([key, value]) => (
          <div key={key}>
            <span>{key}: </span>
            <span>{value?.toString() || 'N/A'}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">{title}</h2>
      {authLoading || isLoading ? (
        <div className="animate-pulse bg-gray-100 p-4 rounded-lg">
          Loading data...
        </div>
      ) : error ? (
        <div className="bg-red-100 border border-red-500 text-red-700 p-4 rounded-lg">
          <p>Error: {error}</p>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="bg-gray-100 p-4 rounded-lg">
          <p className="text-gray-500">No data found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.map((item, index) => (
            renderItem ? renderItem(item, index) : defaultRenderer(item, index)
          ))}
        </div>
      )}
    </div>
  );
}