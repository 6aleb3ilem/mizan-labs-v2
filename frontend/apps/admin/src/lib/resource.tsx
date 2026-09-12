/** Shared building blocks of the configuration screens: list page, record drawer form, mutations. */
import { ApiError, useApi } from "@mizan/api-client";
import { useErrorToast } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import { Button, DataTable, Drawer, ErrorState, PageHeader, SearchInput, type ColumnDef } from "@mizan/ui";
import { useMutation, useQuery, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";

export function useList<T>(queryKey: QueryKey, fetcher: () => Promise<T[] | undefined>, options?: { enabled?: boolean }) {
  return useQuery({ queryKey, queryFn: async () => (await fetcher()) ?? [], enabled: options?.enabled ?? true });
}

/** A mutation that invalidates the given keys and toasts problem details; returns field errors on failure. */
export function useSave<TVars, TResult>(mutate: (vars: TVars) => Promise<TResult>, invalidate: QueryKey[], onSuccess?: (result: TResult) => void) {
  const queryClient = useQueryClient();
  const errorToast = useErrorToast();
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const mutation = useMutation({
    mutationFn: mutate,
    onSuccess: async (result) => {
      setFieldErrors({});
      await Promise.all(invalidate.map((key) => queryClient.invalidateQueries({ queryKey: key })));
      onSuccess?.(result);
    },
    onError: (error) => setFieldErrors(errorToast(error)),
  });
  return { ...mutation, fieldErrors, setFieldErrors };
}

export function textOf(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export type ListPageProps<T> = {
  title: ReactNode;
  subtitle?: ReactNode;
  columns: ColumnDef<T, unknown>[];
  rows: T[] | undefined;
  loading: boolean;
  error?: unknown;
  onRetry?: () => void;
  getRowId: (row: T) => string;
  searchable?: (row: T, needle: string) => boolean;
  onRowClick?: (row: T) => void;
  createLabel?: string;
  onCreate?: () => void;
  canCreate?: boolean;
  actions?: ReactNode;
  toolbar?: ReactNode;
  emptyHint?: ReactNode;
  selectable?: boolean;
  bulkActions?: (rows: T[]) => ReactNode;
};

/** List page pattern (SPEC §21.5): header → toolbar (search, filters, new) → table. */
export function ListPage<T>({ title, subtitle, columns, rows, loading, error, onRetry, getRowId, searchable, onRowClick, createLabel, onCreate, canCreate = true, actions, toolbar, emptyHint, selectable, bulkActions }: ListPageProps<T>) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const filtered = useMemo(() => {
    if (!rows) return [];
    const needle = search.trim().toLowerCase();
    if (!needle || !searchable) return rows;
    return rows.filter((row) => searchable(row, needle));
  }, [rows, search, searchable]);
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={title}
        subtitle={subtitle}
        actions={
          <>
            {actions}
            {onCreate && canCreate && (
              <Button onClick={onCreate} leftIcon={<Plus className="size-4" aria-hidden />}>
                {createLabel ?? t("common.new")}
              </Button>
            )}
          </>
        }
      />
      <div className="flex flex-wrap items-center gap-2">
        {searchable && <SearchInput value={search} onChange={(e) => setSearch(e.target.value)} onClear={() => setSearch("")} placeholder={t("common.search")} className="w-72 max-w-full" aria-label={t("common.search")} />}
        {toolbar}
        {rows && <span className="text-sm text-muted">{t("common.results", { count: filtered.length })}</span>}
      </div>
      {error ? (
        <ErrorState title={t("common.error_title")} detail={ApiError.is(error) ? error.message : undefined} onRetry={onRetry} retryLabel={t("common.retry")} />
      ) : (
        <DataTable columns={columns} data={filtered} getRowId={getRowId} loading={loading} onRowClick={onRowClick} emptyTitle={t("common.empty_title")} emptyHint={emptyHint ?? t("common.empty_hint")} columnPicker columnsLabel={t("common.columns")} selectable={selectable} bulkActions={bulkActions} />
      )}
    </div>
  );
}

export type RecordDrawerProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  onSubmit: () => void;
  saving?: boolean;
  submitLabel?: string;
  children: ReactNode;
  extraActions?: ReactNode;
  width?: string;
};

/** Record drawer with the form pattern (SPEC §21.5): single column, sticky actions, double-submit lock. */
export function RecordDrawer({ open, onOpenChange, title, description, onSubmit, saving, submitLabel, children, extraActions, width }: RecordDrawerProps) {
  const { t } = useTranslation();
  return (
    <Drawer
      open={open}
      onOpenChange={onOpenChange}
      title={title}
      description={description}
      width={width}
      closeLabel={t("common.close")}
      footer={
        <>
          {extraActions}
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button onClick={onSubmit} loading={saving}>
            {submitLabel ?? t("common.save")}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!saving) onSubmit();
        }}
      >
        {children}
        <button type="submit" className="hidden" aria-hidden />
      </form>
    </Drawer>
  );
}

export function useApiClient() {
  return useApi().client;
}
