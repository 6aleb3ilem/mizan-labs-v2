from django.db import migrations

from mizan.platform.db.rls import enable_rls, enable_rls_for


class Migration(migrations.Migration):
    dependencies = [("documents", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    operations = [
        *enable_rls_for(
            "document_template", "print_profile", "signing_key", "issued_document", "rendition",
            "transparency_leaf", "transparency_head",
        ),
        # unknown-token attempts and anonymous fraud reports have no tenant
        enable_rls("verification_attempt", global_when_null=True),
        enable_rls("fraud_case", global_when_null=True),
    ]  # fmt: skip
