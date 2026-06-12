import { Outlet } from "react-router-dom";
import { TopNav } from "../../components/navigation/TopNav";
import { AdminTabs } from "../../components/navigation/AdminTabs";

export function AdminLayout() {
  return (
    <div className="app-shell">
      <TopNav />
      <div className="admin-shell">
        <AdminTabs />
        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
