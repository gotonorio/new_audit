# Generated by Django 5.0 on 2023-12-19 12:21

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("record", "0004_transaction_is_approval"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApprovalCheckData",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "atext",
                    models.CharField(
                        blank=True,
                        max_length=16,
                        null=True,
                        unique=True,
                        verbose_name="チェック文字列",
                    ),
                ),
                (
                    "comment",
                    models.CharField(
                        blank=True, max_length=50, null=True, verbose_name="備考"
                    ),
                ),
                ("alive", models.BooleanField(default=True, verbose_name="有効")),
            ],
        ),
    ]