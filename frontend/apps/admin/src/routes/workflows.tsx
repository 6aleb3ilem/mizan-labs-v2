/**
 * Workflow editor (SPEC §23.3, §10.4).
 *
 * A workflow is the state machine behind a record kind — what states a quote can be in, which
 * transitions are allowed, what must be true to take one (guards) and what happens when it is
 * taken (effects). States are configurable but each must map onto a fixed *semantic*, because
 * the rest of the platform reasons about semantics, not labels: an invoice is payable when its
 * state means ISSUED, whatever the tenant calls it.
 *
 * The editing model is deliberately blunt:
 *
 * - **Only drafts are editable.** An active workflow governs live records; changing it under
 *   them would leave records in states that no longer exist. Editing means a new version.
 * - **Validate, then simulate, then activate.** Validation catches the structural faults (no
 *   initial state, unreachable states, a semantic left uncovered). Simulation runs a sequence of
 *   actions through the machine and reports where it ends up or which guard stopped it. Both are
 *   server-side, against the same engine that will run in production.
 * - **The whole definition is written at once.** `PUT` replaces states and transitions together,
 *   so the machine is never briefly half-edited.
 */
import { useApi } from "@mizan/api-client";
import { useSession } from "@mizan/app-kit";
import { useTranslation } from "@mizan/i18n";
import {
  Alert,
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  FormField,
  Input,
  LabelsInput,
  PageHeader,
  Select,
  Switch,
  Textarea,
  Tooltip,
  useToast,
} from "@mizan/ui";
import { useNavigate, useParams } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, Play, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { useList, useSave } from "../lib/resource";

type State = {
  id?: string;
  code: string;
  semantic: string;
  labels: Record<string, string>;
  colour: string;
  is_initial: boolean;
  is_terminal: boolean;
  sla_days: number | null;
  ord: number;
};

type Transition = {
  id?: string;
  from_state_id: string | null;
  to_state_id: string;
  required_action: string;
  guards: unknown[];
  effects: unknown[];
  labels: Record<string, string>;
  ord: number;
};

type Workflow = {
  id: string;
  kind: string;
  branch_id: string | null;
  version: number;
  status: string;
  activated_at: string | null;
  states: State[];
  transitions: Transition[];
};

type Catalogue = { semantics: Record<string, string[]>; guards: string[]; effects: string[] };
type Problem = { loc?: unknown; msg?: string; [key: string]: unknown };

/** The draft shape: transitions reference state *codes*, since ids do not exist until saved. */
type DraftTransition = { from_code: string | null; to_code: string; required_action: string; guards: string[]; effects: string[] };

const HUES = ["slate", "gray", "red", "orange", "amber", "green", "teal", "blue", "indigo", "violet", "pink", "brown"];
const WORKFLOWS_KEY = ["workflows", "list", {}];

function statusTone(status: string): "success" | "amber" | "slate" {
  return status === "ACTIVE" ? "success" : status === "DRAFT" ? "amber" : "slate";
}

