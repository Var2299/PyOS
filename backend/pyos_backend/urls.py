from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "healthy", "message": "PyOS Backend is awake!"}, status=200)
    
urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/health/', health_check),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.filesystem.urls")),
    path("api/", include("apps.core.urls")),
]
