import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowSelectionState,
  type VisibilityState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Columns3 } from "lucide-react";
import { DropdownMenu as RadixDropdown } from "radix-ui";
import { useRef, useState, type ReactNode } from "react";

import { cn } from "../cn";
import { Button } from "./Button";
import { Checkbox } from "./Toggle";
import { EmptyState, SkeletonRows } from "./Feedback";

export type { ColumnDef };

export type DataTableProps<T> = {
  columns: ColumnDef<T, unknown>[];
  data: T[];
  getRowId?: (row: T) => string;
  loading?: boolean;
  /** Cursor pagination: a "load more" button appears while `hasMore`. */
  hasMore?: boolean;
  onLoadMore?: () => void;
  loadMoreLabel?: string;
  emptyTitle?: ReactNode;
  emptyHint?: ReactNode;
  emptyAction?: ReactNode;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  selection?: RowSelectionState;
  onSelectionChange?: (selection: RowSelectionState) => void;
  bulkActions?: (selectedRows: T[]) => ReactNode;
  columnPicker?: boolean;
  columnsLabel?: string;
  footer?: ReactNode;
  dense?: boolean;
  className?: string;
  /** Rows beyond this count are virtualised. */
  virtualiseAfter?: number;
  maxHeight?: string;
};

/** Data table (SPEC §21.4): server pagination, column picker, row selection with bulk bar, virtual rows. */
export function DataTable<T>({
  columns,
  data,
  getRowId,
  loading,
  hasMore,
  onLoadMore,
  loadMoreLabel = "Load more",
  emptyTitle = "Nothing to show",
  emptyHint,
  emptyAction,
  onRowClick,
  selectable,
  selection,
  onSelectionChange,
  bulkActions,
  columnPicker,
  columnsLabel = "Columns",
  footer,
  dense,
  className,
  virtualiseAfter = 200,
  maxHeight = "70vh",
}: DataTableProps<T>) {
  const [internalSelection, setInternalSelection] = useState<RowSelectionState>({});
  const [visibility, setVisibility] = useState<VisibilityState>({});
  const rowSelection = selection ?? internalSelection;
  const setRowSelection = (updater: RowSelectionState | ((old: RowSelectionState) => RowSelectionState)) => {
    const next = typeof updater === "function" ? updater(rowSelection) : updater;
    (onSelectionChange ?? setInternalSelection)(next);
  };

  const allColumns: ColumnDef<T, unknown>[] = selectable
    ? [
        {
          id: "__select",
          size: 36,
          enableHiding: false,
          header: ({ table }) => (
            <Checkbox
              aria-label="Select all"
              checked={table.getIsAllRowsSelected() ? true : table.getIsSomeRowsSelected() ? "indeterminate" : false}
              onCheckedChange={(v) => table.toggleAllRowsSelected(v)}
            />
          ),
          cell: ({ row }) => (
            <div onClick={(e) => e.stopPropagation()}>
              <Checkbox aria-label="Select row" checked={row.getIsSelected()} onCheckedChange={(v) => row.toggleSelected(v)} />
            </div>
          ),
        },
        ...columns,
      ]
    : columns;

  const table = useReactTable({
    data,
    columns: allColumns,
    getRowId,
    state: { rowSelection, columnVisibility: visibility },
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setVisibility,
    enableRowSelection: !!selectable,
    getCoreRowModel: getCoreRowModel(),
  });

  const rows = table.getRowModel().rows;
  const virtual = rows.length > virtualiseAfter;
  const scrollRef = useRef<HTMLDivElement>(null);
  const rowHeight = dense ? 32 : 40;
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => rowHeight,
    overscan: 12,
    enabled: virtual,
  });
  const selectedRows = table.getSelectedRowModel().rows.map((r) => r.original);
  const cell = dense ? "px-3 py-1.5" : "px-3 py-2.5";

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {(columnPicker || (selectable && selectedRows.length > 0)) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            {selectable && selectedRows.length > 0 && (
              <div role="toolbar" aria-label="Bulk actions" className="flex items-center gap-2 rounded-control bg-primary-subtle px-3 py-1.5 text-sm">
                <span className="font-medium">{selectedRows.length}</span>
                {bulkActions?.(selectedRows)}
              </div>
            )}
          </div>
          {columnPicker && (
            <RadixDropdown.Root>
              <RadixDropdown.Trigger asChild>
                <Button variant="outline" size="sm" leftIcon={<Columns3 className="size-4" aria-hidden />}>
                  {columnsLabel}
                </Button>
              </RadixDropdown.Trigger>
              <RadixDropdown.Portal>
                <RadixDropdown.Content align="end" sideOffset={4} className="z-50 min-w-44 rounded-card border border-line bg-surface p-1 shadow-3">
                  {table
                    .getAllLeafColumns()
                    .filter((c) => c.getCanHide())
                    .map((column) => (
                      <RadixDropdown.CheckboxItem
                        key={column.id}
                        checked={column.getIsVisible()}
                        onCheckedChange={(v) => column.toggleVisibility(!!v)}
                        className="flex cursor-default select-none items-center gap-2 rounded-control px-2 py-1.5 text-base outline-none data-[highlighted]:bg-subtle"
                      >
                        <span className={cn("size-3 rounded-sm border border-line", column.getIsVisible() && "bg-primary")} aria-hidden />
                        {typeof column.columnDef.header === "string" ? column.columnDef.header : column.id}
                      </RadixDropdown.CheckboxItem>
                    ))}
                </RadixDropdown.Content>
              </RadixDropdown.Portal>
            </RadixDropdown.Root>
          )}
        </div>
      )}
      <div ref={scrollRef} className="overflow-auto rounded-card border border-line bg-surface" style={virtual ? { maxHeight } : undefined}>
        <table className="w-full border-collapse text-base">
          <thead className="sticky top-0 z-10 bg-subtle text-left text-xs font-semibold uppercase tracking-wide text-muted">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => (
                  <th key={header.id} scope="col" className={cn(cell, "whitespace-nowrap border-b border-line")} style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}>
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {loading && rows.length === 0 ? (
              <tr>
                <td colSpan={allColumns.length} className="p-3">
                  <SkeletonRows rows={5} />
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={allColumns.length} className="p-3">
                  <EmptyState title={emptyTitle} hint={emptyHint} action={emptyAction} />
                </td>
              </tr>
            ) : virtual ? (
              <>
                {virtualizer.getVirtualItems().length > 0 && (
                  <tr style={{ height: virtualizer.getVirtualItems()[0]!.start }} aria-hidden>
                    <td colSpan={allColumns.length} />
                  </tr>
                )}
                {virtualizer.getVirtualItems().map((item) => {
                  const row = rows[item.index]!;
                  return (
                    <tr
                      key={row.id}
                      data-index={item.index}
                      onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                      className={cn("border-b border-line last:border-b-0 hover:bg-subtle", onRowClick && "cursor-pointer", row.getIsSelected() && "bg-primary-subtle")}
                      style={{ height: rowHeight }}
                    >
                      {row.getVisibleCells().map((c) => (
                        <td key={c.id} className={cn(cell, "whitespace-nowrap")}>
                          {flexRender(c.column.columnDef.cell, c.getContext())}
                        </td>
                      ))}
                    </tr>
                  );
                })}
                <tr style={{ height: virtualizer.getTotalSize() - (virtualizer.getVirtualItems().at(-1)?.end ?? 0) }} aria-hidden>
                  <td colSpan={allColumns.length} />
                </tr>
              </>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={onRowClick ? () => onRowClick(row.original) : undefined}
                  className={cn("border-b border-line last:border-b-0 hover:bg-subtle", onRowClick && "cursor-pointer", row.getIsSelected() && "bg-primary-subtle")}
                >
                  {row.getVisibleCells().map((c) => (
                    <td key={c.id} className={cn(cell, "align-middle")}>
                      {flexRender(c.column.columnDef.cell, c.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
          {footer && (
            <tfoot className="bg-subtle text-sm font-medium">
              <tr>
                <td colSpan={allColumns.length} className={cell}>
                  {footer}
                </td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      {hasMore && onLoadMore && (
        <div className="flex justify-center">
          <Button variant="outline" size="sm" onClick={onLoadMore} loading={loading}>
            {loadMoreLabel}
          </Button>
        </div>
      )}
    </div>
  );
}
