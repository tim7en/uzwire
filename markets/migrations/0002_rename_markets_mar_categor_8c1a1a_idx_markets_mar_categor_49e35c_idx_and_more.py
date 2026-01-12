"""No-op migration.

We originally introduced this migration to rename auto-generated index names.
After aligning index names in 0001, the rename is no longer needed.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("markets", "0001_initial"),
    ]

    operations = []
