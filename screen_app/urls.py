from django.urls import path
from . import views

urlpatterns = [
    # Basic media endpoints
    path('<int:station_id>/media/', views.get_station_media, name='station_media'),
    path('<int:station_id>/slider/', views.station_media_slider, name='station_media_slider'),
    path('<int:station_id>/stream/', views.station_media_stream, name='station_media_stream'),
    
    # File streaming
    path('stream/video/<path:video_path>/', views.stream_video, name='stream_video'),
    path('stream/pdf/<path:pdf_path>/', views.stream_pdf, name='stream_pdf'),
    
    # BRG Assembly management endpoints
    path('<int:station_id>/clicker/', views.clicker_action, name='clicker_action'),
    path('<int:station_id>/assembly/config/', views.update_assembly_config, name='update_assembly_config'),
    path('<int:station_id>/assembly/options/', views.get_assembly_options, name='assembly_options'),
    path('<int:station_id>/boms/', views.get_bom_files, name='get_bom_files'),
    
    # Workflow management
    path('workflow/status/', views.get_workflow_status, name='workflow_status'),
    path('workflow/sync/', views.sync_all_displays, name='sync_all_displays'),
    
    # debug
    path('<int:station_id>/debug/', views.debug_station, name='debug_station'),
   path('<int:station_id>/stream-debug/', views.station_media_stream_debug, name='station_stream_debug'),


#  direct html
    path('supervisor-dashboard.html', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('workflow-guide.html', views.workflow_guide, name='workflow_guide'),
    path('hindi.html', views.workflow_guide2, name='hindi'),

]