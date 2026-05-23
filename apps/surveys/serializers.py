from rest_framework import serializers
from .models import Survey, SurveyQuestion, SurveyAnswer

class SurveySerializer(serializers.ModelSerializer):
    event_title = serializers.ReadOnlyField(source='event.title')

    class Meta:
        model = Survey
        fields = ['id', 'event_id', 'event_title', 'title', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

class SurveyQuestionSerializer(serializers.ModelSerializer):
    survey_title = serializers.ReadOnlyField(source='survey.title')

    class Meta:
        model = SurveyQuestion
        fields = ['id', 'survey_id', 'survey_title', 'question', 'question_type', 'options', 'sort_order', 'created_at']
        read_only_fields = ['id', 'created_at']

class SurveyAnswerSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.profile.full_name')

    class Meta:
        model = SurveyAnswer
        fields = ['id', 'question_id', 'user_id', 'user_name', 'answer', 'created_at']
        read_only_fields = ['id', 'created_at']

