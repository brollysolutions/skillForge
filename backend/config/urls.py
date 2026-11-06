from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import LoginView, ProfileView, LogoutView, StudentViewSet, StaffViewSet, AccessRefreshView
from courses.views import CourseViewSet, TopicViewSet, BatchViewSet
from materials.views import MaterialViewSet
from assignments.views import AssignmentViewSet
from submissions.views import SubmissionViewSet
from ai_services.views import GenerateAssignmentView, RegenerateQuestionView
from code_execution.views import RunCodeView
from reports.views import ReportViewSet, GenerateReportView, LearningPathView, BatchReportView, BatchReportDownloadView
from analytics.views import DashboardView, AdminDashboardView, ScopedAnalyticsView, ExportAnalyticsView, LeaderboardView
from core.views import HealthView, NotificationViewSet, SettingsView

router = DefaultRouter()
router.register('admin/students', StudentViewSet, basename='students')
router.register('staff', StaffViewSet, basename='staff')
router.register('batches', BatchViewSet, basename='batches')
router.register('courses', CourseViewSet, basename='courses')
router.register('topics', TopicViewSet, basename='topics')
router.register('materials', MaterialViewSet, basename='materials')
router.register('assignments', AssignmentViewSet, basename='assignments')
router.register('submissions', SubmissionViewSet, basename='submissions')
router.register('reports', ReportViewSet, basename='reports')
router.register('notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/health/', HealthView.as_view()),
    path('api/auth/login/', LoginView.as_view()),
    path('api/auth/token/refresh/', AccessRefreshView.as_view()),
    path('api/auth/logout/', LogoutView.as_view()),
    path('api/auth/profile/', ProfileView.as_view()),
    path('api/admin/dashboard/', AdminDashboardView.as_view()),
    path('api/student/dashboard/', DashboardView.as_view()),
    path('api/student/performance/', DashboardView.as_view()),
    path('api/student/assignments/', AssignmentViewSet.as_view({'get':'list'})),
    path('api/student/submissions/', SubmissionViewSet.as_view({'get':'list'})),
    path('api/student/reports/', ReportViewSet.as_view({'get':'list'})),
    path('api/student/learning-path/', LearningPathView.as_view()),
    path('api/ai/generate-assignment/', GenerateAssignmentView.as_view()),
    path('api/ai/assignments/<int:pk>/regenerate-question/', RegenerateQuestionView.as_view()),
    path('api/code/run/', RunCodeView.as_view()),
    path('api/reports/generate/<int:student_id>/', GenerateReportView.as_view()),
    path('api/reports/batch/', BatchReportView.as_view()),
    path('api/reports/batch/<int:pk>/download/', BatchReportDownloadView.as_view()),
    path('api/analytics/overview/', DashboardView.as_view()),
    path('api/analytics/export/', ExportAnalyticsView.as_view()),
    path('api/analytics/<str:kind>/<int:pk>/', ScopedAnalyticsView.as_view()),
    path('api/leaderboard/', LeaderboardView.as_view()),
    path('api/settings/', SettingsView.as_view()),
    path('api/', include(router.urls)),
]
