from django.urls import path
from .views import (AnalyzePlantView, AnalysisHistoryView, AnalysisDetailView, ExportHistoryView,
                    AnalyticsDashboardView, ChatbotView, SupportedPlantsView)

urlpatterns = [
    path('analyze/', AnalyzePlantView.as_view(), name='analyze-plant'),
    path('history/', AnalysisHistoryView.as_view(), name='analysis-history'),
    path('history/export/', ExportHistoryView.as_view(), name='export-history'),
    path('history/<int:pk>/', AnalysisDetailView.as_view(), name='analysis-detail'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('plants/', SupportedPlantsView.as_view(), name='supported-plants'),
    path('chat/', ChatbotView.as_view(), name='chat'),
]
