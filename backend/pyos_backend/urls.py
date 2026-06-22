from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/health/', health_check),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/", include("apps.filesystem.urls")),
    path("api/", include("apps.core.urls")),
]
