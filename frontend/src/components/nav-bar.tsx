"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UploadDialog } from "@/components/upload-dialog";

import { Sparkles, BookOpen, MessageSquare, BarChart3, Layers } from "lucide-react";

const NAV_LINKS = [
  { href: "/papers", label: "Papers", icon: BookOpen },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/traces", label: "Trace Inspector", icon: Layers },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 },
];

export function NavBar() {
  const pathname = usePathname();

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-white/95 backdrop-blur border-b border-slate-200 shadow-xs">
      <div className="mx-auto flex h-full max-w-7xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="flex items-center gap-2 text-base font-bold text-slate-900 tracking-tight group"
          >
            <div className="size-7 rounded-lg bg-slate-900 text-white flex items-center justify-center shadow-xs group-hover:bg-slate-800 transition-colors">
              <Sparkles className="size-4" />
            </div>
            <span>Paper Pilot</span>
          </Link>

          <nav className="hidden sm:flex items-center gap-1.5">
            {NAV_LINKS.map((link) => {
              const Icon = link.icon;
              const active = isActive(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    active
                      ? "bg-slate-900 text-white font-semibold shadow-xs"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"
                  }`}
                >
                  <Icon className={`size-3.5 ${active ? "text-white" : "text-slate-400"}`} />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        <UploadDialog />
      </div>
    </header>
  );
}
