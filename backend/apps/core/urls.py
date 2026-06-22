from django.urls import path

from .views import (
    ActivityLogListView,
    CommandHistoryDetailView,
    CommandHistoryListView,
    RunCommandView,
)

urlpatterns = [
    path("logs/", ActivityLogListView.as_view(), name="logs"),
    path("commands/", CommandHistoryListView.as_view(), name="commands"),
    path("commands/<int:pk>/", CommandHistoryDetailView.as_view(), name="command-detail"),
    path("terminal/run/", RunCommandView.as_view(), name="terminal-run"),
]
