# Generated by Django 5.1.3 on 2024-11-22 00:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('record', '0011_transaction_is_maeukekin'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='is_mishuukin',
            field=models.BooleanField(default=False, verbose_name='未収金'),
        ),
    ]
