"use client";
import { useState } from "react";
import { Menu } from "lucide-react";
import { Sidebar, type ActiveItem } from "./Sidebar";

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeItem: ActiveItem;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function DashboardLayout({
  children,
  activeItem,
  title,
  subtitle,
  actions,
}: DashboardLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-screen bg-ink overflow-hidden">
      <Sidebar
        activeItem={activeItem}
        mobileOpen={mobileOpen}
        onMobileOpen={setMobileOpen}
      />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <div className="border-b border-slate-700 px-6 py-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden text-slate-400 hover:text-bone transition-colors"
              aria-label="Ouvrir le menu"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 className="font-fraunces text-xl text-bone">{title}</h1>
              {subtitle && (
                <p className="font-mono text-xs text-slate-400">{subtitle}</p>
              )}
            </div>
          </div>
          {actions && (
            <div className="flex items-center gap-3">{actions}</div>
          )}
        </div>

        {/* Scrollable content */}
        <main className="flex-1 overflow-y-auto px-6 py-8">{children}</main>
      </div>
    </div>
  );
}
