from rest_framework import viewsets
from .models import Profile
from .serializers import ProfileSerializer

class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    def get_object(self):
        if self.kwargs.get('pk') == 'me':
            return Profile.objects.get(id=self.request.user.id)
        return super().get_object()
