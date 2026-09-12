from django.db import migrations

from mizan.platform.db.rls import enable_rls_for


class Migration(migrations.Migration):
    dependencies = [("notify", "0001_initial"), ("platform", "0002_extensions_and_rls")]

    operations = enable_rls_for(
        "notification_rule",
        "message_template",
        "contact_channel_preference",
        "notification_delivery",
        "notification",
    )
