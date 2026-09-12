/** Global search results grouped by type (SPEC §21.9); navigation targets are the route map. */
import { useTranslation } from "@mizan/i18n";
import { EmptyState, PageHeader, SearchInput } from "@mizan/ui";
import { useState } from "react";

import { useSpaces } from "../shell";
import { Link } from "@tanstack/react-router";

export function SearchPage() {
  const { t } = useTranslation();
  const [q, setQ] = useState("");
  const spaces = useSpaces();
  const needle = q.trim().toLowerCase();
  const hits = needle ? spaces.flatMap((s) => s.entries.filter((e) => e.label.toLowerCase().includes(needle)).map((e) => ({ ...e, space: s.label }))) : [];
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={t("common.search")} />
      <SearchInput value={q} onChange={(e) => setQ(e.target.value)} onClear={() => setQ("")} placeholder={t("common.search")} aria-label={t("common.search")} autoFocus className="max-w-xl" />
      {needle && hits.length === 0 ? (
        <EmptyState title={t("common.empty_title")} hint={t("common.not_found_hint")} kind="search" />
      ) : (
        <ul className="flex flex-col divide-y divide-line rounded-card border border-line bg-surface">
          {hits.map((hit) => (
            <li key={hit.href}>
              <Link to={hit.href as never} className="flex items-center justify-between px-4 py-2 hover:bg-subtle">
                <span>{hit.label}</span>
                <span className="text-xs text-muted">{hit.space}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
