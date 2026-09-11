from rest_framework import serializers
from .models import AnalysisResult
from .services.model_service import display_name


class AnalysisResultSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()
    prediction_status = serializers.CharField(read_only=True)

    class Meta:
        model = AnalysisResult
        fields = ['id', 'image_url', 'disease', 'disease_name', 'confidence', 'severity', 'created_at',
                  'recommended_treatment', 'expected_recovery_time', 'prevention_tips', 'top_predictions',
                  'guidance_source', 'prediction_status', 'notes']
        read_only_fields = [f for f in fields if f != 'notes']

    def get_image_url(self, obj):
        if obj.image_preview:
            return obj.image_preview
        # Legacy files have no public media route; migrate them to previews before hosting.
        return None

    def get_disease(self, obj):
        return display_name(obj.disease_name)


class ChatPartSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4096, allow_blank=False)


class ChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'model'])
    parts = serializers.ListField(child=ChatPartSerializer(), min_length=1, max_length=1)


class ChatbotRequestSerializer(serializers.Serializer):
    history = serializers.ListField(child=ChatHistoryItemSerializer(), max_length=20, required=False, default=list)
    newMessage = serializers.CharField(max_length=4096, allow_blank=False, trim_whitespace=True)
    analysisId = serializers.IntegerField(required=False, min_value=1)
