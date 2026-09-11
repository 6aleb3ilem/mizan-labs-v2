from django.db import migrations

from mizan.platform.db.rls import enable_rls


class Migration(migrations.Migration):
    dependencies = [("identity", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    # Platform operators have no tenant: rows with a NULL tenant are global.
    operations = [enable_rls("app_user", global_when_null=True)]
