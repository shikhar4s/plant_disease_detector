from rest_framework import serializers
import base64

from .models import AnalysisResult, CommodityWatchlist
from .services.disease_registry import disease_info
from .services.model_service import display_name


class AnalysisResultSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()
    prediction_status = serializers.CharField(read_only=True)
    information = serializers.SerializerMethodField()

    class Meta:
        model = AnalysisResult
        fields = ['id', 'image_url', 'crop_name', 'condition_name', 'disease', 'disease_name', 'confidence',
                  'severity', 'status', 'model_version', 'created_at', 'information',
                  'recommended_treatment', 'expected_recovery_time', 'prevention_tips', 'top_predictions',
                  'guidance_source', 'prediction_status', 'notes']
        read_only_fields = [f for f in fields if f != 'notes']

    def get_image_url(self, obj):
        if obj.image_preview_bytes:
            return f'data:{obj.image_mime};base64,' + base64.b64encode(bytes(obj.image_preview_bytes)).decode('ascii')
        if obj.image_preview:
            return obj.image_preview
        # Legacy files have no public media route; migrate them to previews before hosting.
        return None

    def get_disease(self, obj):
        return display_name(obj.disease_name)

    def get_information(self, obj):
        request = self.context.get('request')
        language = request.headers.get('Language', 'en') if request else 'en'
        return disease_info(obj.disease_name, obj.prediction_status == 'uncertain', language)


class ChatPartSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4096, allow_blank=False)


class ChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'model'])
    parts = serializers.ListField(child=ChatPartSerializer(), min_length=1, max_length=1)


class ChatbotRequestSerializer(serializers.Serializer):
    history = serializers.ListField(child=ChatHistoryItemSerializer(), max_length=20, required=False, default=list)
    newMessage = serializers.CharField(max_length=4096, allow_blank=False, trim_whitespace=True)
    analysisId = serializers.IntegerField(required=False, min_value=1)
    weatherContextId = serializers.CharField(required=False, max_length=80)
    mandiContextId = serializers.CharField(required=False, max_length=80)


class WatchlistSerializer(serializers.ModelSerializer):
    latest = serializers.SerializerMethodField()

    class Meta:
        model = CommodityWatchlist
        fields = ['id', 'commodity', 'state', 'district', 'market', 'created_at', 'latest']
        read_only_fields = ['id', 'created_at', 'latest']

    def validate(self, attrs):
        for key in ('commodity', 'state', 'district', 'market'):
            if key in attrs:
                attrs[key] = attrs[key].strip()
        if not attrs.get('commodity'):
            raise serializers.ValidationError({'commodity': 'Commodity is required.'})
        request = self.context.get('request')
        if request and CommodityWatchlist.objects.filter(user=request.user,
                commodity__iexact=attrs['commodity'], state__iexact=attrs.get('state', ''),
                district__iexact=attrs.get('district', ''), market__iexact=attrs.get('market', '')).exists():
            raise serializers.ValidationError('This commodity and market scope is already on your watchlist.')
        return attrs

    def get_latest(self, obj):
        from .models import MandiSnapshot
        query = MandiSnapshot.objects.filter(commodity__iexact=obj.commodity)
        if obj.state:
            query = query.filter(state__iexact=obj.state)
        if obj.district:
            query = query.filter(district__iexact=obj.district)
        if obj.market:
            query = query.filter(market__iexact=obj.market)
        item = query.first()
        return None if not item else {
            'modal_price': float(item.modal_price) if item.modal_price is not None else None,
            'unit': item.unit, 'market': item.market, 'price_date': item.price_date.isoformat(),
        }
