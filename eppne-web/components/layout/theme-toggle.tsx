// components/layout/theme-toggle.tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Sun, Moon } from "lucide-react";

const STORAGE_KEY = "eppne-color-mode";
type ColorMode = "light" | "dark";

export function ThemeToggle() {
  const [mode, setMode] = useState<ColorMode>("light");

  // التأكد من تطبيق السمة المحفوظة عند التحميل + تنضيف أثر النظام القديم (data-theme)
  useEffect(() => {
    document.documentElement.removeAttribute("data-theme");
    localStorage.removeItem("eppne-theme");

    const saved = localStorage.getItem(STORAGE_KEY) as ColorMode | null;
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial: ColorMode = saved ?? (prefersDark ? "dark" : "light");
    setMode(initial);
    document.documentElement.classList.toggle("dark", initial === "dark");
  }, []);

  const toggleMode = () => {
    const next: ColorMode = mode === "dark" ? "light" : "dark";
    setMode(next);
    document.documentElement.classList.toggle("dark", next === "dark");
    localStorage.setItem(STORAGE_KEY, next);
  };

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggleMode}
      aria-label={mode === "dark" ? "التبديل للوضع الفاتح" : "التبديل للوضع الغامق"}
    >
      {mode === "dark" ? <Sun className="h-5 w-5 text-primary" /> : <Moon className="h-5 w-5 text-primary" />}
    </Button>
  );
}