export function WorkflowsPage() {
  const { t } = useTranslation();
  const api = useApi();
  const session = useSession();
  const toast = useToast();
  const navigate = useNavigate();
  const params = useParams({ strict: false }) as { kind?: string };

  const workflows = useList<Workflow>(WORKFLOWS_KEY, async () => (await api.client.GET("/workflows")).data as Workflow[] | undefined, {
    enabled: session.can("workflow", "view"),
  });
  const catalogue = useList<Catalogue>(
    ["workflows", "semantics"],
    async () => {
      const result = (await api.client.GET("/workflows/semantics")).data;
      return result ? [result as Catalogue] : [];
    },
    { enabled: session.can("workflow", "view") },
  );
  const cat = catalogue.data?.[0];

  // The kind lives in the route, so a workflow can be linked to and reloaded straight into.
  const kinds = useMemo(() => [...new Set((workflows.data ?? []).map((w) => w.kind))].sort(), [workflows.data]);
  const kind = params.kind ?? kinds[0] ?? "";
  const versions = useMemo(
    () => (workflows.data ?? []).filter((w) => w.kind === kind).sort((a, b) => b.version - a.version),
    [workflows.data, kind],
  );
  const workflow = versions[0];

  /* The draft mirrors the workflow it came from, so switching kind or version cannot show one
     machine's edits against another's baseline. */
  const [draft, setDraft] = useState<{ id: string; states: State[]; transitions: DraftTransition[] } | null>(null);
  const [validation, setValidation] = useState<Problem[] | null>(null);
  const [simulation, setSimulation] = useState<Record<string, unknown> | null>(null);
  const [actions, setActions] = useState("");
  const [activating, setActivating] = useState(false);

  const baseline = useMemo(() => {
    const states = [...(workflow?.states ?? [])].sort((a, b) => a.ord - b.ord);
    const byId = new Map(states.map((state) => [state.id, state.code]));
    const transitions: DraftTransition[] = [...(workflow?.transitions ?? [])]
      .sort((a, b) => a.ord - b.ord)
      .map((transition) => ({
        from_code: transition.from_state_id ? (byId.get(transition.from_state_id) ?? null) : null,
        to_code: byId.get(transition.to_state_id) ?? "",
        required_action: transition.required_action,
        guards: (transition.guards ?? []).map(String),
        effects: (transition.effects ?? []).map(String),
      }));
    return { states, transitions };
  }, [workflow]);

  const pending = draft?.id === workflow?.id ? draft : null;
  const states = pending?.states ?? baseline.states;
  const transitions = pending?.transitions ?? baseline.transitions;
  const dirty = pending !== null;
  const editable = workflow?.status === "DRAFT" && session.can("workflow", "configure");

  const mutate = (update: (next: { states: State[]; transitions: DraftTransition[] }) => void) => {
    if (!workflow) return;
    setDraft((current) => {
      const source = current?.id === workflow.id ? current : { id: workflow.id, states: baseline.states, transitions: baseline.transitions };
      const next = { states: [...source.states], transitions: [...source.transitions] };
      update(next);
      return { id: workflow.id, ...next };
    });
  };

  const save = useSave(
    async () =>
      (await api.client.PUT("/workflows/{workflow_id}/definition", {
        params: { path: { workflow_id: workflow!.id } },
        body: {
          states: states.map((state, index) => ({
            code: state.code,
            semantic: state.semantic,
            labels: state.labels,
            colour: state.colour,
            is_initial: state.is_initial,
            is_terminal: state.is_terminal,
            sla_days: state.sla_days,
            ord: index,
          })),
          transitions: transitions.map((transition) => ({
            from_code: transition.from_code,
            to_code: transition.to_code,
            required_action: transition.required_action,
            guards: transition.guards,
            effects: transition.effects,
          })),
        } as never,
      })).data,
    [WORKFLOWS_KEY],
    () => {
      setDraft(null);
      toast.success(t("common.saved"));
    },
  );

  const validate = useSave(async () => {
    const response = await api.client.POST("/workflows/{workflow_id}:validate", { params: { path: { workflow_id: workflow!.id } } });
    setValidation((response.data ?? []) as Problem[]);
    return response.data;
  }, []);

  const simulate = useSave(async () => {
    const response = await api.client.POST("/workflows/{workflow_id}:simulate", {
      params: { path: { workflow_id: workflow!.id } },
      body: { actions: actions.split(/[,\s]+/).filter(Boolean) } as never,
    });
    setSimulation((response.data ?? null) as Record<string, unknown> | null);
    return response.data;
  }, []);

  const newVersion = useSave(
    async () => (await api.client.POST("/workflows/{workflow_id}/versions", { params: { path: { workflow_id: workflow!.id } } })).data,
    [WORKFLOWS_KEY],
    () => toast.success(t("common.saved")),
  );

  const activate = useSave(
    async () => (await api.client.POST("/workflows/{workflow_id}:activate", { params: { path: { workflow_id: workflow!.id } } })).data,
    [WORKFLOWS_KEY],
    () => {
      setActivating(false);
      toast.success(t("common.saved"));
    },
  );

  const semantics = cat?.semantics?.[kind] ?? [];
  // Every semantic must be reachable, or the platform cannot ask "is this quote accepted?".
  const uncovered = semantics.filter((semantic) => !states.some((state) => state.semantic === semantic));

  if (workflows.isPending || catalogue.isPending) {
    return <PageHeader title={t("nav.admin.workflows")} subtitle={t("common.loading")} />;
  }

  if (!workflow) {
    return (
      <div className="flex flex-col gap-4">
        <PageHeader title={t("nav.admin.workflows")} />
        <EmptyState title={t("common.empty_title")} hint={t("common.empty_hint")} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title={t("nav.admin.workflows")}
        subtitle={kind}
        badges={
          <>
            <Badge tone={statusTone(workflow.status)}>{workflow.status}</Badge>
            <Badge tone="slate">v{workflow.version}</Badge>
            {dirty && <Badge tone="amber">{t("common.unsaved_changes")}</Badge>}
          </>
        }
        actions={
          <>
            <Select
              value={kind}
              onValueChange={(next) => void navigate({ to: "/workflows/$kind", params: { kind: next } })}
              className="w-48"
              options={kinds.map((value) => ({ value, label: value }))}
              aria-label={t("nav.admin.workflows")}
            />
            {workflow.status === "ACTIVE" && session.can("workflow", "configure") && (
              <Button variant="outline" onClick={() => newVersion.mutate(undefined as never)} loading={newVersion.isPending}>
                {t("common.version")} +1
              </Button>
            )}
            {editable && (
              <>
                {dirty && (
                  <Button variant="ghost" onClick={() => setDraft(null)}>
                    {t("common.cancel")}
                  </Button>
                )}
                <Button variant="outline" onClick={() => save.mutate(undefined as never)} loading={save.isPending} disabled={!dirty}>
                  {t("common.save")}
                </Button>
                <Button onClick={() => setActivating(true)} leftIcon={<CheckCircle2 className="size-4" aria-hidden />} disabled={dirty}>
                  {t("numbering.activate")}
                </Button>
              </>
            )}
          </>
        }
      />

      {workflow.status === "ACTIVE" && <Alert tone="info">{t("access.builtin_hint")}</Alert>}
      {uncovered.length > 0 && <Alert tone="warning">{`${t("common.required")}: ${uncovered.join(", ")}`}</Alert>}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title={
            <span className="flex items-center justify-between">
              {t("common.status")}
              {editable && (
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<Plus className="size-4" aria-hidden />}
                  onClick={() =>
                    mutate((next) => {
                      next.states = [
                        ...next.states,
                        {
                          code: "",
                          semantic: semantics[0] ?? "",
                          labels: { fr: "", en: "" },
                          colour: "slate",
                          is_initial: next.states.length === 0,
                          is_terminal: false,
                          sla_days: null,
                          ord: next.states.length,
                        },
                      ];
                    })
                  }
                >
                  {t("common.new")}
                </Button>
              )}
            </span>
          }
        >
          <div className="flex flex-col gap-3">
            {states.map((state, index) => (
              <div key={index} className="flex flex-col gap-3 rounded-card border border-line p-3">
                <div className="flex items-center justify-between gap-2">
                  <Badge tone={state.colour as never}>{state.code || "—"}</Badge>
                  <span className="flex items-center gap-1">
                    {state.is_initial && (
                      <Tooltip content="initial">
                        <Badge tone="teal">▶</Badge>
                      </Tooltip>
                    )}
                    {state.is_terminal && (
                      <Tooltip content="terminal">
                        <Badge tone="slate">■</Badge>
                      </Tooltip>
                    )}
                    {editable && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("common.delete")}
                        className="text-danger"
                        onClick={() => mutate((next) => void (next.states = next.states.filter((_, i) => i !== index)))}
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    )}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <FormField label={t("common.code")} required>
                    <Input
                      value={state.code}
                      disabled={!editable}
                      onChange={(e) =>
                        mutate((next) => void (next.states = next.states.map((s, i) => (i === index ? { ...s, code: e.target.value.toUpperCase() } : s))))
                      }
                    />
                  </FormField>
                  {/* The semantic is what the rest of the platform reasons about; the code and
                      label are the tenant's own words for it. */}
                  <FormField label="semantic" required>
                    <Select
                      value={state.semantic}
                      disabled={!editable}
                      onValueChange={(semantic) => mutate((next) => void (next.states = next.states.map((s, i) => (i === index ? { ...s, semantic } : s))))}
                      options={semantics.map((value) => ({ value, label: value }))}
                    />
                  </FormField>
                </div>
                <FormField label={t("common.labels")} required>
                  <LabelsInput
                    value={{ fr: state.labels?.["fr"] ?? "", en: state.labels?.["en"] ?? "" }}
                    disabled={!editable}
                    onChange={(labels) =>
                      mutate(
                        (next) =>
                          void (next.states = next.states.map((s, i) => (i === index ? { ...s, labels: { fr: labels.fr ?? "", en: labels.en ?? "" } } : s))),
                      )
                    }
                  />
                </FormField>
                <div className="grid grid-cols-2 gap-3">
                  <FormField label={t("org.colour")}>
                    <Select
                      value={state.colour}
                      disabled={!editable}
                      onValueChange={(colour) => mutate((next) => void (next.states = next.states.map((s, i) => (i === index ? { ...s, colour } : s))))}
                      options={HUES.map((hue) => ({ value: hue, label: <Badge tone={hue as never}>{hue}</Badge> }))}
                    />
                  </FormField>
                  <FormField label="SLA (days)" optionalLabel={t("common.optional")}>
                    <Input
                      type="number"
                      min={0}
                      value={state.sla_days === null ? "" : String(state.sla_days)}
                      disabled={!editable}
                      className="tabular"
                      onChange={(e) =>
                        mutate(
                          (next) =>
                            void (next.states = next.states.map((s, i) =>
                              i === index ? { ...s, sla_days: e.target.value === "" ? null : Number(e.target.value) } : s,
                            )),
                        )
                      }
                    />
                  </FormField>
                </div>
                <div className="flex gap-4">
                  <Switch
                    checked={state.is_initial}
                    disabled={!editable}
                    label="initial"
                    // Exactly one initial state: setting one clears the rest rather than
                    // leaving a machine with two entry points.
                    onCheckedChange={(checked) =>
                      mutate((next) => void (next.states = next.states.map((s, i) => ({ ...s, is_initial: checked ? i === index : s.is_initial && i !== index }))))
                    }
                  />
                  <Switch
                    checked={state.is_terminal}
                    disabled={!editable}
                    label="terminal"
                    onCheckedChange={(checked) => mutate((next) => void (next.states = next.states.map((s, i) => (i === index ? { ...s, is_terminal: checked } : s))))}
                  />
                </div>
              </div>
            ))}
            {states.length === 0 && <p className="text-sm text-muted">{t("common.empty_title")}</p>}
          </div>
        </Card>

        <div className="flex flex-col gap-4">
          <Card
            title={
              <span className="flex items-center justify-between">
                transitions
                {editable && (
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={<Plus className="size-4" aria-hidden />}
                    onClick={() =>
                      mutate((next) => {
                        next.transitions = [
                          ...next.transitions,
                          { from_code: next.states[0]?.code ?? null, to_code: next.states[1]?.code ?? next.states[0]?.code ?? "", required_action: "edit", guards: [], effects: [] },
                        ];
                      })
                    }
                  >
                    {t("common.new")}
                  </Button>
                )}
              </span>
            }
          >
            <div className="flex flex-col gap-3">
              {transitions.map((transition, index) => (
                <div key={index} className="flex flex-col gap-3 rounded-card border border-line p-3">
                  <div className="flex items-center gap-2">
                    <Select
                      value={transition.from_code ?? ""}
                      disabled={!editable}
                      allowEmpty
                      emptyLabel="∅"
                      className="flex-1"
                      onValueChange={(from_code) =>
                        mutate((next) => void (next.transitions = next.transitions.map((x, i) => (i === index ? { ...x, from_code: from_code || null } : x))))
                      }
                      options={states.map((state) => ({ value: state.code, label: state.code }))}
                      aria-label="from"
                    />
                    <ArrowRight className="size-4 shrink-0 text-muted" aria-hidden />
                    <Select
                      value={transition.to_code}
                      disabled={!editable}
                      className="flex-1"
                      onValueChange={(to_code) => mutate((next) => void (next.transitions = next.transitions.map((x, i) => (i === index ? { ...x, to_code } : x))))}
                      options={states.map((state) => ({ value: state.code, label: state.code }))}
                      aria-label="to"
                    />
                    {editable && (
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        aria-label={t("common.delete")}
                        className="text-danger"
                        onClick={() => mutate((next) => void (next.transitions = next.transitions.filter((_, i) => i !== index)))}
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    )}
                  </div>
                  <FormField label="action" required>
                    <Input
                      value={transition.required_action}
                      disabled={!editable}
                      className="tabular"
                      onChange={(e) =>
                        mutate((next) => void (next.transitions = next.transitions.map((x, i) => (i === index ? { ...x, required_action: e.target.value } : x))))
                      }
                    />
                  </FormField>
                  <div className="grid grid-cols-2 gap-3">
                    <FormField label="guards" optionalLabel={t("common.optional")}>
                      <Select
                        value={transition.guards[0] ?? ""}
                        disabled={!editable}
                        allowEmpty
                        emptyLabel={t("common.none")}
                        onValueChange={(guard) =>
                          mutate((next) => void (next.transitions = next.transitions.map((x, i) => (i === index ? { ...x, guards: guard ? [guard] : [] } : x))))
                        }
                        options={(cat?.guards ?? []).map((value) => ({ value, label: value }))}
                      />
                    </FormField>
                    <FormField label="effects" optionalLabel={t("common.optional")}>
                      <Select
                        value={transition.effects[0] ?? ""}
                        disabled={!editable}
                        allowEmpty
                        emptyLabel={t("common.none")}
                        onValueChange={(effect) =>
                          mutate((next) => void (next.transitions = next.transitions.map((x, i) => (i === index ? { ...x, effects: effect ? [effect] : [] } : x))))
                        }
                        options={(cat?.effects ?? []).map((value) => ({ value, label: value }))}
                      />
                    </FormField>
                  </div>
                  {transition.guards.length + transition.effects.length > 1 && (
                    <p className="text-xs text-muted">{[...transition.guards, ...transition.effects].join(" · ")}</p>
                  )}
                </div>
              ))}
              {transitions.length === 0 && <p className="text-sm text-muted">{t("common.empty_title")}</p>}
            </div>
          </Card>

          <Card title={t("common.preview")}>
            <div className="flex flex-col gap-3">
              <Button variant="outline" onClick={() => validate.mutate(undefined as never)} loading={validate.isPending}>
                {t("common.confirm")}
              </Button>
              {validation !== null &&
                (validation.length === 0 ? (
                  <Alert tone="success">{t("common.saved")}</Alert>
                ) : (
                  <ul className="flex flex-col gap-1">
                    {validation.map((problem, index) => (
                      <li key={index} className="text-sm text-danger">
                        {problem.msg ?? JSON.stringify(problem)}
                      </li>
                    ))}
                  </ul>
                ))}

              <FormField label="actions" help="submit approve send">
                <Textarea value={actions} onChange={(e) => setActions(e.target.value)} rows={2} className="tabular" />
              </FormField>
              <Button variant="outline" onClick={() => simulate.mutate(undefined as never)} loading={simulate.isPending} leftIcon={<Play className="size-4" aria-hidden />}>
                {t("common.preview")}
              </Button>
              {simulation && <pre className="max-h-64 overflow-auto rounded-card border border-line bg-subtle p-3 text-xs">{JSON.stringify(simulation, null, 2)}</pre>}
            </div>
          </Card>
        </div>
      </div>

      <ConfirmDialog
        open={activating}
        onOpenChange={setActivating}
        title={t("numbering.activate_confirm")}
        consequences={t("numbering.activate_consequences")}
        confirmLabel={t("numbering.activate")}
        cancelLabel={t("common.cancel")}
        loading={activate.isPending}
        onConfirm={() => activate.mutate(undefined as never)}
      />
    </div>
  );
}
