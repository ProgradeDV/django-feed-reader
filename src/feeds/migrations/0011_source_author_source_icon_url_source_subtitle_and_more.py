# Generated by Django 4.2.10 on 2024-04-06 15:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0010_enclosure_description_enclosure_medium'),
    ]

    operations = [
        migrations.AddField(
            model_name='source',
            name='author',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='source',
            name='icon_url',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name='source',
            name='subtitle',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='source',
            name='title',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.TextField(blank=True)),
                ('body', models.TextField()),
                ('link', models.CharField(blank=True, max_length=512, null=True)),
                ('created', models.DateTimeField(db_index=True)),
                ('guid', models.CharField(blank=True, db_index=True, max_length=512, null=True)),
                ('author', models.CharField(blank=True, max_length=255, null=True)),
                ('index', models.IntegerField(db_index=True)),
                ('image_url', models.CharField(blank=True, max_length=512, null=True)),
                ('found', models.DateTimeField(auto_now_add=True)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='feeds.source')),
            ],
            options={
                'ordering': ['index'],
            },
        ),
        migrations.AlterField(
            model_name='enclosure',
            name='post',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enclosures', to='feeds.entry'),
        ),
        migrations.DeleteModel(
            name='Post',
        ),
    ]
