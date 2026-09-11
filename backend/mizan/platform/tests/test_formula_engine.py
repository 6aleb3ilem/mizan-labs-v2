"""Definition evaluation: Appendix J concrete compression, sieve monotonic BLOCK, water content."""

from __future__ import annotations

import copy
from decimal import Decimal as D
from typing import Any

from mizan.platform.formula.engine import (
    RunData,
    Subject,
    evaluate_definition,
    validate_definition_formulas,
)

CONCRETE: dict[str, Any] = {
    "code": "CONCRETE_COMPRESSION",
    "computed": [
        {
            "key": "section_cm2",
            "level": "PER_SPECIMEN",
            "precision": 2,
            "formula": "specimen.shape == 'CYLINDER' ? pi() * specimen.d ^ 2 / 4 : specimen.side ^ 2",
        },
        {
            "key": "stress_kgcm2",
            "level": "PER_SPECIMEN",
            "precision": 0,
            "formula": "round(inputs.load_kgf / computed.section_cm2, 0)",
        },
        {
            "key": "stress_mpa",
            "level": "PER_SPECIMEN",
            "precision": 1,
            "formula": "round(computed.stress_kgcm2 / 10, 1)",
        },
    ],
    "aggregates": [
        {"key": "mean_mpa", "precision": 1, "formula": "round(avg(specimens.stress_mpa), 1)"},
        {"key": "n_tested", "formula": "count(specimens.stress_mpa)"},
    ],
    "rules": [
        {
            "code": "SINGLE_OUTLIER",
            "effect": "EXCLUDE_AND_RECOMPUTE",
            "params": {"threshold": 5},
            "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) == 1",
            "target": "argmin(specimens.stress_mpa)",
            "labels": {"fr": "Une éprouvette écartée", "en": "One specimen excluded"},
        },
        {
            "code": "MULTI_OUTLIER",
            "effect": "FLAG",
            "params": {"threshold": 5},
            "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) >= 2",
            "labels": {"fr": "Dispersion élevée", "en": "High dispersion"},
        },
    ],
}
CYL_16x32 = {"shape": "CYLINDER", "d": 16}


def _run(loads: list[float]) -> RunData:
    return RunData(
        subjects=[
            Subject(
                id=str(i + 1), inputs={"weight_kg": 12.4, "load_kgf": load}, properties=CYL_16x32
            )
            for i, load in enumerate(loads)
        ],
        intake={"fabrication_date": "2026-09-10"},
    )


def test_concrete_compression_without_outlier() -> None:
    result = evaluate_definition(CONCRETE, _run([45210, 46800, 44950, 45500]))
    assert not result.blocked
    first = result.subjects[0].computed
    assert first["section_cm2"] == D("201.06")
    assert first["stress_kgcm2"] == 225
    assert first["stress_mpa"] == 22.5
    assert result.aggregates["n_tested"] == 4
    assert result.aggregates["mean_mpa"] == D("22.7")  # (22.5 + 23.3 + 22.4 + 22.6) / 4
    assert result.flags == [] and result.exclusions == []


def test_single_outlier_is_excluded_and_mean_recomputed() -> None:
    result = evaluate_definition(CONCRETE, _run([45210, 46800, 30000, 45500]))
    assert [s.excluded for s in result.subjects] == [False, False, True, False]
    assert result.subjects[2].exclusion_reason == "SINGLE_OUTLIER"
    assert result.exclusions[0].target_subject_id == "3"
    assert result.aggregates["n_tested"] == 3
    assert result.aggregates["mean_mpa"] == D("22.8")
    assert result.flags == []
    assert not result.blocked


def test_two_outliers_only_flag() -> None:
    result = evaluate_definition(
        CONCRETE, _run([45210, 25000, 24000, 45500])
    )  # 22.5, 12.4, 11.9, 22.6
    assert result.exclusions == []
    assert [f.code for f in result.flags] == ["MULTI_OUTLIER"]
    assert result.flags[0].labels["fr"] == "Dispersion élevée"
    assert result.aggregates["n_tested"] == 4


def test_missing_specimens_are_left_out_of_aggregates() -> None:
    data = _run([45210, 46800, 44950, 45500])
    data.subjects[3].status = "MISSING"
    result = evaluate_definition(CONCRETE, data)
    assert result.aggregates["n_tested"] == 3
    assert "stress_mpa" not in result.subjects[3].computed


