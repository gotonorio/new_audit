# Generated by Django 5.0.4 on 2024-04-27 04:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monthly_report', '0005_reporttransaction_is_miharai'),
    ]

    operations = [
        migrations.AddField(
            model_name='reporttransaction',
            name='is_manualinput',
            field=models.BooleanField(default=False),
        ),
    ]