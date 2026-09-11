from django.db import migrations

from mizan.platform.db.rls import enable_rls_for


class Migration(migrations.Migration):
    dependencies = [("config", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    operations = enable_rls_for(
        "numbering_scheme",
        "numbering_counter",
        "number_reservation",
        "vocabulary_entry",
        "workflow",
        "workflow_state",
        "workflow_transition",
        "payment_terms_template",
        "service_category",
        "service",
        "specimen_type",
        "sieve_set",
        "test_definition",
        "price_list",
        "price",
        "tax_rule",
    )
