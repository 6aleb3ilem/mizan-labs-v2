from django.db import migrations

from mizan.platform.db.rls import enable_rls

EXTENSIONS = ("unaccent", "pg_trgm", "citext")


class Migration(migrations.Migration):
    dependencies = [("platform", "0001_initial")]

    operations = [
        *[
            migrations.RunSQL(
                sql=f"CREATE EXTENSION IF NOT EXISTS {ext};",
                reverse_sql=migrations.RunSQL.noop,
            )
            for ext in EXTENSIONS
        ],
        enable_rls("i18n_text"),
        enable_rls("idempotency_key"),
    ]
