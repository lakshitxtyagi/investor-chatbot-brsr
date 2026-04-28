"use client";

import { createContext, useContext, useEffect, useState } from "react";

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

type ThemeCtx = { isDark: boolean; toggle: () => void };

const ThemeContext = createContext<ThemeCtx>({ isDark: true, toggle: () => {} });

// ---------------------------------------------------------------------------
// Provider
// Renders a data-theme="dark|light" wrapper div (display:contents so it is
// invisible to layout).  CSS variables are defined on [data-theme] selectors
// in globals.css — no direct DOM manipulation needed, React controls it.
// ---------------------------------------------------------------------------

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [isDark, setIsDark] = useState(true);

  // Sync with localStorage on first client render
  useEffect(() => {
    try {
      const stored = localStorage.getItem("brsr-theme");
      if (stored === "light") setIsDark(false);
    } catch {
      // localStorage unavailable (SSR safety)
    }
  }, []);

  const toggle = () => {
    setIsDark((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("brsr-theme", next ? "dark" : "light");
      } catch { /* ignore */ }
      return next;
    });
  };

  return (
    <ThemeContext.Provider value={{ isDark, toggle }}>
      {/* data-theme drives all CSS variables — React owns this, no classList hacks */}
      <div data-theme={isDark ? "dark" : "light"} style={{ display: "contents" }}>
        {children}
      </div>
    </ThemeContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useTheme() {
  return useContext(ThemeContext);
}

// ---------------------------------------------------------------------------
// ThemeToggle button — drop-in for any page header
// ---------------------------------------------------------------------------

export function ThemeToggle() {
  const { isDark, toggle } = useTheme();
  return (
    <button
      onClick={toggle}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: 34,
        height: 34,
        borderRadius: 8,
        background: "var(--clr-surface-hover)",
        border: "1px solid var(--clr-border-alt)",
        cursor: "pointer",
        color: "var(--clr-text-muted)",
        transition: "background 0.2s",
        flexShrink: 0,
      }}
    >
      {isDark ? (
        // Sun icon → click to go light
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5" />
          <line x1="12" y1="1" x2="12" y2="3" />
          <line x1="12" y1="21" x2="12" y2="23" />
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
          <line x1="1" y1="12" x2="3" y2="12" />
          <line x1="21" y1="12" x2="23" y2="12" />
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
        </svg>
      ) : (
        // Moon icon → click to go dark
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
      )}
    </button>
  );
}
