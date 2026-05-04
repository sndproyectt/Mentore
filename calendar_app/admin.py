from django.contrib import admin
from .models import GoogleCalendarToken

@admin.register(GoogleCalendarToken)
class GoogleCalendarTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at", "token_expiry")
    readonly_fields = ("created_at", "updated_at")
