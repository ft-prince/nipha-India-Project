# urls.py - Complete fixed version

from django.urls import path
from . import views

urlpatterns = [
    # Basic media endpoints
    path('<int:station_id>/media/', views.get_station_media, name='station_media'),
    path('<int:station_id>/slider/', views.station_media_slider_enhanced, name='station_media_slider'),
    path('<int:station_id>/stream/', views.station_media_stream, name='station_media_stream'),
    path('<int:station_id>/debug-bom/', views.debug_bom_stage, name='debug_bom_stage'),
    # MISSING: Enhanced media endpoint with BOM integration
    path('<int:station_id>/media-with-bom/', views.get_station_media_with_bom, name='station_media_with_bom'),
    path('<int:station_id>/bom-render/', views.render_bom_for_slider, name='render_bom_for_slider'),
    # Add this URL pattern to your urls.py:
path('<int:station_id>/bom-settings/', views.update_bom_settings, name='update_bom_settings'),
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
    
    # Debug endpoints
    path('<int:station_id>/debug/', views.debug_station, name='debug_station'),
    path('<int:station_id>/stream-debug/', views.station_media_stream_debug, name='station_stream_debug'),

    # Direct HTML pages
    path('supervisor-dashboard.html', views.supervisor_dashboard, name='supervisor_dashboard'),
    path('workflow-guide.html', views.workflow_guide, name='workflow_guide'),
    path('hindi.html', views.workflow_guide2, name='hindi'),
    
    # Database BOM endpoints
    path('api/station/<int:station_id>/bom-data/', views.get_station_bom_data, name='station_bom_data'),
    path('api/station/<int:station_id>/bom-settings/', views.update_bom_settings, name='update_bom_settings'),
    path('<int:station_id>/bom-display/', views.render_bom_display, name='bom_display'),
    
    # BOM management endpoints
    path('api/bom-templates/', views.get_bom_templates, name='bom_templates'),
    path('api/bom-template/<int:template_id>/preview/', views.preview_bom_template, name='preview_bom_template'),
    path('api/bom-items/', views.get_bom_items, name='bom_items'),
    path('api/bom-item/quick-add/', views.quick_add_bom_item, name='quick_add_bom_item'),
    path('api/bom-items/bulk-update/', views.bulk_update_bom_items, name='bulk_update_bom_items'),
    path('api/bom-items/export-csv/', views.export_all_bom_items_csv, name='export_all_bom_items_csv'),
    
    # Enhanced streaming
    path('<int:station_id>/stream-enhanced/', views.station_media_stream_enhanced, name='station_stream_enhanced'),
    
    # Management dashboard
    path('bom-management/', views.bom_management_dashboard, name='bom_management_dashboard'),
    path('bom-items/', views.bom_item_management, name='bom_item_management'),
    path('bom-templates/', views.bom_template_management, name='bom_template_management'),
    
    # Export
    path('api/bom-template/<int:template_id>/export-csv/', views.export_bom_csv, name='export_bom_csv'),
]