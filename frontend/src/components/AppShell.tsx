"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { ComplianceBanner } from "./ComplianceBanner";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/search", label: "Search" },
  { href: "/records", label: "Records" },
  { href: "/documents", label: "Documents" },
  { href: "/matches", label: "Potential Matches" },
  { href: "/projects", label: "Research Projects" },
  { href: "/saved-searches", label: "Saved Searches" },
  { href: "/import", label: "Import Data" },
  { href: "/jobs", label: "Processing Jobs" },
  { href: "/audit", label: "Audit History" },
  { href: "/chat", label: "AI Chat" },
  { href: "/guide", label: "User Guide" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) return <div className="p-8 text-gray-500">Loading…</div>;
  if (!user) return null;

  return (
    <div className="min-h-screen">
      <ComplianceBanner />
      <div className="flex">
        <aside className="w-60 shrink-0 border-r border-gray-200 bg-white min-h-[calc(100vh-33px)]">
          <div className="p-4 border-b border-gray-200">
            <div className="font-semibold text-brand-700">Records Research</div>
            <div className="text-xs text-gray-500 truncate">
              {user.workspaces[0]?.name}
            </div>
          </div>
          <nav className="p-2 space-y-0.5">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-md px-3 py-2 text-sm ${
                    active
                      ? "bg-brand-50 text-brand-700 font-medium"
                      : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <div className="flex-1 min-w-0">
          <header className="h-14 border-b border-gray-200 bg-white flex items-center justify-between px-6">
            <div className="text-sm text-gray-500">{user.user.email} · {user.user.role}</div>
            <button className="btn-secondary" onClick={logout}>
              Log out
            </button>
          </header>
          <main className="p-6 max-w-7xl">{children}</main>
        </div>
      </div>
    </div>
  );
}
