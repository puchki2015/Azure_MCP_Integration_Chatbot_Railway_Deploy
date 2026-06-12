import { Outlet } from "react-router-dom";

export function PublicLayout() {
  return (
    <div className="public-shell">
      <Outlet />
    </div>
  );
}
