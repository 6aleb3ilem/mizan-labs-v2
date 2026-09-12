import type { Meta, StoryObj } from "@storybook/react-vite";
import { Bell, FlaskConical, Home, Landmark, Search } from "lucide-react";
import { useState } from "react";

import { AppShell } from "../components/AppShell";
import { Button } from "../components/Button";
import { CommandPalette } from "../components/CommandPalette";
import { KpiCard, PageHeader } from "../components/Navigation";

const meta = { title: "Layout/AppShell", component: AppShell } satisfies Meta<typeof AppShell>;
export default meta;

export const BackOffice: StoryObj = {
  render: function Render() {
    const [open, setOpen] = useState(false);
    return (
      <AppShell
        brand={<span className="text-md font-semibold">Mizan Labs</span>}
        sections={[
          { key: "main", items: [{ key: "home", label: "Accueil", href: "#", icon: <Home className="size-4" />, active: true }] },
          { key: "spaces", label: "Espaces", items: [{ key: "lab", label: "Laboratoire", href: "#", icon: <FlaskConical className="size-4" /> }, { key: "fin", label: "Finance", href: "#", icon: <Landmark className="size-4" /> }] },
        ]}
        renderLink={(item, className, children) => (
          <a key={item.key} href={item.href} className={className} aria-current={item.active ? "page" : undefined}>
            {children}
          </a>
        )}
        topbar={
          <>
            <Button variant="outline" size="sm" leftIcon={<Search className="size-4" aria-hidden />} onClick={() => setOpen(true)}>
              Rechercher… ⌘K
            </Button>
            <span className="flex-1" />
            <Button variant="ghost" size="icon-sm" aria-label="Notifications">
              <Bell className="size-4" aria-hidden />
            </Button>
          </>
        }
        offline
        offlineMessage="Hors ligne — 3 modifications en attente"
        onScan={() => undefined}
        bottomNav={[{ key: "home", label: "Accueil", href: "#", icon: <Home className="size-5" />, active: true }, { key: "lab", label: "Labo", href: "#", icon: <FlaskConical className="size-5" /> }]}
      >
        <PageHeader title="Ma journée" subtitle="Mardi 12 septembre" actions={<Button>Nouvelle réception</Button>} />
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <KpiCard label="Essais à faire" value="12" />
          <KpiCard label="En retard" value="2" tone="danger" />
          <KpiCard label="À valider" value="7" tone="warning" />
          <KpiCard label="Réceptions" value="4" />
        </div>
        <CommandPalette open={open} onOpenChange={setOpen} items={[{ id: "1", group: "Navigation", label: "Nouvelle réception", onSelect: () => undefined }]} />
      </AppShell>
    );
  },
};
