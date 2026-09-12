import os

from django.contrib import admin
from django.db import connection
from django.http import FileResponse, JsonResponse
from django.conf import settings
from django.urls import include, path, re_path
from django.views.decorators.cache import never_cache


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        if not (settings.BASE_DIR / 'deployment_artifacts' / 'plant_disease_model.pth').is_file():
            return JsonResponse({'status': 'unavailable'}, status=503)
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({
        'status': 'ok',
        'integrations': {
            'gemini': {
                'configured': bool(os.getenv('GEMINI_API_KEY', '').strip()),
                'model': os.getenv('GEMINI_MODEL', 'gemini-3.5-flash').removeprefix('models/'),
            },
            'mandi': {'configured': bool(os.getenv('DATA_GOV_IN_API_KEY', '').strip())},
            'weather': {'configured': True},
        },
    })


@never_cache
def frontend(request):
    index = settings.FRONTEND_DIR / 'index.html'
    if not index.exists():
        return JsonResponse({'detail': 'Build the frontend or use the Vite development server.'}, status=503)
    return FileResponse(index.open('rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('healthz', health),
    path('api/users/', include('users.urls')),
    path('api/plant_doctor_ai/', include('plant_doctor_ai.urls')),
    re_path(r'^(?!api/|admin/|media/|static/|assets/).*$', frontend),
]
