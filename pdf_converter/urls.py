from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('process-folder/', views.process_folder, name='process_folder'),
    path('job-status/<int:job_id>', views.get_job_status, name='get_job_status'),
    path('download-csv/<int:file_id>', views.download_csv, name='download_csv'),
]
