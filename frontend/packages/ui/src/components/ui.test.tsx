import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Button } from "./Button";
import { DataTable, type ColumnDef } from "./DataTable";
import { FormField } from "./FormField";
import { Input } from "./Input";
import { Badge } from "./Badge";

describe("Button", () => {
  it("is disabled and busy while loading", () => {
    render(<Button loading>Save</Button>);
    const button = screen.getByRole("button", { name: /save/i });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("aria-busy", "true");
  });
});

describe("FormField", () => {
  it("links the label, help and error to the control", () => {
    render(
      <FormField label="Code" help="Uppercase" error="Required">
        <Input />
      </FormField>,
    );
    const input = screen.getByLabelText("Code");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Required");
    expect(input.getAttribute("aria-describedby")).toContain("-error");
  });
});

describe("DataTable", () => {
  type Row = { id: string; name: string };
  const columns: ColumnDef<Row, unknown>[] = [{ accessorKey: "name", header: "Name" }];

  it("renders rows, empty state and load more", () => {
    const onLoadMore = vi.fn();
    const { rerender } = render(<DataTable columns={columns} data={[{ id: "1", name: "SOGECO" }]} getRowId={(r) => r.id} hasMore onLoadMore={onLoadMore} loadMoreLabel="More" />);
    expect(screen.getByText("SOGECO")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "More" }));
    expect(onLoadMore).toHaveBeenCalled();
    rerender(<DataTable columns={columns} data={[]} emptyTitle="Nothing" />);
    expect(screen.getByText("Nothing")).toBeInTheDocument();
  });

  it("selects rows and shows the bulk bar", () => {
    render(<DataTable columns={columns} data={[{ id: "1", name: "A" }, { id: "2", name: "B" }]} getRowId={(r) => r.id} selectable bulkActions={(rows) => <span>{rows.length} selected</span>} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Select all" }));
    expect(screen.getByRole("toolbar", { name: "Bulk actions" })).toHaveTextContent("2 selected");
  });
});

describe("Badge", () => {
  it("maps semantic tones to palette colours", () => {
    render(<Badge tone="success">ok</Badge>);
    expect(screen.getByText("ok").style.color).not.toBe("");
  });
});
