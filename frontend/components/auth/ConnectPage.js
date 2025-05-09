import ConnectSources from "../profile/connect/ConnectSources";
import ProtectedRoute from "./ProtectedRoute";

export default function ConnectPage() {
    return (
        <ProtectedRoute>
            <div className="py-10">
                <ConnectSources />
            </div>
        </ProtectedRoute>
    );
}