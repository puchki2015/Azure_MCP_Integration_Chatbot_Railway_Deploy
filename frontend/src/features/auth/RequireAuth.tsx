import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { Spinner } from "../../components/ui/Spinner";
import { useAuth } from "../../app/providers/AuthProvider";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="screen-center">
        <Spinner />
      </div>
    );
  }

  if (status !== "authenticated") {
    return <Navigate to="/" replace />;
  }

  return children;
}
