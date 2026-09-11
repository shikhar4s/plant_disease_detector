from django.db import models
from django.conf import settings


class AnalysisResult(models.Model):
    class Severity(models.TextChoices):
        UNKNOWN = 'Unknown', 'Not assessed'
        LOW = 'Low', 'Low (legacy)'
        MEDIUM = 'Medium', 'Medium (legacy)'
        HIGH = 'High', 'High (legacy)'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    image = models.ImageField(upload_to='analyses/%Y/%m/%d/', blank=True)
    image_preview = models.TextField(blank=True)
    disease_name = models.CharField(max_length=255)
    confidence = models.FloatField()
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.UNKNOWN)
    recommended_treatment = models.TextField()
    prevention_tips = models.JSONField(default=list)
    expected_recovery_time = models.CharField(max_length=100, default='Not estimated from a photo')
    top_predictions = models.JSONField(default=list)
    guidance_source = models.CharField(max_length=30, default='care-guide')
    notes = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def prediction_status(self):
        if self.confidence < 0.7:
            return 'uncertain'
        return 'healthy' if self.disease_name.lower().endswith('___healthy') else 'possible_disease'

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.disease_name} ({self.created_at:%Y-%m-%d})'
