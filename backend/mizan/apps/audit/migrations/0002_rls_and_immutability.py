from django.db import migrations

from mizan.platform.db.rls import enable_rls

IMMUTABLE_TRIGGER = """
CREATE OR REPLACE FUNCTION audit_event_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_event is append-only (SPEC §20.1)' USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER audit_event_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION audit_event_immutable();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS audit_event_no_update_delete ON audit_event;
DROP FUNCTION IF EXISTS audit_event_immutable();
"""


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    operations = [
        enable_rls("audit_event", global_when_null=True),
        migrations.RunSQL(sql=IMMUTABLE_TRIGGER, reverse_sql=DROP_TRIGGER),
    ]
