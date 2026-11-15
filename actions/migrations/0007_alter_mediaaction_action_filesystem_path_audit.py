# Generated manually for fs_imported / fs_original_gone / fs_pruned / path_migrated audit actions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("actions", "0006_alter_mediaaction_action_metadata_integrity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mediaaction",
            name="action",
            field=models.CharField(
                choices=[
                    ("like", "Like"),
                    ("dislike", "Dislike"),
                    ("watch", "Watch"),
                    ("report", "Report"),
                    ("rate", "Rate"),
                    ("report_cleared", "Report cleared"),
                    ("report_confirmed", "Report confirmed"),
                    ("media_reviewed", "Media reviewed"),
                    ("media_unreviewed", "Media unreviewed"),
                    ("original_deleted", "Original deleted"),
                    ("metadata_refresh", "Metadata refreshed"),
                    ("integrity_warning", "Integrity warning"),
                    ("fs_imported", "Filesystem imported"),
                    ("fs_original_gone", "Filesystem original gone"),
                    ("fs_pruned", "Filesystem pruned"),
                    ("path_migrated", "Path migrated"),
                ],
                default="watch",
                max_length=20,
            ),
        ),
    ]
