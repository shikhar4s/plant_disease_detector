import csv
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView, ListCreateAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .images import read_image, preview_bytes, validate_photo_quality
from .models import AnalysisResult, MandiSnapshot, CommodityWatchlist
from .serializers import AnalysisResultSerializer, ChatbotRequestSerializer, WatchlistSerializer
from .services.care_guide import language_code
from .services.gemini_service import gemini_service
from .services.model_service import model_service, class_names, display_name, model_manifest
from .services.disease_registry import split_label
from .services.mandi_service import search_mandi, mandi_options, MandiProviderError
from .services.market_history_service import market_history
from .services.commodity_image_service import resolve_commodity_images
from .services.weather_service import weather, search_locations, WeatherProviderError
from .services.risk_service import weather_risk
from .services.context_store import load_context

logger = logging.getLogger(__name__)


class AnalyzePlantView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope = 'analyze'

    def post(self, request):
        image = read_image(request.FILES.get('image'))
        validate_photo_quality(image)
        language = language_code(request.headers.get('Language'))
        type(request.user).objects.filter(pk=request.user.pk).update(total_uploads=F('total_uploads') + 1)
        try:
            prediction = model_service.predict(image)
        except Exception:
            logger.exception('Plant model inference failed')
            return Response({'error': 'Analysis is temporarily unavailable. Please try again shortly.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        guidance = gemini_service.get_treatment_info(prediction['disease'], language, prediction['status'] == 'uncertain')
        crop, condition = split_label(prediction['disease'])
        with transaction.atomic():
            analysis = AnalysisResult.objects.create(
                user=request.user, image_preview_bytes=preview_bytes(image), image_mime='image/jpeg',
                crop_name=crop, condition_name=condition, status=prediction['status'],
                model_version=prediction['model_version'],
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
        queryset = queryset.filter(Q(status='uncertain') | Q(status='', confidence__lt=0.7))
    elif result_status == 'healthy':
        queryset = queryset.filter(Q(status='healthy') | Q(status='', confidence__gte=0.7, disease_name__iendswith='___healthy'))
    elif result_status == 'possible_disease':
        queryset = queryset.filter(Q(status='possible_disease') | (Q(status='', confidence__gte=0.7) & ~Q(disease_name__iendswith='___healthy')))
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

        for item in history_queryset(request).defer('image_preview', 'image_preview_bytes', 'image').iterator(chunk_size=100):
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
            {'name': name, 'conditions': conditions} for name, conditions in sorted(plants.items())],
            'model': model_manifest()})


class MandiRatesView(APIView):
    throttle_scope = 'market'

    def get(self, request):
        try:
            return Response(search_mandi(request.user.id, request.query_params))
        except ValueError as exc:
            return Response({'error': str(exc), 'source': 'AGMARKNET via data.gov.in'}, status=400)
        except MandiProviderError as exc:
            return Response({'error': str(exc), 'source': 'AGMARKNET via data.gov.in'}, status=503)


class MandiHistoryView(APIView):
    throttle_scope = 'market'

    def get(self, request):
        try:
            return Response(market_history(request.query_params))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)


class MandiOptionsView(APIView):
    throttle_scope = 'market'

    def get(self, request):
        try:
            return Response(mandi_options(request.query_params))
        except MandiProviderError as exc:
            return Response({'error': str(exc), 'source': 'AGMARKNET via data.gov.in'}, status=503)


class CommodityImagesView(APIView):
    throttle_scope = 'market'

    def post(self, request):
        names = request.data.get('commodities')
        if not isinstance(names, list) or len(names) > 30 or any(not isinstance(name, str) for name in names):
            return Response({'error': 'commodities must be a list of names.'}, status=400)
        return Response({'images': resolve_commodity_images(names),
                         'source': {'name': 'Wikimedia Commons', 'url': 'https://commons.wikimedia.org/'}})

    def get(self, request):
        raw = request.query_params.get('commodities', '')
        commodities = [item.strip() for item in raw.split(',') if item.strip()]
        if len(commodities) > 30 or any(len(name) > 160 for name in commodities):
            return Response({'error': 'Request up to 30 commodity names, each at most 160 characters.'}, status=400)
        return Response({'images': resolve_commodity_images(commodities),
                         'source': {'name': 'Wikimedia Commons', 'url': 'https://commons.wikimedia.org/'}})


class WeatherView(APIView):
    throttle_scope = 'weather'

    def get(self, request):
        try:
            result = weather(request.user.id, city=request.query_params.get('city', ''),
                latitude=request.query_params.get('latitude'), longitude=request.query_params.get('longitude'),
                location_id=request.query_params.get('location_id'),
                language=request.headers.get('Language', 'en'))
            return Response(result)
        except WeatherProviderError as exc:
            code = 400 if exc.status_code == 400 or str(exc).startswith(('Enter', 'Invalid', 'No matching', 'Choose')) else 503
            return Response({'error': str(exc), 'source': 'Open-Meteo'}, status=code)


class WeatherLocationsView(APIView):
    throttle_scope = 'weather'

    def get(self, request):
        try:
            return Response(search_locations(request.query_params.get('q', ''),
                language=request.headers.get('Language', 'en')))
        except WeatherProviderError as exc:
            code = 400 if str(exc).startswith(('Enter', 'Invalid', 'No matching')) else 503
            return Response({'error': str(exc), 'source': 'Open-Meteo'}, status=code)


class WeatherCatalogView(APIView):
    throttle_scope = 'weather'

    def get(self, request):
        from .services.india_location_service import list_cities, list_states
        state = request.query_params.get('state')
        if state is None:
            return Response(list_states())
        try:
            return Response(list_cities(state))
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)


class WeatherRiskView(APIView):
    def post(self, request):
        context = load_context(request.user.id, 'weather', str(request.data.get('weatherContextId', '')))
        if not context:
            return Response({'error': 'Fetch current weather before calculating risk.'}, status=400)
        crop = str(request.data.get('crop', ''))[:120]
        disease = str(request.data.get('disease', ''))[:180]
        return Response(weather_risk(context, crop, disease, request.headers.get('Language', 'en')))


class WatchlistView(ListCreateAPIView):
    serializer_class = WatchlistSerializer

    def get_queryset(self):
        return CommodityWatchlist.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchlistDetailView(APIView):
    def delete(self, request, pk):
        item = get_object_or_404(CommodityWatchlist, pk=pk, user=request.user)
        item.delete()
        return Response(status=204)


class ChatbotView(APIView):
    throttle_scope = 'chat'

    def post(self, request):
        serializer = ChatbotRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if sum(len(item['parts'][0]['text']) for item in data['history']) > 20000:
            return Response({'error': 'Conversation is too long. Start a new chat.'}, status=400)
        analysis = get_object_or_404(AnalysisResult, pk=data['analysisId'], user=request.user) if data.get('analysisId') else None
        weather_context = load_context(request.user.id, 'weather', data.get('weatherContextId'))
        mandi_context = load_context(request.user.id, 'mandi', data.get('mandiContextId'))
        return Response(gemini_service.process_chat(data['history'], data['newMessage'],
            language=request.headers.get('Language'), analysis=analysis, weather=weather_context, mandi=mandi_context))
