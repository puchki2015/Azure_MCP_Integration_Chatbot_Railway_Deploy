import { Outlet } from "react-router-dom";
import { TopNav } from "../../components/navigation/TopNav";
import { ThemeSwitcher } from "../../components/navigation/ThemeSwitcher";

export function ChatLayout() {
  return (
    <div className="app-shell">
      <TopNav />
      <main className="app-main">
        <Outlet />
      </main>
      <ThemeSwitcher />
    </div>
  );
}
