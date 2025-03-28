# Generated by Django 5.1.7 on 2025-03-23 03:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='right_answer',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.CreateModel(
            name='Ordinance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500)),
                ('text', models.TextField()),
                ('county', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.county')),
            ],
        ),
        migrations.AddField(
            model_name='question',
            name='ordinance',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='polls.ordinance'),
        ),
    ]
