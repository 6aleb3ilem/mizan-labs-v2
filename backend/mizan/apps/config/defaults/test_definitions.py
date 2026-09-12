"""The four V1 tests as definitions (SPEC §14.6, Appendix J), with their specimen types, sieve
set and categories. Installed by the seed; editable afterwards like any configuration."""

from __future__ import annotations

from typing import Any

from django.utils import timezone

from mizan.apps.config.models import (
    ConfigStatus,
    ServiceCategory,
    SieveSet,
    SpecimenType,
    TestDefinition,
)
from mizan.platform.formula.engine import validate_definition_formulas

SPECIMEN_TYPES: tuple[dict[str, Any], ...] = (
    {"code": "CYL_16x32", "labels": {"fr": "Cylindre 16x32", "en": "Cylinder 16x32"}, "shape": "CYLINDER", "dims": {"d": 16, "h": 32}},
    {"code": "CYL_15x30", "labels": {"fr": "Cylindre 15x30", "en": "Cylinder 15x30"}, "shape": "CYLINDER", "dims": {"d": 15, "h": 30}},
    {"code": "CUBE_15", "labels": {"fr": "Cube 15", "en": "Cube 15"}, "shape": "CUBE", "dims": {"side": 15}},
    {"code": "HOLLOW", "labels": {"fr": "Parpaing creux", "en": "Hollow block"}, "shape": "BLOCK", "dims": {"L": 40, "W": 20, "H": 20}, "derived": {"net_factor": 0.55}},
    {"code": "SOLID", "labels": {"fr": "Parpaing plein", "en": "Solid block"}, "shape": "BLOCK", "dims": {"L": 40, "W": 20, "H": 20}, "derived": {"net_factor": 1}},
    {"code": "HOURDIS", "labels": {"fr": "Hourdis", "en": "Hourdis"}, "shape": "BLOCK", "dims": {"L": 50, "W": 20, "H": 16}, "derived": {"net_factor": 0.45}},
)  # fmt: skip

SIEVE_SETS: tuple[dict[str, Any], ...] = (
    {"code": "AGG_STANDARD", "labels": {"fr": "Série normalisée granulats", "en": "Standard aggregate series"}, "sizes_mm": [31.5, 20, 16, 12.5, 10, 8, 6.3, 4, 2, 1, 0.5, 0.25, 0.125, 0.08]},
)  # fmt: skip

CATEGORIES: tuple[dict[str, Any], ...] = (
    {"code": "TESTS", "labels": {"fr": "Essais laboratoire", "en": "Laboratory tests"}, "ord": 1},
    {"code": "TESTS.CONCRETE", "parent": "TESTS", "department": "CONCRETE", "labels": {"fr": "Béton", "en": "Concrete"}, "ord": 1},
    {"code": "TESTS.BLOCKS", "parent": "TESTS", "department": "CONCRETE", "labels": {"fr": "Parpaings", "en": "Blocks"}, "ord": 2},
    {"code": "TESTS.AGGREGATES", "parent": "TESTS", "department": "SOILS", "labels": {"fr": "Granulats", "en": "Aggregates"}, "ord": 3},
    {"code": "TESTS.SOILS", "parent": "TESTS", "department": "SOILS", "labels": {"fr": "Sols", "en": "Soils"}, "ord": 4},
    {"code": "FIELD", "labels": {"fr": "Prestations terrain", "en": "Field services"}, "ord": 2},
    {"code": "STUDIES", "labels": {"fr": "Études", "en": "Studies"}, "ord": 3},
)  # fmt: skip

