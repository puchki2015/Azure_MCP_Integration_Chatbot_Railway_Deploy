import { NavLink } from "react-router-dom";

export function AdminTabs() {
  return (
    <div className="admin-tabs">
      <NavLink to="/admin/pending" className={({ isActive }) => (isActive ? "active" : "")}>Pending</NavLink>
      <NavLink to="/admin/approved" className={({ isActive }) => (isActive ? "active" : "")}>Approved</NavLink>
      <NavLink to="/admin/failed" className={({ isActive }) => (isActive ? "active" : "")}>Failed</NavLink>
      <NavLink to="/admin/rejected" className={({ isActive }) => (isActive ? "active" : "")}>Rejected</NavLink>
    </div>
  );
}
