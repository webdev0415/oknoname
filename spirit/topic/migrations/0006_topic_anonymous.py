# Generated by Django 3.0.9 on 2020-08-25 19:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spirit_topic', '0005_auto_20200824_1512'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='anonymous',
            field=models.BooleanField(default=False),
        ),
    ]
