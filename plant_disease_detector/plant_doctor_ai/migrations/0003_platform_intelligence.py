import base64
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_analysis_metadata(apps, schema_editor):
    AnalysisResult = apps.get_model('plant_doctor_ai', 'AnalysisResult')
    for item in AnalysisResult.objects.all().iterator(chunk_size=100):
        crop, condition = (item.disease_name.split('___', 1) + [''])[:2]
        status = ('uncertain' if item.confidence < 0.7 else
                  'healthy' if item.disease_name.lower().endswith('___healthy') else 'possible_disease')
        payload = b''
        if item.image_preview and ';base64,' in item.image_preview:
            try:
                payload = base64.b64decode(item.image_preview.split(';base64,', 1)[1], validate=True)
            except (ValueError, TypeError):
                payload = b''
        item.crop_name = crop.replace('_', ' ').replace(',', '').strip()
        item.condition_name = condition.replace('_', ' ').strip()
        item.status = status
        item.model_version = 'legacy-cnn-pv38-v1'
        item.image_preview_bytes = payload
        if payload:
            item.image_preview = ''
        item.save(update_fields=['crop_name', 'condition_name', 'status', 'model_version',
                                 'image_preview_bytes', 'image_preview'])


class Migration(migrations.Migration):
    dependencies = [('plant_doctor_ai', '0002_reliable_results'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='analysisresult', name='condition_name', field=models.CharField(blank=True, max_length=180)),
        migrations.AddField(model_name='analysisresult', name='crop_name', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='analysisresult', name='image_mime', field=models.CharField(default='image/jpeg', max_length=40)),
        migrations.AddField(model_name='analysisresult', name='image_preview_bytes', field=models.BinaryField(blank=True, default=bytes)),
        migrations.AddField(model_name='analysisresult', name='model_version', field=models.CharField(default='legacy-cnn-pv38-v1', max_length=80)),
        migrations.AddField(model_name='analysisresult', name='status', field=models.CharField(blank=True, default='', max_length=30)),
        migrations.CreateModel(name='MandiSnapshot', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('provider', models.CharField(default='data.gov.in', max_length=40)),
            ('state', models.CharField(max_length=120)), ('district', models.CharField(blank=True, max_length=120)),
            ('market', models.CharField(max_length=160)), ('commodity', models.CharField(max_length=160)),
            ('variety', models.CharField(blank=True, max_length=160)),
            ('min_price', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
            ('max_price', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
            ('modal_price', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
            ('unit', models.CharField(default='INR/quintal', max_length=50)),
            ('price_date', models.DateField()), ('fetched_at', models.DateTimeField(auto_now=True)),
        ], options={'ordering': ['-price_date', '-fetched_at']}),
        migrations.AddConstraint(model_name='mandisnapshot', constraint=models.UniqueConstraint(
            fields=('provider', 'state', 'district', 'market', 'commodity', 'variety', 'price_date'), name='unique_mandi_observation')),
        migrations.CreateModel(name='CommodityWatchlist', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('commodity', models.CharField(max_length=160)), ('state', models.CharField(blank=True, max_length=120)),
            ('district', models.CharField(blank=True, max_length=120)), ('market', models.CharField(blank=True, max_length=160)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commodity_watchlist', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['commodity', 'state', 'district', 'market']}),
        migrations.AddConstraint(model_name='commoditywatchlist', constraint=models.UniqueConstraint(
            fields=('user', 'commodity', 'state', 'district', 'market'), name='unique_user_watchlist_item')),
        migrations.RunPython(migrate_analysis_metadata, migrations.RunPython.noop),
    ]
