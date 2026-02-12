from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("telemetry_app", "0031_merge_20260204_1340"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="inspectimage",
            index=models.Index(
                fields=["inspect_task", "detect_status"],
                name="insimg_task_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="inspectimage",
            index=models.Index(
                fields=["inspect_task", "object_key"],
                name="insimg_task_objkey_idx",
            ),
        ),
    ]
