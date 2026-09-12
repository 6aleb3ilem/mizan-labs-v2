import type { Meta, StoryObj } from "@storybook/react-vite";
import { Plus } from "lucide-react";

import { Button } from "../components/Button";

const meta = {
  title: "Actions/Button",
  component: Button,
  args: { children: "Enregistrer", variant: "primary", size: "md" },
  argTypes: { variant: { control: "select", options: ["primary", "secondary", "outline", "ghost", "danger", "link"] }, size: { control: "select", options: ["sm", "md", "lg"] } },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};
export const Loading: Story = { args: { loading: true } };
export const WithIcon: Story = { args: { leftIcon: <Plus className="size-4" aria-hidden />, children: "Nouveau devis" } };
export const Danger: Story = { args: { variant: "danger", children: "Supprimer" } };
export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      {(["primary", "secondary", "outline", "ghost", "danger", "link"] as const).map((variant) => (
        <Button key={variant} variant={variant}>
          {variant}
        </Button>
      ))}
    </div>
  ),
};
