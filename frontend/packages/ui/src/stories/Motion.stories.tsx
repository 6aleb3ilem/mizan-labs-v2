/**
 * The motion system, laid out so it can be judged rather than described.
 *
 * Open these with the browser's animation inspector slowed to 25 %: every surface should be
 * decelerating on the way in and accelerating on the way out, and nothing should be moving
 * more than about 12 px.
 */
import { DURATION, EASING } from "@mizan/tokens";
import type { Meta, StoryObj } from "@storybook/react-vite";
import { Copy, Download, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "../components/Button";
import { Logo, LogoMark } from "../components/Logo";
import { AnimatedNumber, Kbd, Skeleton, SkeletonRows, Spinner, useModifierKey } from "../components/Motion";
import { ConfirmDialog, Dialog, DropdownMenu, Drawer, Tooltip } from "../components/Overlay";
import { ToastProvider, useToast } from "../components/Toast";

const meta = { title: "Foundations/Motion" } satisfies Meta;
export default meta;
type Story = StoryObj;

/** The token table, rendered as the curves themselves rather than as numbers. */
export const Curves: Story = {
  render: () => (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="mb-1 text-md font-semibold">Durations</h3>
        <p className="mb-3 text-sm text-muted">Hover a bar to run it. Exits use 70 % of the enter duration.</p>
        <div className="flex flex-col gap-2">
          {(Object.entries(DURATION) as [keyof typeof DURATION, number][]).map(([name, ms]) => (
            <div key={name} className="group flex items-center gap-3">
              <span className="w-20 text-sm text-muted">{name}</span>
              <span className="tabular w-14 text-sm">{ms}ms</span>
              <div className="h-8 flex-1 overflow-hidden rounded-control bg-subtle">
                <div
                  className="h-full w-12 rounded-control bg-primary transition-transform group-hover:translate-x-[calc(100%*6)]"
                  style={{ transitionDuration: `${ms}ms`, transitionTimingFunction: EASING.out }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div>
        <h3 className="mb-1 text-md font-semibold">Easing</h3>
        <p className="mb-3 text-sm text-muted">All 260 ms, so only the curve differs.</p>
        <div className="flex flex-col gap-2">
          {(Object.entries(EASING) as [keyof typeof EASING, string][]).map(([name, curve]) => (
            <div key={name} className="group flex items-center gap-3">
              <span className="w-24 text-sm text-muted">{name}</span>
              <div className="h-8 flex-1 overflow-hidden rounded-control bg-subtle">
                <div
                  className="h-full w-12 rounded-control bg-info transition-transform duration-[260ms] group-hover:translate-x-[calc(100%*6)]"
                  style={{ transitionTimingFunction: curve }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  ),
};

export const Brand: Story = {
  render: () => (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end gap-8">
        <Logo size={24} />
        <Logo size={32} />
        <Logo size={48} />
        <Logo size={64} />
      </div>
      <div className="flex flex-wrap items-end gap-6">
        <LogoMark size={16} />
        <LogoMark size={24} />
        <LogoMark size={40} />
        <LogoMark size={72} />
      </div>
      <p className="max-w-prose text-sm text-muted">
        The mark keeps its own colours in both themes; only the level bar follows the text colour. The
        tenant&apos;s primary re-brands documents and accents, never the platform mark.
      </p>
    </div>
  ),
};

/** Hover the stack: three toasts collapsed into one, fanning out to be read. */
export const Toasts: Story = {
  render: () => (
    <ToastProvider>
      <ToastDemo />
    </ToastProvider>
  ),
};

function ToastDemo() {
  const toast = useToast();
  return (
    <div className="flex flex-col gap-3">
      <p className="max-w-prose text-sm text-muted">
        Push several, then hover the stack to expand it — timers pause while it is open. Drag a toast
        to the right to dismiss it.
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => toast.success("Devis DEV-2026-0184 envoyé", "Le client a reçu le lien du portail.")}>
          Success
        </Button>
        <Button variant="outline" onClick={() => toast.info("Import en cours", "412 lignes sur 900.")}>
          Info
        </Button>
        <Button variant="outline" onClick={() => toast.warning("3 essais en retard", "Département béton, échéance dépassée.")}>
          Warning
        </Button>
        <Button
          variant="outline"
          onClick={() =>
            toast.show({
              title: "Échec de l'envoi",
              description: "Le serveur de messagerie n'a pas répondu.",
              tone: "danger",
              action: { label: "Réessayer", onClick: () => toast.success("Envoyé") },
            })
          }
        >
          Error with action
        </Button>
      </div>
    </div>
  );
}

export const Surfaces: Story = {
  render: () => <SurfacesDemo />,
};

function SurfacesDemo() {
  const [dialog, setDialog] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [drawer, setDrawer] = useState(false);
  const [sheet, setSheet] = useState(false);
  const modifier = useModifierKey();
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => setDialog(true)}>
          Dialog
        </Button>
        <Button variant="outline" onClick={() => setConfirm(true)}>
          Confirm
        </Button>
        <Button variant="outline" onClick={() => setDrawer(true)}>
          Drawer
        </Button>
        <Button variant="outline" onClick={() => setSheet(true)}>
          Bottom sheet (draggable)
        </Button>
        <Tooltip content="Copier la référence" shortcut={<Kbd>{modifier} C</Kbd>}>
          <Button variant="ghost" size="icon" aria-label="Copier">
            <Copy className="size-4" aria-hidden />
          </Button>
        </Tooltip>
        <DropdownMenu
          trigger={<Button variant="outline">Menu</Button>}
          items={[
            { key: "export", label: "Exporter", icon: <Download className="size-4" aria-hidden />, shortcut: <Kbd>{modifier} E</Kbd> },
            { key: "duplicate", label: "Dupliquer", icon: <Copy className="size-4" aria-hidden /> },
            { key: "sep", label: "", separator: true },
            { key: "delete", label: "Supprimer", icon: <Trash2 className="size-4" aria-hidden />, destructive: true },
          ]}
        />
      </div>

      <Dialog open={dialog} onOpenChange={setDialog} title="Nouveau prélèvement" description="Le dialogue monte de 8 px et se pose.">
        <p className="text-sm text-muted">Le fond se floute de 2 px : la page reste lisible derrière, sans distraire.</p>
      </Dialog>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Annuler la série d'essais ?"
        consequences="3 essais programmés seront annulés et le client sera notifié."
        confirmLabel="Annuler la série"
        cancelLabel="Revenir"
        destructive
        onConfirm={() => setConfirm(false)}
      />
      <Drawer open={drawer} onOpenChange={setDrawer} title="Fiche client" description="Panneau latéral, courbe spring.">
        <p className="text-sm text-muted">Un tiroir portant un formulaire n&apos;est pas glissable : un geste mal placé perdrait la saisie.</p>
      </Drawer>
      <Drawer open={sheet} onOpenChange={setSheet} side="bottom" title="Filtres" description="Glissez la poignée vers le bas.">
        <p className="text-sm text-muted">
          La feuille suit le doigt, résiste vers le haut, et se ferme au-delà de 35 % de sa hauteur ou sur un
          geste rapide.
        </p>
      </Drawer>
    </div>
  );
}

export const LoadingStates: Story = {
  render: () => <LoadingDemo />,
};

function LoadingDemo() {
  const [count, setCount] = useState(128);
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="mb-2 text-md font-semibold">Skeletons</h3>
        <div className="rounded-card border border-line bg-surface">
          <SkeletonRows rows={4} columns={4} />
        </div>
        <div className="mt-3 flex items-center gap-3">
          <Skeleton shape="circle" className="size-10" />
          <div className="flex flex-1 flex-col gap-2">
            <Skeleton shape="text" width="40%" />
            <Skeleton shape="text" width="65%" />
          </div>
        </div>
      </div>
      <div>
        <h3 className="mb-2 text-md font-semibold">Spinner</h3>
        <p className="mb-2 text-sm text-muted">Held back 400 ms: a request that resolves quickly shows nothing at all.</p>
        <div className="flex items-center gap-6">
          <Spinner delay={0} label="Immédiat" />
          <Spinner delay={400} label="Après 400 ms" />
        </div>
      </div>
      <div>
        <h3 className="mb-2 text-md font-semibold">Animated number</h3>
        <div className="flex items-center gap-4">
          <AnimatedNumber value={count} className="text-2xl font-semibold" />
          <Button variant="outline" size="sm" onClick={() => setCount((c) => c + 37)}>
            +37
          </Button>
          <Button variant="outline" size="sm" onClick={() => setCount((c) => Math.max(0, c - 91))}>
            −91
          </Button>
        </div>
      </div>
    </div>
  );
}
