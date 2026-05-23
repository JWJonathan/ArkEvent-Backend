from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SurveyViewSet, SurveyQuestionViewSet, SurveyAnswerViewSet

router = DefaultRouter()
router.register(r'surveys', SurveyViewSet)
router.register(r'survey-questions', SurveyQuestionViewSet)
router.register(r'survey-answers', SurveyAnswerViewSet)

urlpatterns = [
    path('', include(router.urls)),
]