_STAGES_SPECIMEN = [
    {"code": "RECEIVED", "labels": {"fr": "Reçu", "en": "Received"}},
    {
        "code": "CURING",
        "labels": {"fr": "En cure", "en": "Curing"},
        "location_vocab": "curing_location",
    },
    {"code": "TESTING", "labels": {"fr": "En essai", "en": "Testing"}},
    {"code": "REPORTED", "labels": {"fr": "Rapporté", "en": "Reported"}, "is_terminal": True},
]
_STAGES_SAMPLE = [
    {"code": "RECEIVED", "labels": {"fr": "Reçu", "en": "Received"}},
    {"code": "PREPARED", "labels": {"fr": "Préparé", "en": "Prepared"}},
    {"code": "TESTING", "labels": {"fr": "En essai", "en": "Testing"}},
    {"code": "REPORTED", "labels": {"fr": "Rapporté", "en": "Reported"}, "is_terminal": True},
]
_OUTLIER_RULES = [
    {
        "code": "SINGLE_OUTLIER", "effect": "EXCLUDE_AND_RECOMPUTE", "params": {"threshold": 5},
        "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) == 1",
        "target": "argmin(specimens.stress_mpa)",
        "labels": {"fr": "Une éprouvette écartée (écart ≥ {threshold} MPa)", "en": "One specimen excluded (deviation ≥ {threshold} MPa)"},
    },
    {
        "code": "MULTI_OUTLIER", "effect": "FLAG", "params": {"threshold": 5},
        "expression": "count(filter(specimens, {aggregates.mean_mpa - .stress_mpa >= params.threshold})) >= 2",
        "labels": {"fr": "Dispersion élevée : vérifier", "en": "High dispersion: check"},
    },
]  # fmt: skip

CONCRETE_COMPRESSION: dict[str, Any] = {
    "code": "CONCRETE_COMPRESSION",
    "labels": {"fr": "Écrasement d'éprouvettes béton", "en": "Concrete compressive strength"},
    "category": "TESTS.CONCRETE",
    "department": "CONCRETE",
    "method_ref": "NF EN 12390-3",
    "unit_under_test": "SPECIMEN",
    "specimen_type_codes": ["CYL_16x32", "CYL_15x30", "CUBE_15"],
    "scheduling": {"type": "AGE", "reference_field": "fabrication_date", "allowed_ages": [2, 3, 7, 14, 28, 56, 90]},
    "stages": _STAGES_SPECIMEN,
    "intake_fields": [
        {"key": "fabrication_date", "type": "date", "required": True, "labels": {"fr": "Date de fabrication", "en": "Fabrication date"}},
        {"key": "sampling_by", "type": "enum", "options": ["LAB", "CLIENT"], "required": True, "labels": {"fr": "Prélèvement", "en": "Sampled by"}},
        {"key": "structure_part", "type": "text", "labels": {"fr": "Partie d'ouvrage", "en": "Structure part"}},
        {"key": "site", "type": "text", "labels": {"fr": "Chantier", "en": "Site"}},
        {"key": "slump_cm", "type": "number", "unit": "cm", "min": 0, "max": 30, "labels": {"fr": "Affaissement", "en": "Slump"}},
        {"key": "placement", "type": "text", "labels": {"fr": "Mise en place", "en": "Placement"}},
        {"key": "mix_design", "type": "structured", "labels": {"fr": "Formulation", "en": "Mix design"}, "schema": {
            "gravel1": {"name": "text", "dosage": "number:kg/m3"}, "gravel2": {"name": "text", "dosage": "number:kg/m3"},
            "sand1": {"name": "text", "dosage": "number:kg/m3"}, "sand2": {"name": "text", "dosage": "number:kg/m3"},
            "cement": {"name": "text", "dosage": "number:kg/m3"}, "admixture": {"name": "text", "dosage": "number:l/m3"},
            "water": {"name": "text", "dosage": "number:l/m3"}}},
    ],
    "inputs": [
        {"key": "weight_kg", "type": "number", "unit": "kg", "level": "PER_SPECIMEN", "required": True, "min": 0, "max": 50, "step": 0.01, "labels": {"fr": "Masse", "en": "Weight"}},
        {"key": "load_kgf", "type": "number", "unit": "kgf", "level": "PER_SPECIMEN", "required": True, "min": 0, "max": 200000, "step": 1, "labels": {"fr": "Charge de rupture", "en": "Failure load"}},
    ],
    "computed": [
        {"key": "section_cm2", "unit": "cm2", "level": "PER_SPECIMEN", "precision": 2, "formula": "specimen.shape == 'CYLINDER' ? pi() * specimen.d ^ 2 / 4 : specimen.side ^ 2"},
        {"key": "stress_kgcm2", "unit": "kgf/cm2", "level": "PER_SPECIMEN", "precision": 0, "formula": "round(inputs.load_kgf / computed.section_cm2, 0)"},
        {"key": "stress_mpa", "unit": "MPa", "level": "PER_SPECIMEN", "precision": 1, "formula": "round(computed.stress_kgcm2 / 10, 1)"},
    ],
    "aggregates": [
        {"key": "mean_mpa", "unit": "MPa", "precision": 1, "formula": "round(avg(specimens.stress_mpa), 1)"},
        {"key": "n_tested", "formula": "count(specimens.stress_mpa)"},
    ],
    "rules": _OUTLIER_RULES,
    "required_equipment_class_code": "COMPRESSION_PRESS",
    "report_template_code": "PV_CONCRETE",
    "report_columns": ["ref", "specimen_type", "age", "weight_kg", "load_kgf", "stress_kgcm2", "stress_mpa", "mean_mpa"],
    "unit_of_sale": "PER_SPECIMEN",
}  # fmt: skip

