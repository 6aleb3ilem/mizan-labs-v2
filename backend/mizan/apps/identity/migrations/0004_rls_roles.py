from django.db import migrations

from mizan.platform.db.rls import enable_rls, enable_rls_for


class Migration(migrations.Migration):
    dependencies = [("identity", "0003_role_apikey_grant_membership_refreshtoken")]

    operations = [
        *enable_rls_for("role", "grant_", "membership", "api_key"),
        enable_rls("refresh_token", global_when_null=True),
    ]
