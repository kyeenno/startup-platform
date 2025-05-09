'use client';

import { useEffect, useState } from 'react';
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabaseClient";

export default function UserData({ 
  tableName = 'user_info',  // Default table to query
  columns = '*',           // Default columns to select
  title = 'User Data',     // Component title
  renderItem              // Optional custom render function
}) {
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
        
        console.log(`Fetching ${tableName} data for user:`, user.id);
        
        const { data: userData, error } = await supabase
          .from(tableName)
          .select(columns)
          .eq('user_id', user.id);
        
        if (error) throw error;
        
        console.log(`Retrieved ${userData?.length || 0} rows from ${tableName}`);
        setData(userData);
        
      } catch (err) {
        console.error(`Error fetching data from ${tableName}:`, err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    fetchUserData();
  }, [user, tableName, columns]);

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
    <div className="text-white">
      <h2 className="text-2xl font-bold mb-4">{title}</h2>
      
      {authLoading || isLoading ? (
        <div className="animate-pulse bg-gray-800 p-4 rounded-lg">
          Loading data...
        </div>
      ) : error ? (
        <div className="bg-red-900/30 border border-red-500 p-4 rounded-lg">
          <p className="text-red-300">Error: {error}</p>
        </div>
      ) : !data || data.length === 0 ? (
        <div className="bg-gray-800 p-4 rounded-lg">
          <p className="text-gray-300">No data found.</p>
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