BLOCK_COMPRESSION: dict[str, Any] = {
    "code": "BLOCK_COMPRESSION",
    "labels": {"fr": "Écrasement de parpaings", "en": "Block compressive strength"},
    "category": "TESTS.BLOCKS",
    "department": "CONCRETE",
    "method_ref": "NF EN 772-1",
    "unit_under_test": "SPECIMEN",
    "specimen_type_codes": ["HOLLOW", "SOLID", "HOURDIS"],
    "scheduling": {"type": "TURNAROUND", "days": 3},
    "stages": _STAGES_SPECIMEN,
    "intake_fields": [
        {"key": "manufacturer", "type": "text", "labels": {"fr": "Fabricant", "en": "Manufacturer"}},
        {"key": "block_type", "type": "vocab", "vocab": "block_type", "required": True, "labels": {"fr": "Type", "en": "Type"}},
        {"key": "site", "type": "text", "labels": {"fr": "Chantier", "en": "Site"}},
    ],
    "inputs": [
        {"key": "weight_kg", "type": "number", "unit": "kg", "level": "PER_SPECIMEN", "required": True, "min": 0, "max": 60, "step": 0.01, "labels": {"fr": "Masse", "en": "Weight"}},
        {"key": "load_kgf", "type": "number", "unit": "kgf", "level": "PER_SPECIMEN", "required": True, "min": 0, "max": 200000, "step": 1, "labels": {"fr": "Charge de rupture", "en": "Failure load"}},
        {"key": "gross_area_cm2", "type": "number", "unit": "cm2", "level": "PER_SPECIMEN", "required": True, "min": 1, "max": 5000, "step": 0.1, "default_formula": "specimen.L * specimen.W", "labels": {"fr": "Section brute", "en": "Gross area"}},
        {"key": "net_area_cm2", "type": "number", "unit": "cm2", "level": "PER_SPECIMEN", "required": True, "min": 1, "max": 5000, "step": 0.1, "default_formula": "specimen.net_factor * specimen.L * specimen.W", "labels": {"fr": "Section nette", "en": "Net area"}},
    ],
    "computed": [
        {"key": "gross_kgcm2", "unit": "kgf/cm2", "level": "PER_SPECIMEN", "precision": 1, "formula": "round(inputs.load_kgf / inputs.gross_area_cm2, 1)"},
        {"key": "net_kgcm2", "unit": "kgf/cm2", "level": "PER_SPECIMEN", "precision": 1, "formula": "round(inputs.load_kgf / inputs.net_area_cm2, 1)"},
        {"key": "stress_mpa", "unit": "MPa", "level": "PER_SPECIMEN", "precision": 1, "formula": "round(computed.net_kgcm2 / 10, 1)"},
    ],
    "aggregates": [
        {"key": "mean_mpa", "unit": "MPa", "precision": 1, "formula": "round(avg(specimens.stress_mpa), 1)"},
        {"key": "n_tested", "formula": "count(specimens.stress_mpa)"},
    ],
    "rules": _OUTLIER_RULES,
    "required_equipment_class_code": "COMPRESSION_PRESS",
    "report_template_code": "GENERIC_REPORT",
    "report_columns": ["ref", "specimen_type", "weight_kg", "load_kgf", "gross_kgcm2", "net_kgcm2", "stress_mpa", "mean_mpa"],
    "unit_of_sale": "PER_SPECIMEN",
}  # fmt: skip

