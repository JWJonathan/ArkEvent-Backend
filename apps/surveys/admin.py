from django.contrib import admin
from .models import Survey, SurveyQuestion, SurveyAnswer

class SurveyQuestionInline(admin.TabularInline):
    model = SurveyQuestion
    extra = 1

@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'is_active', 'created_at')
    list_filter = ('is_active', 'event')
    search_fields = ('title', 'description', 'event__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('event',)
    inlines = [SurveyQuestionInline]

@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ('question', 'survey', 'question_type', 'sort_order')
    list_filter = ('question_type', 'survey')
    search_fields = ('question', 'survey__title')
    raw_id_fields = ('survey',)

@admin.register(SurveyAnswer)
class SurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'answer', 'created_at')
    list_filter = ('created_at', 'question__survey')
    search_fields = ('answer', 'question__question', 'user__email')
    raw_id_fields = ('question', 'user')
