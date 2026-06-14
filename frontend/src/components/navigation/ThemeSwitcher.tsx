import { useEffect, useState } from "react";

type ThemeName = "dark" | "white";

const themeLabels: Record<ThemeName, string> = {
  dark: "Dark",
  white: "Light"
};

export function ThemeSwitcher() {
  const [theme, setTheme] = useState<ThemeName>("dark");

  useEffect(() => {
    const savedTheme = window.localStorage.getItem("azureops-theme") as ThemeName | null;
    if (savedTheme === "white" || savedTheme === "dark") {
      setTheme(savedTheme);
      document.body.setAttribute("data-theme", savedTheme);
    }
  }, []);

  useEffect(() => {
    document.body.setAttribute("data-theme", theme);
    window.localStorage.setItem("azureops-theme", theme);
  }, [theme]);

  return (
    <div className="app-theme-switcher" aria-label="Theme switcher">
      <button
        type="button"
        className={`app-theme-switcher__btn${theme === "dark" ? " active" : ""}`}
        onClick={() => setTheme("dark")}
        aria-label={themeLabels.dark}
        title={themeLabels.dark}
      >
        <span className="app-theme-switcher__dot app-theme-switcher__dot--dark" />
        <span className="app-theme-switcher__label">{themeLabels.dark}</span>
      </button>
      <button
        type="button"
        className={`app-theme-switcher__btn${theme === "white" ? " active" : ""}`}
        onClick={() => setTheme("white")}
        aria-label={themeLabels.white}
        title={themeLabels.white}
      >
        <span className="app-theme-switcher__dot app-theme-switcher__dot--white" />
        <span className="app-theme-switcher__label">{themeLabels.white}</span>
      </button>
    </div>
  );
}
