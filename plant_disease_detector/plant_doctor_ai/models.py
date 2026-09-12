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
    image_preview_bytes = models.BinaryField(blank=True, default=bytes)
    image_mime = models.CharField(max_length=40, default='image/jpeg')
    crop_name = models.CharField(max_length=120, blank=True)
    condition_name = models.CharField(max_length=180, blank=True)
    disease_name = models.CharField(max_length=255)
    confidence = models.FloatField()
    status = models.CharField(max_length=30, blank=True, default='')
    model_version = models.CharField(max_length=80, default='legacy-cnn-pv38-v1')
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
        if self.status in {'healthy', 'uncertain', 'possible_disease'}:
            return self.status
        if self.confidence < 0.7:
            return 'uncertain'
        return 'healthy' if self.disease_name.lower().endswith('___healthy') else 'possible_disease'

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.disease_name} ({self.created_at:%Y-%m-%d})'


class MandiSnapshot(models.Model):
    provider = models.CharField(max_length=40, default='data.gov.in')
    state = models.CharField(max_length=120)
    district = models.CharField(max_length=120, blank=True)
    market = models.CharField(max_length=160)
    commodity = models.CharField(max_length=160)
    variety = models.CharField(max_length=160, blank=True)
    min_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    max_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    modal_price = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    unit = models.CharField(max_length=50, default='INR/quintal')
    price_date = models.DateField()
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-price_date', '-fetched_at']
        constraints = [models.UniqueConstraint(
            fields=['provider', 'state', 'district', 'market', 'commodity', 'variety', 'price_date'],
            name='unique_mandi_observation')]


class CommodityWatchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='commodity_watchlist')
    commodity = models.CharField(max_length=160)
    state = models.CharField(max_length=120, blank=True)
    district = models.CharField(max_length=120, blank=True)
    market = models.CharField(max_length=160, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['commodity', 'state', 'district', 'market']
        constraints = [models.UniqueConstraint(
            fields=['user', 'commodity', 'state', 'district', 'market'], name='unique_user_watchlist_item')]
