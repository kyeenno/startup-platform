import Navbar from "@/components/ui/Navbar";
import ProtectedRoute from "@/components/auth/ProtectedRoute";

export default function ProfileLayout({ children }) {
    return (
        <ProtectedRoute>
            <Navbar />
            <div>
                {children}
            </div>
        </ProtectedRoute>
    );
}