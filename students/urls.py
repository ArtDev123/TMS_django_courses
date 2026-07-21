from django.urls import path

from . import views

urlpatterns = [
    path('register/', views.StudentRegistrationView.as_view(),
         name='student_registration'),
    path('enroll-course/', views.StudentEnrollCourseView.as_view(),
         name='student_enroll_course'),
    path('courses/', views.StudentCourseListView.as_view(),
         name='student_course_list'),
    path('course/<int:pk>/', views.StudentCourseDetailView.as_view(),
         name='student_course_detail'),
    path('course/<int:pk>/module/<int:module_id>/',
         views.StudentCourseDetailView.as_view(),
         name='student_course_detail_module'),
    path('course/<int:pk>/module/<int:module_id>/complete/',
         views.ModuleCompleteView.as_view(), name='module_complete'),
    path('course/<int:pk>/quiz/<int:quiz_id>/',
         views.QuizTakeView.as_view(), name='quiz_take'),
    path('course/<int:pk>/quiz/<int:quiz_id>/result/',
         views.QuizResultView.as_view(), name='quiz_result'),
    path('certificate/<uuid:code>/',
         views.CertificateDetailView.as_view(), name='certificate_detail'),
    path('profile/', views.StudentProfileView.as_view(),
         name='student_profile'),
]