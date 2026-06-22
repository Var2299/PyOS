from django.contrib import admin

from .models import ActivityLog, CommandHistory

admin.site.register(ActivityLog)
admin.site.register(CommandHistory)
