from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('telemetry_app', '0031_merge_20260204_1340'),
    ]

    operations = [
        migrations.AddField(
            model_name='flighttaskinfo',
            name='flight_duration',
            field=models.IntegerField(default=0, verbose_name='飞行时长(秒)'),
        ),
        migrations.AddField(
            model_name='flighttaskinfo',
            name='flight_distance',
            field=models.FloatField(default=0.0, verbose_name='飞行里程(km)'),
        ),
    ]
