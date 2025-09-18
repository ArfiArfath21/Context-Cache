import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import StatusPage from "./pages/Status";
import SearchPage from "./pages/Search";
import SettingsPage from "./pages/Settings";

const NAV_ITEMS = [
  { path: "/status", label: "Status" },
  { path: "/search", label: "Search" },
  { path: "/settings", label: "Settings" }
];

function ThemeToggle() {
  const [theme, setTheme] = useState(() =>
    document.documentElement.getAttribute("data-theme") || "light"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ctxc-theme", theme);
  }, [theme]);

  useEffect(() => {
    const stored = localStorage.getItem("ctxc-theme");
    if (stored) {
      setTheme(stored);
    }
  }, []);

  return (
    <button className="theme-toggle" onClick={() => setTheme(theme === "light" ? "dark" : "light")}>
      {theme === "light" ? "🌙" : "☀️"}
    </button>
  );
}

function Navigation() {
  const location = useLocation();
  return (
    <nav className="nav">
      {NAV_ITEMS.map((item) => (
        <Link key={item.path} className={location.pathname === item.path ? "active" : ""} to={item.path}>
          {item.label}
        </Link>
      ))}
      <div className="right-actions">
        <ThemeToggle />
      </div>
    </nav>
  );
}

export default function App() {
  const defaultRoute = useMemo(() => {
    return NAV_ITEMS[0].path;
  }, []);

  return (
    <div className="app-shell">
      <Navigation />
      <main>
        <Routes>
          <Route path="/status" element={<StatusPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/" element={<Navigate to={defaultRoute} replace />} />
        </Routes>
      </main>
    </div>
  );
}
