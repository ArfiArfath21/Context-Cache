import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";

import StatusPage from "./pages/Status";
import SearchPage from "./pages/Search";
import SettingsPage from "./pages/Settings";
import { useBackendHost } from "./hooks/useApi";
import logoAsset from "./assets/logo.png";

const NAV_ITEMS = [
  { path: "/status", label: "Status", description: "Monitor pipelines and data sources" },
  { path: "/search", label: "Search", description: "Ask questions across your indexed knowledge" },
  { path: "/settings", label: "Settings", description: "Manage ingestion sources and connection settings" }
];

function ThemeToggle() {
  const [theme, setTheme] = useState(() => document.documentElement.getAttribute("data-theme") || "light");

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

  const next = theme === "light" ? "dark" : "light";

  return (
    <button
      className={`theme-toggle ${theme}`}
      type="button"
      aria-label={`Switch to ${next} theme`}
      onClick={() => setTheme(next)}
    >
      <span>{theme === "light" ? "Light" : "Dark"}</span>
    </button>
  );
}

function Sidebar() {
  const location = useLocation();
  return (
    <aside className="sidebar">
      <div className="brand">
        <img src={logoAsset} alt="Context Cache" className="brand-logo" />
        <div>
          <p className="brand-title">Context Cache</p>
          <p className="brand-subtitle">Local knowledge workspace</p>
        </div>
      </div>
      <nav className="nav-links">
        {NAV_ITEMS.map((item) => {
          const active = location.pathname === item.path;
          return (
            <Link key={item.path} to={item.path} className={active ? "active" : ""}>
              <span className="nav-label">{item.label}</span>
              <span className="nav-caption">{item.description}</span>
            </Link>
          );
        })}
      </nav>
      <footer className="sidebar-footer">
        <p className="sidebar-note">All processing stays on this machine.</p>
      </footer>
    </aside>
  );
}

function Header() {
  const host = useBackendHost();
  const location = useLocation();
  const active = NAV_ITEMS.find((item) => item.path === location.pathname) ?? NAV_ITEMS[0];

  return (
    <header className="app-header">
      <div>
        <h1>{active.label}</h1>
        <p>{active.description}</p>
      </div>
      <div className="header-actions">
        <div className="host-chip">
          <span>Backend</span>
          <strong>{host}</strong>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}

export default function App() {
  const defaultRoute = useMemo(() => NAV_ITEMS[0].path, []);

  return (
    <div className="layout">
      <Sidebar />
      <div className="content-area">
        <Header />
        <main className="content-scroll">
          <Routes>
            <Route path="/status" element={<StatusPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/" element={<Navigate to={defaultRoute} replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
