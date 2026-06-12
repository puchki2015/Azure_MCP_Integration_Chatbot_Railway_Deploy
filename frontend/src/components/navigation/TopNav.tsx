import { Link } from "react-router-dom";
import { Button } from "../ui/Button";
import { useAuth } from "../../app/providers/AuthProvider";

export function TopNav() {
  const { user, logout } = useAuth();

  return (
    <header className="topnav">
      <div className="topnav__brand">
        <Link to="/chat">Azure AI Ops</Link>
      </div>
      <div className="topnav__actions">
        <nav className="topnav__links">
          {user?.isAdmin ? <Link to="/admin">Admin</Link> : null}
          <Link to="/approvals">Approvals</Link>
          <Link to="/approvals/failed">Failed</Link>
          <Link to="/chat">Chat</Link>
        </nav>
        <div className="topnav__user">{user?.displayName ?? "Guest"}</div>
        <Button variant="secondary" onClick={() => void logout()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
