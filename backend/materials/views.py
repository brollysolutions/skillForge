from django.http import FileResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from core.api import IsTrainer, AIThrottle
from core.models import audit
from .models import StudyMaterial
from .extraction import extract, normalize, MAX_TEXT


class MaterialSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = StudyMaterial
        fields = ['id', 'course', 'course_title', 'topic', 'title', 'subject', 'description', 'learning_objectives',
                  'important_concepts', 'trainer_instructions', 'notes', 'file', 'original_filename', 'size_bytes',
                  'extracted_text', 'analysis', 'analysis_approved', 'status', 'created_at']
        read_only_fields = ['original_filename', 'size_bytes', 'extracted_text', 'analysis', 'analysis_approved', 'status', 'created_at']

    def validate(self, attrs):
        course = attrs.get('course', getattr(self.instance, 'course', None))
        topic = attrs.get('topic', getattr(self.instance, 'topic', None))
        if not course or course.trainer_id != self.context['request'].user.id:
            raise serializers.ValidationError('Invalid course.')
        if topic and topic.course_id != course.pk:
            raise serializers.ValidationError('Topic must belong to the selected course.')
        if self.instance is None and not attrs.get('file') and not attrs.get('notes', '').strip():
            raise serializers.ValidationError('Upload a document or enter your notes.')
        if len(attrs.get('notes', '')) > MAX_TEXT:
            raise serializers.ValidationError('Notes exceed 120,000 characters.')
        return attrs


class MaterialViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTrainer]
    serializer_class = MaterialSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        qs = StudyMaterial.objects.filter(trainer=self.request.user).select_related('course').order_by('-created_at')
        if self.request.query_params.get('course'):
            qs = qs.filter(course_id=self.request.query_params['course'])
        return qs

    def perform_create(self, serializer):
        file = serializer.validated_data.get('file')
        text = extract(file) if file else normalize(serializer.validated_data['notes'])
        material = serializer.save(trainer=self.request.user, extracted_text=text,
                                   original_filename=file.name if file else '', size_bytes=file.size if file else 0)
        audit(self.request.user, 'material.created', material)

    def perform_update(self, serializer):
        file = serializer.validated_data.get('file')
        updates = {'analysis_approved': False, 'analysis': {}}
        if file:
            updates.update(extracted_text=extract(file), original_filename=file.name, size_bytes=file.size)
        elif 'notes' in serializer.validated_data:
            updates['extracted_text'] = normalize(serializer.validated_data['notes'])
        serializer.save(**updates)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        return self.create(request)

    @action(detail=False, methods=['post'], url_path='text')
    def text(self, request):
        return self.create(request)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        material = self.get_object()
        if not material.file:
            raise serializers.ValidationError('This material has no uploaded file.')
        return FileResponse(material.file.open('rb'), as_attachment=True, filename=material.original_filename)

    @action(detail=True, methods=['post'], throttle_classes=[AIThrottle])
    def analyze(self, request, pk=None):
        from ai_services.workflows import analyze_material
        material = self.get_object()
        material.analysis = analyze_material(request.user, material)
        material.analysis_approved = False
        material.save(update_fields=['analysis', 'analysis_approved', 'updated_at'])
        audit(request.user, 'material.analyzed', material)
        return Response(self.get_serializer(material).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        from ai_services.schemas import MaterialAnalysis
        from pydantic import ValidationError
        material = self.get_object()
        try:
            material.analysis = MaterialAnalysis.model_validate(request.data.get('analysis', material.analysis)).model_dump()
        except ValidationError:
            raise serializers.ValidationError('Provide a valid analysis with summary, topics, concepts, objectives and terminology.')
        material.analysis_approved = True
        material.save()
        audit(request.user, 'material.approved', material)
        return Response(self.get_serializer(material).data)
