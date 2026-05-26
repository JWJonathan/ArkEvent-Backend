from django.db import models
from django.conf import settings
import uuid

class Survey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey('events.Event', on_delete=models.CASCADE, db_column='event_id', related_name='surveys')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'arkevent.surveys'

    def __str__(self):
        return self.title


class SurveyQuestion(models.Model):
    QUESTION_TYPES = [
        ('text', 'Text'),
        ('rating', 'Rating'),
        ('multiple_choice', 'Multiple Choice'),
        ('yes_no', 'Yes/No'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, db_column='survey_id', related_name='questions')
    question = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    options = models.JSONField(default=list, blank=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.survey_questions'

    def __str__(self):
        return self.question


class SurveyAnswer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, db_column='question_id', related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, db_column='user_id', related_name='survey_answers')
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arkevent.survey_answers'

    def __str__(self):
        return self.answer[:50]