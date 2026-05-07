"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";
import { Logo } from "@/components/brand/Logo";
import {
  LayoutDashboard,
  Video,
  Target,
  FileText,
  Users,
  GraduationCap,
  Upload,
  X,
} from "lucide-react";
import Link from "next/link";

export type ActiveItem =
  | "dashboard"
  | "match"
  | "shot-tracker"
  | "reports"
  | "players"
  | "academy"
  | "upload"
  | "settings";

export interface SidebarProps {
  activeItem: ActiveItem;
  onMobileOpen?: (open: boolean) => void;
  mobileOpen?: boolean;
}

interface NavItem {
  id: ActiveItem;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  href: string;
  badge?: string;
}

const ANALYSE_ITEMS: NavItem[] = [
  { id: "dashboard", label: "Tableau de bord", icon: LayoutDashboard, href: "/demo/coach" },
  { id: "match",     label: "Analyse de match", icon: Video,            href: "/demo/coach",        badge: "LIVE" },
  { id: "shot-tracker", label: "Shot Tracker",  icon: Target,           href: "/demo/coach#shots" },
  { id: "reports",   label: "Rapports",          icon: FileText,         href: "/demo/coach#reports" },
];

const CLUB_ITEMS: NavItem[] = [
  { id: "players",  label: "Joueurs",      icon: Users,          href: "/demo/coach#players" },
  { id: "academy",  label: "Académie",     icon: GraduationCap,  href: "/demo/academy" },
  { id: "upload",   label: "Upload vidéo", icon: Upload,         href: "/upload" },
];

function NavLink({ item, active }: { item: NavItem; active: boolean }) {
  return (
    <Link
      href={item.href}
      className={[
        "flex items-center gap-3 px-3 py-2 rounded-r-md text-sm transition-all border-l-2",
        active
          ? "bg-court/10 border-court text-bone"
          : "border-transparent text-slate-400 hover:text-bone hover:bg-slate-900",
      ].join(" ")}
    >
      <item.icon
        size={15}
        className={active ? "text-court" : "text-slate-400"}
      />
      <span className="font-geist flex-1">{item.label}</span>
      {item.badge && active && (
        <span className="font-mono text-[10px] text-signal border border-signal/40 px-1.5 py-0.5 rounded leading-none">
          {item.badge}
        </span>
      )}
    </Link>
  );
}

function SidebarContent({ activeItem }: { activeItem: ActiveItem }) {
  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-slate-700">
        <Link href="/">
          <Logo className="h-7 w-auto text-bone" />
        </Link>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-5 space-y-5 overflow-y-auto">
        {/* ANALYSE group */}
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400 px-3 mb-2">
            Analyse
          </p>
          <div className="space-y-0.5">
            {ANALYSE_ITEMS.map((item) => (
              <NavLink key={item.id} item={item} active={activeItem === item.id} />
            ))}
          </div>
        </div>

        {/* CLUB group */}
        <div>
          <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400 px-3 mb-2">
            Club
          </p>
          <div className="space-y-0.5">
            {CLUB_ITEMS.map((item) => (
              <NavLink key={item.id} item={item} active={activeItem === item.id} />
            ))}
          </div>
        </div>
      </nav>

      {/* Bottom user section */}
      <div className="border-t border-slate-700 px-4 py-4">
        <div className="flex items-center gap-3">
          {/* Avatar */}
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
            <span className="font-mono text-xs text-bone">YK</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-geist text-sm text-bone leading-tight truncate">Yao Konaté</p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <p className="font-mono text-[10px] text-slate-400 truncate">ABC Fighters</p>
              <span className="font-mono text-[10px] border border-court text-court px-1 py-0.5 rounded leading-none shrink-0">
                PRO
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function Sidebar({ activeItem, mobileOpen = false, onMobileOpen }: SidebarProps) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-[220px] shrink-0 bg-ink border-r border-slate-700 flex-col h-screen sticky top-0">
        <SidebarContent activeItem={activeItem} />
      </aside>

      {/* Mobile overlay + slide-in */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 bg-black/50 z-40 lg:hidden"
              onClick={() => onMobileOpen?.(false)}
            />

            {/* Slide-in panel */}
            <motion.aside
              key="sidebar"
              initial={{ x: -220 }}
              animate={{ x: 0 }}
              exit={{ x: -220 }}
              transition={{ type: "tween", duration: 0.25 }}
              className="fixed left-0 top-0 bottom-0 w-[220px] bg-ink border-r border-slate-700 z-50 lg:hidden flex flex-col"
            >
              {/* Close button */}
              <button
                onClick={() => onMobileOpen?.(false)}
                className="absolute top-4 right-4 text-slate-400 hover:text-bone transition-colors"
                aria-label="Fermer le menu"
              >
                <X size={18} />
              </button>
              <SidebarContent activeItem={activeItem} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
