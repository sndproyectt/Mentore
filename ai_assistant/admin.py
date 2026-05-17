from django.contrib import admin
from .models import ChatHistory, ConversationSummary, UserMemory


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'short_message', 'created_at']
    list_filter = ['user', 'created_at']
    search_fields = ['user__username', 'user_message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

    def short_message(self, obj):
        return obj.user_message[:80] + "..." if len(obj.user_message) > 80 else obj.user_message
    short_message.short_description = "Mensaje"


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ['user', 'messages_covered', 'short_summary', 'created_at']
    list_filter = ['user', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def short_summary(self, obj):
        return obj.summary[:100] + "..." if len(obj.summary) > 100 else obj.summary
    short_summary.short_description = "Resumen"


@admin.register(UserMemory)
class UserMemoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'teaching_grade', 'subjects', 'updated_at']
    list_filter = ['teaching_grade']
    search_fields = ['user__username', 'teaching_grade', 'subjects']
    readonly_fields = ['created_at', 'updated_at']
