import { Navigate } from "react-router-dom";
import { Spinner } from "../../components/ui/Spinner";
import { useAuth } from "../../app/providers/AuthProvider";

export function AuthCallbackPage() {
  const { status } = useAuth();

  if (status === "authenticated") {
    return <Navigate to="/chat" replace />;
  }

  if (status === "unauthenticated") {
    return <Navigate to="/" replace />;
  }

  return (
    <div className="screen-center">
      <Spinner />
    </div>
  );
}
