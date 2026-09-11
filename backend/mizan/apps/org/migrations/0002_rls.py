from django.db import migrations

from mizan.platform.db.rls import enable_rls_for


class Migration(migrations.Migration):
    dependencies = [("org", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    # The tenant table is the isolation boundary itself and is not scoped.
    operations = enable_rls_for("branch", "department", "signatory", "treasury_account")