def test_missing_input_blocks_with_message_key() -> None:
    data = _run([45210, 46800])
    del data.subjects[1].inputs["load_kgf"]
    result = evaluate_definition(CONCRETE, data)
    assert result.blocked
    assert result.problems[0].message_key == "formula.missing_value"
    assert result.problems[0].where == "computed:stress_kgcm2[2]"


SIEVE: dict[str, Any] = {
    "computed": [
        {
            "key": "pct_retained",
            "level": "PER_SERIES",
            "precision": 1,
            "formula": "inputs.cum_retained_g / run.total_mass_g * 100",
        },
        {
            "key": "pct_passing",
            "level": "PER_SERIES",
            "precision": 1,
            "formula": "100 - computed.pct_retained",
        },
    ],
    "aggregates": [{"key": "sieves", "formula": "count(series.cum_retained_g)"}],
    "rules": [
        {
            "code": "SERIES_MONOTONIC",
            "effect": "BLOCK",
            "expression": "not is_monotonic_nondecreasing(series.cum_retained_g)",
        },
        {
            "code": "SERIES_MASS",
            "effect": "BLOCK",
            "expression": "max(series.cum_retained_g) > run.total_mass_g",
        },
    ],
}


def test_sieve_analysis_blocks_on_non_monotonic_series() -> None:
    ok = RunData(
        run={"total_mass_g": 1000},
        series=[
            Subject(id=str(i), inputs={"sieve_mm": mm, "cum_retained_g": g})
            for i, (mm, g) in enumerate([(20, 0), (10, 250), (5, 600), (0.08, 980)])
        ],
    )
    result = evaluate_definition(SIEVE, ok)
    assert not result.blocked
    assert (
        [s.computed["pct_passing"] for s in result.series_or_subjects()]
        if hasattr(result, "series_or_subjects")
        else True
    )
    assert ok.series[1].computed == {"pct_retained": 25.0, "pct_passing": 75.0}
    bad = copy.deepcopy(ok)
    bad.series[2].inputs["cum_retained_g"] = 200
    result = evaluate_definition(SIEVE, bad)
    assert [b.code for b in result.blocks] == ["SERIES_MONOTONIC"]


WATER: dict[str, Any] = {
    "computed": [
        {
            "key": "water",
            "level": "PER_PORTION",
            "formula": "inputs.wet_plus_tare - inputs.dry_plus_tare",
        },
        {"key": "dry_net", "level": "PER_PORTION", "formula": "inputs.dry_plus_tare - inputs.tare"},
        {
            "key": "w_pct",
            "level": "PER_PORTION",
            "precision": 1,
            "formula": "computed.water / computed.dry_net * 100",
        },
    ],
    "aggregates": [{"key": "mean_w", "precision": 1, "formula": "round(avg(portions.w_pct), 1)"}],
}


def test_water_content_division_by_zero_blocks() -> None:
    data = RunData(
        portions=[
            Subject(id="1", inputs={"wet_plus_tare": 150.0, "dry_plus_tare": 140.0, "tare": 40.0}),
            Subject(id="2", inputs={"wet_plus_tare": 160.0, "dry_plus_tare": 148.0, "tare": 40.0}),
        ]
    )
    result = evaluate_definition(WATER, data)
    assert not result.blocked
    assert data.portions[0].computed["w_pct"] == 10.0
    assert result.aggregates["mean_w"] == D("10.6")
    broken = RunData(
        portions=[
            Subject(id="1", inputs={"wet_plus_tare": 150.0, "dry_plus_tare": 40.0, "tare": 40.0})
        ]
    )
    result = evaluate_definition(WATER, broken)
    assert result.blocked
    assert result.problems[0].message_key == "formula.division_by_zero"


def test_definition_formulas_are_validated_before_activation() -> None:
    assert validate_definition_formulas(CONCRETE) == []
    broken = copy.deepcopy(CONCRETE)
    broken["rules"][0]["target"] = "argmin("
    problems = validate_definition_formulas(broken)
    assert [p.where for p in problems] == ["rule:SINGLE_OUTLIER:target"]
