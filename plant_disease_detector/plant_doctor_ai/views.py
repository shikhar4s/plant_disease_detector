import csv
import logging

from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .images import read_image, preview_data_uri
from .models import AnalysisResult
from .serializers import AnalysisResultSerializer, ChatbotRequestSerializer
from .services.care_guide import language_code
from .services.gemini_service import gemini_service
from .services.model_service import model_service, class_names, display_name

logger = logging.getLogger(__name__)


class AnalyzePlantView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = 'analyze'

    def post(self, request):
        image = read_image(request.FILES.get('image'))
        language = language_code(request.headers.get('Language'))
        type(request.user).objects.filter(pk=request.user.pk).update(total_uploads=F('total_uploads') + 1)
        try:
            prediction = model_service.predict(image)
        except Exception:
            logger.exception('Plant model inference failed')
            return Response({'error': 'Analysis is temporarily unavailable. Please try again shortly.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        guidance = gemini_service.get_treatment_info(prediction['disease'], language, prediction['confidence'] < 0.7)
        with transaction.atomic():
            analysis = AnalysisResult.objects.create(
                user=request.user, image_preview=preview_data_uri(image),
                disease_name=prediction['disease'], confidence=prediction['confidence'],
                severity=AnalysisResult.Severity.UNKNOWN, top_predictions=prediction['top_predictions'],
                **guidance,
            )
            type(request.user).objects.filter(pk=request.user.pk).update(total_analyzed=F('total_analyzed') + 1)
        return Response(AnalysisResultSerializer(analysis).data, status=status.HTTP_201_CREATED)


def history_queryset(request):
    queryset = AnalysisResult.objects.filter(user=request.user)
    query = request.query_params.get('q', '').strip()[:200]
    if query:
        queryset = queryset.filter(Q(disease_name__icontains=query.replace(' ', '_')) | Q(notes__icontains=query))
    result_status = request.query_params.get('status')
    if result_status == 'uncertain':
        queryset = queryset.filter(confidence__lt=0.7)
    elif result_status == 'healthy':
        queryset = queryset.filter(confidence__gte=0.7, disease_name__iendswith='___healthy')
    elif result_status == 'possible_disease':
        queryset = queryset.filter(confidence__gte=0.7).exclude(disease_name__iendswith='___healthy')
    return queryset


class HistoryPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class AnalysisHistoryView(ListAPIView):
    serializer_class = AnalysisResultSerializer
    pagination_class = HistoryPagination

    def get_queryset(self):
        return history_queryset(self.request)


class AnalysisDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = AnalysisResultSerializer
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return AnalysisResult.objects.filter(user=self.request.user)


class ExportHistoryView(APIView):
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="plantdoc-history.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Date', 'Possible match', 'Model confidence (%)', 'Status', 'Care guidance', 'Notes'])

        def cell(value):
            text = str(value)
            return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text

        for item in history_queryset(request).defer('image_preview').iterator(chunk_size=100):
            writer.writerow([cell(value) for value in [item.created_at.isoformat(), display_name(item.disease_name),
                round(item.confidence * 100, 2), item.prediction_status, item.recommended_treatment, item.notes]])
        return response


class AnalyticsDashboardView(APIView):
    def get(self, request):
        queryset = AnalysisResult.objects.filter(user=request.user)
        analyzed = queryset.count()
        healthy = queryset.filter(confidence__gte=0.7, disease_name__iendswith='___healthy').count()
        uncertain = queryset.filter(confidence__lt=0.7).count()
        return Response({
            'summary': {
                'totalUploads': request.user.total_uploads, 'analyzed': analyzed,
                'successRate': round(min(100, request.user.total_analyzed / request.user.total_uploads * 100), 1)
                    if request.user.total_uploads else 0,
                'avgConfidence': round((queryset.aggregate(value=Avg('confidence'))['value'] or 0) * 100, 1),
            },
            'diseaseDistribution': [{'name': display_name(item['disease_name']), 'value': item['count']}
                for item in queryset.values('disease_name').annotate(count=Count('id')).order_by('-count')],
            'statusDistribution': [{'name': 'healthy', 'value': healthy}, {'name': 'uncertain', 'value': uncertain},
                                  {'name': 'possible_disease', 'value': analyzed - healthy - uncertain}],
        })


class SupportedPlantsView(APIView):
    def get(self, request):
        plants = {}
        for label in class_names():
            plant, condition = label.split('___', 1)
            plants.setdefault(plant.replace('_', ' '), []).append(condition.replace('_', ' '))
        return Response({'classCount': len(class_names()), 'plants': [
            {'name': name, 'conditions': conditions} for name, conditions in sorted(plants.items())
        ]})


class ChatbotView(APIView):
    throttle_scope = 'chat'

    def post(self, request):
        serializer = ChatbotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if sum(len(item['parts'][0]['text']) for item in data['history']) > 20000:
            return Response({'error': 'Conversation is too long. Start a new chat.'}, status=400)
        analysis = get_object_or_404(AnalysisResult, pk=data['analysisId'], user=request.user) if data.get('analysisId') else None
        return Response(gemini_service.process_chat(data['history'], data['newMessage'],
            language=request.headers.get('Language'), analysis=analysis))
