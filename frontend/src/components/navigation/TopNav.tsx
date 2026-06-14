import { NavLink } from "react-router-dom";
import { Button } from "../ui/Button";
import { useAuth } from "../../app/providers/AuthProvider";

export function TopNav() {
  const { user, logout } = useAuth();
  const navLinkClass = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : undefined);

  return (
    <header className="topnav">
      <div className="topnav__brand">
        <NavLink to="/chat" className={navLinkClass}>
          Azure AI Ops
        </NavLink>
      </div>
      <div className="topnav__actions">
        <nav className="topnav__links">
          <NavLink to="/chat" className={navLinkClass}>
            Chat
          </NavLink>
          <NavLink to="/costs" target="_blank" rel="noreferrer">
            Cost of your resources
          </NavLink>
          <NavLink to="/approvals" className={navLinkClass}>
            Approvals
          </NavLink>
          <NavLink to="/approvals/failed" className={navLinkClass}>
            Failed
          </NavLink>
          {user?.isAdmin ? (
            <NavLink to="/admin" className={navLinkClass}>
              Admin
            </NavLink>
          ) : null}
        </nav>
        <div className="topnav__user">{user?.displayName ?? "Guest"}</div>
        <Button variant="secondary" onClick={() => void logout()}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
