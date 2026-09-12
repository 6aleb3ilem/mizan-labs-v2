import type { Meta, StoryObj } from "@storybook/react-vite";
import { PALETTE_HUES } from "@mizan/tokens";

import { Badge } from "../components/Badge";

const meta = { title: "Data display/Badge", component: Badge, args: { children: "Envoyé", tone: "blue" } } satisfies Meta<typeof Badge>;
export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Palette: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      {PALETTE_HUES.map((hue) => (
        <Badge key={hue} tone={hue} dot>
          {hue}
        </Badge>
      ))}
      <Badge tone="success">validé</Badge>
      <Badge tone="warning">à valider</Badge>
      <Badge tone="danger">en retard</Badge>
      <Badge tone="primary">sélection</Badge>
    </div>
  ),
};
