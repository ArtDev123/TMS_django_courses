from django.urls import path
from . import views

urlpatterns = [
    path('mine/', views.ManageCourseListView.as_view(), name='manage_course_list'),
    path('create/', views.CourseCreateView.as_view(), name='course_create'),
    path('<pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('<pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    path('<pk>/modules/', views.CourseModuleUpdateView.as_view(),
         name='course_module_update'),
    path('module/<module_id>/content/<model_name>/',
         views.ContentCreateUpdateView.as_view(), name='module_content_create'),
    path('module/<module_id>/content/<model_name>/<id>/',
         views.ContentCreateUpdateView.as_view(), name='module_content_update'),
    path('module/order/', views.ModuleOrderView.as_view(), name='module_order'),
    path('content/order/', views.ContentOrderView.as_view(), name='content_order'),
    path('module/<int:module_id>/content/quiz/<int:quiz_id>/questions/',
         views.QuizManageView.as_view(), name='quiz_manage'),
    path(
        'module/<int:module_id>/content/quiz/<int:quiz_id>/questions/create/',
        views.QuestionCreateUpdateView.as_view(),
        name='question_create',
    ),
    path(
        'module/<int:module_id>/content/quiz/<int:quiz_id>/questions/<int:question_id>/',
        views.QuestionCreateUpdateView.as_view(),
        name='question_update',
    ),
    path(
        'module/<int:module_id>/content/quiz/<int:quiz_id>/questions/<int:question_id>/delete/',
        views.QuestionDeleteView.as_view(),
        name='question_delete',
    ),
]