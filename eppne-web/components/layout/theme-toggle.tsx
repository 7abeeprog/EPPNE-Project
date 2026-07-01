// components/layout/theme-toggle.tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Palette, Check } from "lucide-react";

const THEMES = [
  { name: "Emerald", id: "emerald" },
  { name: "Cyber Blue", id: "cyber-blue" },
  { name: "Royal Purple", id: "royal-purple" },
  { name: "Amber Gold", id: "amber-gold" },
  { name: "Rose Fire", id: "rose-fire" },
  { name: "Ocean Teal", id: "ocean-teal" },
  { name: "Matrix Green", id: "matrix-green" },
];

export function ThemeToggle() {
  const [activeTheme, setActiveTheme] = useState("emerald");

  // التأكد من تطبيق السمة المحفوظة عند التحميل
  useEffect(() => {
    const savedTheme = localStorage.getItem("eppne-theme") || "emerald";
    setActiveTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);
  }, []);

  const changeTheme = (id: string) => {
    setActiveTheme(id);
    document.documentElement.setAttribute("data-theme", id);
    localStorage.setItem("eppne-theme", id);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        {/* تصميم زجاجي يطابق هوية الـ Navbar السيادية */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-10 w-10 rounded-full border border-white/10 bg-background/50 backdrop-blur-md shadow-inner hover:bg-primary/20 transition-all"
        >
          <Palette className="h-5 w-5 text-primary" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48 rounded-2xl bg-card/80 backdrop-blur-3xl border-white/10 p-2 shadow-[0_15px_40px_rgba(0,0,0,0.2)]">
        {THEMES.map((theme) => (
          <DropdownMenuItem 
            key={theme.id} 
            onClick={() => changeTheme(theme.id)}
            className="flex items-center justify-between font-bold cursor-pointer rounded-xl hover:bg-primary/10 transition-colors"
          >
            {theme.name}
            {activeTheme === theme.id && <Check className="h-4 w-4 text-primary" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}