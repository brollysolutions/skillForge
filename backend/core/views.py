import os
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .api import IsTrainer
from .models import Notification, PlatformSettings, AIUsageLog, audit


class HealthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({'status':'ok', 'service':'SkillForge AI'})


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id','title','message','link','read','created_at']


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        item = self.get_object()
        item.read = True
        item.save(update_fields=['read'])
        return Response(self.get_serializer(item).data)


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSettings
        fields = ['organization_name','leaderboard_enabled','recommendations_enabled']


class SettingsView(APIView):
    permission_classes = [IsTrainer]

    def get(self, request):
        from code_execution.service import execution_configured, execution_provider
        settings, _ = PlatformSettings.objects.get_or_create(trainer=request.user)
        return Response({**SettingsSerializer(settings).data, 'integrations': {
            'groq': bool(os.getenv('GROQ_API_KEY')), 'gemini': bool(os.getenv('GEMINI_API_KEY')),
            'code_execution': execution_configured()},
            'execution_provider': execution_provider(),
            'ai_usage': list(AIUsageLog.objects.filter(actor=request.user).order_by('-created_at').values('provider','operation','status','error_type','duration_ms','created_at')[:20])})

    def patch(self, request):
        settings, _ = PlatformSettings.objects.get_or_create(trainer=request.user)
        serializer = SettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit(request.user, 'settings.updated', settings)
        return Response(serializer.data)
