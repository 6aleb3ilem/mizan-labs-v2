import { Menu, PanelLeftClose, PanelLeftOpen, ScanLine, WifiOff } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./Button";

export type NavItem = { key: string; label: ReactNode; icon?: ReactNode; href: string; active?: boolean; badge?: ReactNode };
export type NavSection = { key: string; label?: ReactNode; items: NavItem[] };

export type AppShellProps = {
  brand: ReactNode;
  sections: NavSection[];
  /** Renders a navigation link (the router's Link). */
  renderLink: (item: NavItem, className: string, children: ReactNode) => ReactNode;
  topbar?: ReactNode;
  children: ReactNode;
  offline?: boolean;
  offlineMessage?: ReactNode;
  queued?: ReactNode;
  onScan?: () => void;
  scanLabel?: string;
  bottomNav?: NavItem[];
  sidebarLabel?: string;
  collapsedStorageKey?: string;
};

function readCollapsed(key: string): boolean {
  try {
    return globalThis.localStorage?.getItem(key) === "1";
  } catch {
    return false;
  }
}

/** Sidebar + top bar shell with tablet collapse and phone bottom navigation (SPEC §21.6, §22.1). */
export function AppShell({ brand, sections, renderLink, topbar, children, offline, offlineMessage, queued, onScan, scanLabel = "Scan", bottomNav, sidebarLabel = "Navigation", collapsedStorageKey = "mizan.sidebar" }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(() => readCollapsed(collapsedStorageKey));
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    try {
      globalThis.localStorage?.setItem(collapsedStorageKey, collapsed ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, [collapsed, collapsedStorageKey]);

  const linkClass = (active: boolean | undefined) =>
    cn("flex items-center gap-3 rounded-control px-2.5 py-2 text-base text-text hover:bg-subtle", active && "bg-primary-subtle font-medium text-primary", collapsed && "justify-center px-0");

  const nav = (
    <nav aria-label={sidebarLabel} className="flex flex-1 flex-col gap-4 overflow-y-auto px-2 py-3">
      {sections.map((section) => (
        <div key={section.key} className="flex flex-col gap-0.5">
          {section.label && !collapsed && <p className="px-2.5 pb-1 text-xs font-semibold uppercase tracking-wide text-muted">{section.label}</p>}
          {section.items.map((item) =>
            renderLink(
              item,
              linkClass(item.active),
              <>
                {item.icon && <span className="shrink-0 text-muted [a[aria-current]_&]:text-primary">{item.icon}</span>}
                {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                {!collapsed && item.badge !== undefined && <span className="rounded-full bg-subtle px-1.5 text-xs">{item.badge}</span>}
              </>,
            ),
          )}
        </div>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-dvh bg-canvas text-text">
      <aside className={cn("no-print sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-line bg-surface md:flex", collapsed ? "w-14" : "w-60")}>
        <div className={cn("flex h-14 items-center border-b border-line px-3", collapsed && "justify-center px-0")}>{collapsed ? <span className="text-md font-semibold">M</span> : brand}</div>
        {nav}
        <div className="border-t border-line p-2">
          <Button variant="ghost" size="icon-sm" onClick={() => setCollapsed((v) => !v)} aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed}>
            {collapsed ? <PanelLeftOpen className="size-4" aria-hidden /> : <PanelLeftClose className="size-4" aria-hidden />}
          </Button>
        </div>
      </aside>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden" role="dialog" aria-modal="true" aria-label={sidebarLabel}>
          <div className="absolute inset-0 bg-black/40" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-surface shadow-3" onClick={() => setMobileOpen(false)}>
            <div className="flex h-14 items-center border-b border-line px-3">{brand}</div>
            {nav}
          </aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-line bg-surface/95 px-3 backdrop-blur md:px-4">
          <Button variant="ghost" size="icon-sm" className="md:hidden" onClick={() => setMobileOpen(true)} aria-label={sidebarLabel}>
            <Menu className="size-5" aria-hidden />
          </Button>
          <div className="flex min-w-0 flex-1 items-center gap-2">{topbar}</div>
          {onScan && (
            <Button variant="outline" size="icon" className="touch-target" onClick={onScan} aria-label={scanLabel}>
              <ScanLine className="size-5" aria-hidden />
            </Button>
          )}
        </header>
        {offline && (
          <div role="status" className="flex items-center gap-2 bg-warning px-4 py-1.5 text-sm text-white">
            <WifiOff className="size-4" aria-hidden />
            <span className="flex-1">{offlineMessage ?? "Offline"}</span>
            {queued}
          </div>
        )}
        <main className={cn("flex-1 px-4 py-4 md:px-6", bottomNav && "pb-20 md:pb-4")}>{children}</main>
        {bottomNav && bottomNav.length > 0 && (
          <nav aria-label={sidebarLabel} className="no-print fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-surface md:hidden">
            {bottomNav.map((item) =>
              renderLink(
                item,
                cn("flex flex-1 flex-col items-center gap-0.5 py-2 text-xs text-muted", item.active && "text-primary"),
                <>
                  {item.icon}
                  <span>{item.label}</span>
                </>,
              ),
            )}
          </nav>
        )}
      </div>
    </div>
  );
}
