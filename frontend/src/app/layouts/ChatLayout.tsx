import { Outlet } from "react-router-dom";
import { TopNav } from "../../components/navigation/TopNav";

export function ChatLayout() {
  return (
    <div className="app-shell">
      <TopNav />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