SIEVE_ANALYSIS: dict[str, Any] = {
    "code": "SIEVE_ANALYSIS",
    "labels": {"fr": "Analyse granulométrique par tamisage", "en": "Sieve analysis"},
    "category": "TESTS.AGGREGATES",
    "department": "SOILS",
    "method_ref": "NF EN 933-1",
    "unit_under_test": "SAMPLE",
    "specimen_type_codes": [],
    "scheduling": {"type": "TURNAROUND", "days": 2},
    "stages": _STAGES_SAMPLE,
    "intake_fields": [
        {"key": "material", "type": "vocab", "vocab": "sample_nature", "required": True, "labels": {"fr": "Matériau", "en": "Material"}},
        {"key": "origin", "type": "text", "labels": {"fr": "Provenance", "en": "Origin"}},
    ],
    "inputs": [
        {"key": "total_mass_g", "type": "number", "unit": "g", "level": "PER_RUN", "required": True, "min": 1, "max": 100000, "step": 0.1, "labels": {"fr": "Masse totale sèche", "en": "Total dry mass"}},
        {"key": "sieve_set", "type": "sieve_set", "level": "PER_RUN", "required": True, "default": "AGG_STANDARD", "labels": {"fr": "Série de tamis", "en": "Sieve set"}},
        {"key": "sieve_mm", "type": "number", "unit": "mm", "level": "PER_SERIES", "required": True, "labels": {"fr": "Tamis", "en": "Sieve"}},
        {"key": "cum_retained_g", "type": "number", "unit": "g", "level": "PER_SERIES", "required": True, "min": 0, "step": 0.1, "labels": {"fr": "Refus cumulé", "en": "Cumulative retained"}},
    ],
    "computed": [
        {"key": "pct_retained", "unit": "%", "level": "PER_SERIES", "precision": 1, "formula": "inputs.cum_retained_g / run.total_mass_g * 100"},
        {"key": "pct_passing", "unit": "%", "level": "PER_SERIES", "precision": 1, "formula": "100 - computed.pct_retained"},
    ],
    "aggregates": [{"key": "sieves", "formula": "count(series.cum_retained_g)"}],
    "rules": [
        {"code": "SERIES_MONOTONIC", "effect": "BLOCK", "expression": "not is_monotonic_nondecreasing(series.cum_retained_g)", "labels": {"fr": "Les refus cumulés doivent être croissants", "en": "Cumulative retained masses must be non-decreasing"}},
        {"code": "SERIES_MASS", "effect": "BLOCK", "expression": "max(series.cum_retained_g) > run.total_mass_g", "labels": {"fr": "Refus cumulé supérieur à la masse totale", "en": "Cumulative retained above the total mass"}},
    ],
    "required_equipment_class_code": "SIEVE_SHAKER",
    "report_template_code": "GENERIC_REPORT",
    "report_columns": ["sieve_mm", "cum_retained_g", "pct_retained", "pct_passing"],
    "unit_of_sale": "PER_SAMPLE",
}  # fmt: skip

WATER_CONTENT: dict[str, Any] = {
    "code": "WATER_CONTENT",
    "labels": {"fr": "Teneur en eau", "en": "Water content"},
    "category": "TESTS.SOILS",
    "department": "SOILS",
    "method_ref": "NF EN ISO 17892-1",
    "unit_under_test": "SAMPLE",
    "specimen_type_codes": [],
    "scheduling": {"type": "TURNAROUND", "days": 1},
    "stages": _STAGES_SAMPLE,
    "intake_fields": [
        {"key": "material", "type": "vocab", "vocab": "sample_nature", "required": True, "labels": {"fr": "Matériau", "en": "Material"}},
        {"key": "depth_m", "type": "number", "unit": "m", "labels": {"fr": "Profondeur", "en": "Depth"}},
    ],
    "inputs": [
        {"key": "wet_plus_tare", "type": "number", "unit": "g", "level": "PER_PORTION", "required": True, "min": 0, "step": 0.01, "labels": {"fr": "Humide + tare", "en": "Wet + tare"}},
        {"key": "dry_plus_tare", "type": "number", "unit": "g", "level": "PER_PORTION", "required": True, "min": 0, "step": 0.01, "labels": {"fr": "Sec + tare", "en": "Dry + tare"}},
        {"key": "tare", "type": "number", "unit": "g", "level": "PER_PORTION", "required": True, "min": 0, "step": 0.01, "labels": {"fr": "Tare", "en": "Tare"}},
    ],
    "computed": [
        {"key": "water", "unit": "g", "level": "PER_PORTION", "precision": 2, "formula": "inputs.wet_plus_tare - inputs.dry_plus_tare"},
        {"key": "dry_net", "unit": "g", "level": "PER_PORTION", "precision": 2, "formula": "inputs.dry_plus_tare - inputs.tare"},
        {"key": "w_pct", "unit": "%", "level": "PER_PORTION", "precision": 1, "formula": "computed.water / computed.dry_net * 100"},
    ],
    "aggregates": [{"key": "mean_w", "unit": "%", "precision": 1, "formula": "round(avg(portions.w_pct), 1)"}],
    "rules": [
        {"code": "DRY_NET_POSITIVE", "effect": "BLOCK", "expression": "min(portions.dry_net) <= 0", "labels": {"fr": "Masse sèche nette nulle ou négative", "en": "Net dry mass is zero or negative"}},
    ],
    "required_equipment_class_code": "OVEN",
    "report_template_code": "GENERIC_REPORT",
    "report_columns": ["ref", "wet_plus_tare", "dry_plus_tare", "tare", "water", "dry_net", "w_pct", "mean_w"],
    "unit_of_sale": "PER_SAMPLE",
}  # fmt: skip

