from django.urls import path
from .views import (AnalyzePlantView, AnalysisHistoryView, AnalysisDetailView, ExportHistoryView,
                    AnalyticsDashboardView, ChatbotView, SupportedPlantsView, MandiRatesView, CommodityImagesView,
                    MandiHistoryView, WeatherView, WeatherRiskView, WatchlistView, WatchlistDetailView)
urlpatterns = [
    path('analyze/', AnalyzePlantView.as_view(), name='analyze-plant'),
    path('history/', AnalysisHistoryView.as_view(), name='analysis-history'),
    path('history/export/', ExportHistoryView.as_view(), name='export-history'),
    path('history/<int:pk>/', AnalysisDetailView.as_view(), name='analysis-detail'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('plants/', SupportedPlantsView.as_view(), name='supported-plants'),
    path('chat/', ChatbotView.as_view(), name='chat'),
    path('mandi/', MandiRatesView.as_view(), name='mandi-rates'),
    path('mandi/images/', CommodityImagesView.as_view(), name='mandi-images'),
    path('mandi/history/', MandiHistoryView.as_view(), name='mandi-history'),
    path('commodity-images/', CommodityImagesView.as_view(), name='commodity-images'),
    path('weather/', WeatherView.as_view(), name='weather'),
    path('risk/', WeatherRiskView.as_view(), name='weather-risk'),
    path('watchlist/', WatchlistView.as_view(), name='watchlist'),
    path('watchlist/<int:pk>/', WatchlistDetailView.as_view(), name='watchlist-detail'),
]

