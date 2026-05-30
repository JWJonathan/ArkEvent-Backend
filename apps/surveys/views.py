from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Survey, SurveyQuestion, SurveyAnswer
from .serializers import SurveySerializer, SurveyQuestionSerializer, SurveyAnswerSerializer
from apps.core.permissions import IsAdmin
from apps.notifications.services import NotificationService

class SurveyViewSet(viewsets.ModelViewSet):
    queryset = Survey.objects.all().order_by('-created_at')
    serializer_class = SurveySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        survey = serializer.save()
        # Notify participants of the event
        NotificationService.notify_all_participants(
            event=survey.event,
            title=f"Nouveau sondage pour {survey.event.title}",
            body=f"Votre avis nous intéresse ! Veuillez répondre au sondage : {survey.title}",
            metadata={'survey_id': str(survey.id)}
        )

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())

    def perform_destroy(self, instance):
        instance.delete()


class SurveyQuestionViewSet(viewsets.ModelViewSet):
    queryset = SurveyQuestion.objects.all().order_by('survey__title', 'sort_order')
    serializer_class = SurveyQuestionSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsAdmin()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    def perform_destroy(self, instance):
        instance.delete()


class SurveyAnswerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SurveyAnswer.objects.all().order_by('-created_at')
    serializer_class = SurveyAnswerSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

