"""Evaluation of a test definition over one run (SPEC §14.4, Appendix K.4).

Order: computed keys in declaration order per subject → aggregates → rules in order.
``EXCLUDE_AND_RECOMPUTE`` excludes the rule's target subject and recomputes the aggregates
once (up to three passes when ``params.iterative`` is true). Missing inputs and division by
zero become BLOCK problems with a message key; nothing raises out of ``evaluate_definition``
except programming errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from mizan.platform.formula.errors import FormulaError
from mizan.platform.formula.evaluator import compile_formula
from mizan.platform.formula.functions import round_half_up

Json = dict[str, Any]

LEVEL_SPECIMEN = "PER_SPECIMEN"
LEVEL_PORTION = "PER_PORTION"
LEVEL_SERIES = "PER_SERIES"
LEVEL_RUN = "PER_RUN"
MAX_ITERATIVE_PASSES = 3


@dataclass(slots=True)
class Subject:
    """A specimen (or a portion / series row): inputs plus computed values."""

    id: str
    inputs: Json
    properties: Json = field(default_factory=dict)  # specimen type geometry, e.g. d, side, shape
    computed: Json = field(default_factory=dict)
    excluded: bool = False
    exclusion_reason: str | None = None
    status: str = "OK"  # OK | MISSING | DAMAGED

    def merged(self) -> Json:
        return {**self.inputs, **self.computed, "id": self.id}


@dataclass(slots=True)
class RunData:
    subjects: list[Subject] = field(default_factory=list)
    run: Json = field(default_factory=dict)  # PER_RUN inputs
    intake: Json = field(default_factory=dict)
    series: list[Subject] = field(default_factory=list)
    portions: list[Subject] = field(default_factory=list)
    const: Json = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Problem:
    message_key: str
    params: Json
    where: str  # "computed:stress_mpa[3]" or "aggregate:mean_mpa" or "rule:SINGLE_OUTLIER"


@dataclass(frozen=True, slots=True)
class RuleHit:
    code: str
    effect: str
    labels: Json
    params: Json
    target_subject_id: str | None = None


@dataclass(slots=True)
class EvaluationResult:
    subjects: list[Subject]
    aggregates: Json
    flags: list[RuleHit] = field(default_factory=list)
    blocks: list[RuleHit] = field(default_factory=list)
    exclusions: list[RuleHit] = field(default_factory=list)
    problems: list[Problem] = field(default_factory=list)
    run_computed: Json = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return bool(self.blocks or self.problems)


def _round(value: Any, precision: int | None) -> Any:
    if precision is None or isinstance(value, bool) or not isinstance(value, int | float | Decimal):
        return value
    return round_half_up(value, precision)


def _active(subjects: list[Subject]) -> list[Subject]:
    return [s for s in subjects if not s.excluded and s.status == "OK"]


class DefinitionEvaluator:
    def __init__(self, definition: Json, data: RunData) -> None:
        self.definition = definition
        self.data = data
        self.problems: list[Problem] = []

    # --- environments ----------------------------------------------------------------------

    def _base_env(self) -> Json:
        return {
            "run": self.data.run,
            "intake": self.data.intake,
            "series": [s.merged() for s in self.data.series],
            "portions": [p.merged() for p in self.data.portions],
            "const": self.data.const,
            "params": {},
        }

    def _subject_env(self, subject: Subject) -> Json:
        env = self._base_env()
        env.update(
            {"inputs": subject.inputs, "computed": subject.computed, "specimen": subject.properties}
        )
        return env

    def _aggregate_env(self, aggregates: Json, params: Json | None = None) -> Json:
        env = self._base_env()
        env.update(
            {
                "specimens": [s.merged() for s in _active(self.data.subjects)],
                "aggregates": aggregates,
                "inputs": self.data.run,
                "computed": self.run_computed,
                "params": params or {},
            }
        )
        return env

    # --- steps -----------------------------------------------------------------------------

    def _evaluate(self, formula: str, env: Json, where: str, precision: int | None = None) -> Any:
        try:
            return _round(compile_formula(formula).evaluate(env), precision)
        except FormulaError as exc:
            self.problems.append(
                Problem(exc.message_key, {**exc.params, "detail": str(exc)}, where)
            )
            return None

    def compute_level(self, level: str) -> None:
        specs = [
            c
            for c in self.definition.get("computed", [])
            if c.get("level", LEVEL_SPECIMEN) == level
        ]
        if not specs:
            return
        if level == LEVEL_RUN:
            env = self._base_env()
            env.update({"inputs": self.data.run, "computed": self.run_computed, "specimen": {}})
            for spec in specs:
                value = self._evaluate(
                    spec["formula"], env, f"computed:{spec['key']}", spec.get("precision")
                )
                if value is not None:
                    self.run_computed[spec["key"]] = value
            return
        collection = {
            LEVEL_SPECIMEN: self.data.subjects,
            LEVEL_PORTION: self.data.portions,
            LEVEL_SERIES: self.data.series,
        }[level]
        for subject in collection:
            if subject.status != "OK":
                continue
            env = self._subject_env(subject)
            for spec in specs:
                value = self._evaluate(
                    spec["formula"],
                    env,
                    f"computed:{spec['key']}[{subject.id}]",
                    spec.get("precision"),
                )
                if value is not None:
                    subject.computed[spec["key"]] = value

    def compute_aggregates(self) -> Json:
        aggregates: Json = {}
        for spec in self.definition.get("aggregates", []):
            value = self._evaluate(
                spec["formula"],
                self._aggregate_env(aggregates),
                f"aggregate:{spec['key']}",
                spec.get("precision"),
            )
            if value is not None:
                aggregates[spec["key"]] = value
        return aggregates

    def apply_rules(
        self, aggregates: Json
    ) -> tuple[Json, list[RuleHit], list[RuleHit], list[RuleHit]]:
        flags: list[RuleHit] = []
        blocks: list[RuleHit] = []
        exclusions: list[RuleHit] = []
        for rule in self.definition.get("rules", []):
            params = dict(rule.get("params") or {})
            passes = MAX_ITERATIVE_PASSES if params.get("iterative") else 1
            for _ in range(passes):
                env = self._aggregate_env(aggregates, params)
                fired = self._evaluate(rule["expression"], env, f"rule:{rule['code']}")
                if not fired:
                    break
                effect = rule.get("effect", "FLAG")
                hit = RuleHit(rule["code"], effect, rule.get("labels") or {}, params)
                if effect == "FLAG":
                    flags.append(hit)
                    break
                if effect == "BLOCK":
                    blocks.append(hit)
                    break
                if effect == "EXCLUDE_AND_RECOMPUTE":
                    target = self._evaluate(
                        rule.get("target", ""), env, f"rule:{rule['code']}:target"
                    )
                    active = _active(self.data.subjects)
                    if (
                        target is None
                        or not isinstance(target, int | float)
                        or not 0 <= int(target) < len(active)
                    ):
                        blocks.append(hit)
                        break
                    victim = active[int(target)]
                    victim.excluded = True
                    victim.exclusion_reason = rule["code"]
                    exclusions.append(
                        RuleHit(rule["code"], effect, rule.get("labels") or {}, params, victim.id)
                    )
                    aggregates = self.compute_aggregates()
                    continue
                blocks.append(hit)
                break
        return aggregates, flags, blocks, exclusions

    def run(self) -> EvaluationResult:
        self.run_computed: Json = {}
        for level in (LEVEL_RUN, LEVEL_PORTION, LEVEL_SERIES, LEVEL_SPECIMEN):
            self.compute_level(level)
        aggregates = self.compute_aggregates()
        aggregates, flags, blocks, exclusions = self.apply_rules(aggregates)
        return EvaluationResult(
            subjects=self.data.subjects,
            aggregates=aggregates,
            flags=flags,
            blocks=blocks,
            exclusions=exclusions,
            problems=self.problems,
            run_computed=self.run_computed,
        )


def evaluate_definition(definition: Json, data: RunData) -> EvaluationResult:
    return DefinitionEvaluator(definition, data).run()


def validate_definition_formulas(definition: Json) -> list[Problem]:
    """Compile every formula of a definition (sandbox check before activation)."""
    problems: list[Problem] = []
    for section in ("computed", "aggregates"):
        for spec in definition.get(section, []):
            try:
                compile_formula(spec["formula"])
            except FormulaError as exc:
                problems.append(
                    Problem(exc.message_key, exc.params, f"{section}:{spec.get('key')}")
                )
    for rule in definition.get("rules", []):
        for key in ("expression", "target"):
            text = rule.get(key)
            if text:
                try:
                    compile_formula(text)
                except FormulaError as exc:
                    problems.append(
                        Problem(exc.message_key, exc.params, f"rule:{rule.get('code')}:{key}")
                    )
    return problems
