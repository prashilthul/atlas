"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UploadDialog } from "@/components/upload-dialog";

const NAV_LINKS = [
  { href: "/papers", label: "Papers" },
  { href: "/chat", label: "Chat" },
  { href: "/dashboard", label: "Dashboard" },
];

export function NavBar() {
  const pathname = usePathname();

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-14 bg-white border-b border-border">
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-4">
        <div className="flex items-center gap-8">
          <Link
            href="/"
            className="text-lg font-semibold text-charcoal-900 tracking-tight"
          >
            Paper Pilot
          </Link>
          <nav className="hidden sm:flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm transition-colors ${
                  isActive(link.href)
                    ? "text-charcoal-900 underline underline-offset-4 decoration-charcoal-900"
                    : "text-charcoal-700 hover:text-charcoal-900"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <UploadDialog />
      </div>
    </header>
  );
}
