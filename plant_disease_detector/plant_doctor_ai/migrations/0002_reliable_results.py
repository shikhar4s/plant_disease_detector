from django.db import migrations, models


def fix_legacy_severity(apps, schema_editor):
    apps.get_model('plant_doctor_ai', 'AnalysisResult').objects.update(severity='Unknown')


class Migration(migrations.Migration):
    dependencies = [('plant_doctor_ai', '0001_initial')]
    operations = [
        migrations.AddField(model_name='analysisresult', name='image_preview', field=models.TextField(blank=True)),
        migrations.AddField(model_name='analysisresult', name='top_predictions', field=models.JSONField(default=list)),
        migrations.AddField(model_name='analysisresult', name='guidance_source', field=models.CharField(default='care-guide', max_length=30)),
        migrations.AddField(model_name='analysisresult', name='notes', field=models.CharField(blank=True, max_length=2000)),
        migrations.AlterField(model_name='analysisresult', name='image', field=models.ImageField(blank=True, upload_to='analyses/%Y/%m/%d/')),
        migrations.AlterField(model_name='analysisresult', name='severity', field=models.CharField(choices=[('Unknown', 'Not assessed'), ('Low', 'Low (legacy)'), ('Medium', 'Medium (legacy)'), ('High', 'High (legacy)')], default='Unknown', max_length=10)),
        migrations.AlterField(model_name='analysisresult', name='expected_recovery_time', field=models.CharField(default='Not estimated from a photo', max_length=100)),
        migrations.AlterModelOptions(name='analysisresult', options={'ordering': ['-created_at', '-id']}),
        migrations.RunPython(fix_legacy_severity, migrations.RunPython.noop),
    ]
