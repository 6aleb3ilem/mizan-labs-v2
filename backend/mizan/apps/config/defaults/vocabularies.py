"""Default vocabularies of a new tenant (SPEC Appendix E)."""

from __future__ import annotations

from mizan.apps.config.models import VocabularyEntry

# kind → (code, fr, en, extra)
DEFAULT_VOCABULARIES: dict[str, tuple[tuple[str, str, str], ...]] = {
    "participant_role": (("MO", "Maître d'ouvrage", "Project owner"), ("MOE", "Maître d'œuvre", "Engineering firm"), ("BCT", "Bureau de contrôle", "Technical control bureau"), ("CONTRACTOR", "Entreprise", "Contractor"), ("SUBCONTRACTOR", "Sous-traitant", "Subcontractor")),
    "contact_function": (("DIRECTOR", "Directeur", "Director"), ("SITE_MANAGER", "Conducteur de travaux", "Site manager"), ("ENGINEER", "Ingénieur", "Engineer"), ("ACCOUNTANT", "Comptable", "Accountant"), ("PURCHASER", "Acheteur", "Purchaser")),
    "priority": (("LOW", "Basse", "Low"), ("NORMAL", "Normale", "Normal"), ("HIGH", "Haute", "High"), ("URGENT", "Urgente", "Urgent")),
    "sample_nature": (("SOIL", "Sol", "Soil"), ("AGGREGATE", "Granulat", "Aggregate"), ("SAND", "Sable", "Sand"), ("BITUMEN", "Bitume", "Bitumen"), ("ASPHALT_MIX", "Enrobé", "Asphalt mix"), ("STEEL", "Acier", "Steel"), ("CEMENT", "Ciment", "Cement"), ("CONCRETE", "Béton", "Concrete"), ("BLOCK", "Parpaing", "Block")),
    "curing_location": (("CONCRETE_TANK", "Bac béton", "Concrete tank"), ("CBR_TANK", "Bac CBR", "CBR tank"), ("SHELF_A", "Étagère A", "Shelf A")),
    "payment_method": (("CASH", "Espèces", "Cash"), ("TRANSFER", "Virement", "Bank transfer"), ("CHEQUE", "Chèque", "Cheque"), ("MOBILE_MONEY", "Mobile money", "Mobile money")),
    "reason": (("CLIENT_REQUEST", "Demande du client", "Client request"), ("ERROR", "Erreur", "Error"), ("DUPLICATE", "Doublon", "Duplicate"), ("OTHER", "Autre", "Other")),
    "block_type": (("HOLLOW", "Creux", "Hollow"), ("SOLID", "Plein", "Solid"), ("HOURDIS", "Hourdis", "Hourdis")),
    "specimen_shape": (("CYLINDER", "Cylindre", "Cylinder"), ("CUBE", "Cube", "Cube"), ("PRISM", "Prisme", "Prism")),
    "quote_condition": (("VALIDITY_30", "Validité 30 jours", "Validity 30 days"), ("PRICES_EXCL_VAT", "Prix hors taxes", "Prices excl. VAT"), ("PAYMENT_TERMS", "Conditions de paiement", "Payment terms"), ("SAMPLES_BY_CLIENT", "Échantillons fournis par le client", "Samples supplied by client"), ("REPORTS_AFTER_PAYMENT", "Rapports remis après paiement", "Reports issued after payment")),
    "task_category": (("LAB", "Essais laboratoire", "Laboratory tests"), ("FIELD", "Prestations terrain", "Field services"), ("STUDY", "Études", "Studies"), ("ASSETS", "Matériel", "Assets")),
    "client_tier": (("STANDARD", "Standard", "Standard"), ("KEY_ACCOUNT", "Grand compte", "Key account")),
    "unit": (("UNIT", "Unité", "Unit"), ("SPECIMEN", "Éprouvette", "Specimen"), ("SAMPLE", "Échantillon", "Sample"), ("VISIT", "Visite", "Visit"), ("DAY", "Jour", "Day"), ("MONTH", "Mois", "Month")),
    "equipment_condition": (("GOOD", "Bon", "Good"), ("WORN", "Usé", "Worn"), ("DAMAGED", "Endommagé", "Damaged")),
    "material_family": (("GRAVEL", "Gravier", "Gravel"), ("SAND", "Sable", "Sand"), ("CEMENT", "Ciment", "Cement"), ("ADMIXTURE", "Adjuvant", "Admixture"), ("WATER", "Eau", "Water")),
    "vehicle_document_type": (("FUEL_SLIP", "Bon de carburant", "Fuel slip"), ("FINE", "Amende", "Fine"), ("PURCHASE_ORDER", "Bon de commande", "Purchase order"), ("MAINTENANCE_ORDER", "Ordre d'entretien", "Maintenance order")),
}  # fmt: skip


def install_default_vocabularies() -> int:
    created = 0
    for kind, entries in DEFAULT_VOCABULARIES.items():
        for ord_, (code, fr, en) in enumerate(entries):
            entry, was_created = VocabularyEntry.objects.get_or_create(
                branch=None, kind=kind, code=code, defaults={"ord": ord_}
            )
            entry.set_labels({"fr": fr, "en": en})
            created += int(was_created)
    return created
