import type { Meta, StoryObj } from "@storybook/react-vite";

import { Badge } from "../components/Badge";
import { Button } from "../components/Button";
import { DataTable, type ColumnDef } from "../components/DataTable";

type Quote = { id: string; number: string; account: string; total: string; state: string; hue: string };
const rows: Quote[] = Array.from({ length: 30 }, (_, i) => ({
  id: String(i),
  number: `DV-NKC-2026-${String(i + 1).padStart(5, "0")}`,
  account: ["SOGECO", "ATTM", "SNIM"][i % 3]!,
  total: `${(12000 + i * 1500).toFixed(2)}`,
  state: ["DRAFT", "SENT", "ACCEPTED"][i % 3]!,
  hue: ["slate", "blue", "green"][i % 3]!,
}));
const columns: ColumnDef<Quote, unknown>[] = [
  { accessorKey: "number", header: "Numéro" },
  { accessorKey: "account", header: "Compte" },
  { accessorKey: "total", header: "Total", cell: (c) => <span className="tabular">{c.getValue<string>()} MRU</span> },
  { accessorKey: "state", header: "État", cell: (c) => <Badge tone={c.row.original.hue}>{c.getValue<string>()}</Badge> },
];

const meta = { title: "Data display/DataTable", component: DataTable<Quote>, args: { columns, data: rows, columnPicker: true } } satisfies Meta<typeof DataTable<Quote>>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Selectable: Story = { args: { selectable: true, bulkActions: (selected) => <Button size="sm">Envoyer ({selected.length})</Button> } };
export const Loading: Story = { args: { data: [], loading: true } };
export const Empty: Story = { args: { data: [], emptyTitle: "Aucun devis", emptyHint: "Créez le premier devis depuis un projet.", emptyAction: <Button>Nouveau devis</Button> } };
export const Virtualised: Story = { args: { data: Array.from({ length: 2000 }, (_, i) => ({ ...rows[i % 30]!, id: String(i) })), virtualiseAfter: 100 } };
