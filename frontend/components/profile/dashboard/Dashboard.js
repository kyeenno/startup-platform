"use client";

import AcceptPopup from '../projects/messages/AcceptPopup';
import NewProject from '../projects/NewProject';
 
export default function Dashboard() {
    return (
        <div className="container mx-auto py-10 max-w-5xl text-white">
            <AcceptPopup />
            <NewProject />
        </div>
    );
}