from django.contrib import admin
from .models import (
    AIDownloadLog,
    AIFeedback,
    AIMessageVersion,
    ChatDocument,
    ChatHistory,
    ConversationSummary,
    GeneratedDocument,
    GlobalAssistantPreference,
    UserMemory,
)


@admin.register(ChatDocument)
class ChatDocumentAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'user', 'file_type', 'file_size', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['original_name', 'user__username']
    readonly_fields = ['created_at', 'extracted_text', 'extraction_error']
    ordering = ['-created_at']


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


@admin.register(AIMessageVersion)
class AIMessageVersionAdmin(admin.ModelAdmin):
    list_display = ['message', 'numero_version', 'created_at']
    list_filter = ['created_at']
    search_fields = ['message__user__username', 'content']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(AIFeedback)
class AIFeedbackAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'mensaje', 'tipo', 'fecha']
    list_filter = ['tipo', 'fecha']
    search_fields = ['usuario__username', 'mensaje__user_message', 'mensaje__ai_response']
    readonly_fields = ['fecha']
    ordering = ['-fecha']


@admin.register(AIDownloadLog)
class AIDownloadLogAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'mensaje', 'formato', 'filename', 'fecha']
    list_filter = ['formato', 'fecha']
    search_fields = ['usuario__username', 'filename']
    readonly_fields = ['fecha']
    ordering = ['-fecha']


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'user', 'file_format', 'file_size', 'created_at']
    list_filter = ['file_format', 'created_at']
    search_fields = ['original_name', 'user__username']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(GlobalAssistantPreference)
class GlobalAssistantPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'avatar', 'size', 'position', 'drawer_width', 'is_visible',
        'animations_enabled', 'updated_at',
    ]
    list_filter = [
        'avatar', 'size', 'position', 'border_color', 'shadow',
        'activity_effect', 'is_visible', 'animations_enabled',
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


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