DEFAULT_TEST_DEFINITIONS: tuple[dict[str, Any], ...] = (
    CONCRETE_COMPRESSION,
    BLOCK_COMPRESSION,
    SIEVE_ANALYSIS,
    WATER_CONTENT,
)


def install_default_categories(
    departments: dict[str, Any] | None = None,
) -> dict[str, ServiceCategory]:
    departments = departments or {}
    created: dict[str, ServiceCategory] = {}
    for spec in CATEGORIES:
        parent = created.get(spec.get("parent", ""))
        category, _ = ServiceCategory.objects.get_or_create(
            code=spec["code"],
            defaults={
                "parent": parent,
                "department": departments.get(spec.get("department", "")),
                "ord": spec.get("ord", 0),
            },
        )
        category.set_labels(spec["labels"])
        created[spec["code"]] = category
    return created


def install_default_specimen_types() -> list[SpecimenType]:
    rows: list[SpecimenType] = []
    for spec in SPECIMEN_TYPES:
        row, _ = SpecimenType.objects.get_or_create(
            code=spec["code"],
            defaults={
                "shape": spec["shape"],
                "dims": spec["dims"],
                "derived": spec.get("derived", {}),
            },
        )
        row.set_labels(spec["labels"])
        rows.append(row)
    for spec in SIEVE_SETS:
        sieve, _ = SieveSet.objects.get_or_create(
            code=spec["code"], defaults={"sizes_mm": spec["sizes_mm"]}
        )
        sieve.set_labels(spec["labels"])
    return rows


def install_default_test_definitions(
    departments: dict[str, Any] | None = None, *, activate: bool = True
) -> list[TestDefinition]:
    """Create the four definitions (version 1). Formulas are validated before activation."""
    departments = departments or {}
    categories = install_default_categories(departments)
    install_default_specimen_types()
    rows: list[TestDefinition] = []
    for spec in DEFAULT_TEST_DEFINITIONS:
        problems = validate_definition_formulas(spec)
        if problems:
            raise ValueError(f"{spec['code']}: invalid formulas {problems}")
        definition, was_created = TestDefinition.objects.get_or_create(
            code=spec["code"],
            version=1,
            defaults={
                "status": ConfigStatus.ACTIVE if activate else ConfigStatus.DRAFT,
                "category": categories.get(spec["category"]),
                "department": departments.get(spec["department"]),
                "method_ref": spec["method_ref"],
                "unit_under_test": spec["unit_under_test"],
                "specimen_type_codes": spec["specimen_type_codes"],
                "scheduling": spec["scheduling"],
                "stages": spec["stages"],
                "intake_fields": spec["intake_fields"],
                "inputs": spec["inputs"],
                "computed": spec["computed"],
                "aggregates": spec["aggregates"],
                "rules": spec["rules"],
                "required_equipment_class_code": spec["required_equipment_class_code"],
                "report_template_code": spec["report_template_code"],
                "report_columns": spec["report_columns"],
                "unit_of_sale": spec["unit_of_sale"],
                "activated_at": timezone.now() if activate else None,
            },
        )
        if was_created:
            definition.set_labels(spec["labels"])
        rows.append(definition)
    return rows
