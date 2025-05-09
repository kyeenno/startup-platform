"use client";
import { useState, useEffect } from 'react';
 
export default function DisplayData() {
    const [data, setData] = useState(null);
    // const [err, setErr] = useState({});

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch data from the backend API
                const response = await fetch('http://localhost:8000/');

                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }

                const result = await response.json();
                setData(result);
                console.log(result);

            } catch (e) {
                console.error('Error fetching data:', e);
            }
        };

        fetchData();
    }, []);

    return (
        <div className="text-white">
            <h1 className="mt-8 text-3xl text-green">Formatted message</h1>
            <div>
                { data ? (
                    <p>{data.message}</p>
                ) : 'Loading...' }
            </div>
            <h1 className="mt-8 text-3xl">Raw JSON</h1>
            <div>
                { data ? (
                    <p>{JSON.stringify(data)}</p>
                ) : 'Loading...' }
            </div>
        </div>
    );
}