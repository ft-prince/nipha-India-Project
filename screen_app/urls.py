# urls.py - Complete fixed version

from django.urls import path
from . import views

urlpatterns = [
    
    
    # Basic media endpoints
    path('<int:station_id>/media/', views.get_station_media, name='station_media'),
    path('<int:station_id>/slider/', views.station_media_slider_enhanced, name='station_media_slider'),
    path('<int:station_id>/debug-bom/', views.debug_bom_stage, name='debug_bom_stage'),
    # MISSING: Enhanced media endpoint with BOM integration
    path('<int:station_id>/media-with-bom/', views.get_station_media_with_bom, name='station_media_with_bom'),
    path('<int:station_id>/bom-render/', views.render_bom_for_slider, name='render_bom_for_slider'),
    
    
    
    
    
        path('<int:station_id>/stream/', views.station_media_stream, name='station_media_stream'),

    
    
    
    
    
    
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

    path('<int:station_id>/auto-loop-progress/', views.auto_loop_progress, name='auto_loop_progress'),
    path('<int:station_id>/auto-loop-config/', views.auto_loop_config, name='auto_loop_config'),
    path('auto-loop-status-all/', views.auto_loop_status_all, name='auto_loop_status_all'),
    path('<int:station_id>/debug-sequence/', views.debug_process_sequence, name='debug_process_sequence'),
 
 
 
 
 
 
#  main
 
     path('<int:station_id>/bom-paginated/', views.get_station_bom_data_paginated, name='station_bom_paginated'),
     
     
     
    path('<int:station_id>/media-with-bom-pagination/', views.get_station_media_with_bom_pagination, name='station_media_with_bom_pagination'),
    
    
    
    path('<int:station_id>/bom-pagination-control/', views.bom_pagination_control, name='bom_pagination_control'),
    
    path('<int:station_id>/bom-render-paginated/', views.render_bom_fragment_paginated, name='bom_render_paginated'),

    path('debug/bom/<int:station_id>/', views.debug_bom_template, name='debug_bom_template'),
 
 
 
 
#  

    path('product-info/', views.product_information_view, name='product_information'),
    # Product CRUD URLs
path('product/create/', views.create_product, name='create_product'),
path('product/<int:product_id>/update/', views.update_product, name='update_product'),
path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
path('product/<int:product_id>/', views.get_product_data_api, name='get_product_data'),
    # ==============================================
    # ASSEMBLY STAGE CRUD OPERATIONS (NEW)
    # ==============================================
    path('assembly-stage/create/', views.create_assembly_stage, name='create_assembly_stage'),
    path('assembly-stage/<int:stage_id>/update/', views.update_assembly_stage, name='update_assembly_stage'),
    path('assembly-stage/<int:stage_id>/delete/', views.delete_assembly_stage, name='delete_assembly_stage'),
    path('assembly-stage/<int:stage_id>/', views.get_assembly_stage_data, name='get_assembly_stage_data'),
    
    # ==============================================
    # ASSEMBLY PROCESS CRUD OPERATIONS
    # ==============================================
    path('assembly-process/create/', views.create_assembly_process, name='create_assembly_process'),
    path('assembly-process/<int:process_id>/update/', views.update_assembly_process, name='update_assembly_process'),
    path('assembly-process/<int:process_id>/delete/', views.delete_assembly_process, name='delete_assembly_process'),
    path('assembly-process/<int:process_id>/', views.get_assembly_process_data, name='get_assembly_process_data'),
    
    # ==============================================
    # BOM TEMPLATE CRUD OPERATIONS
    # ==============================================
    path('bom-template/create/', views.create_bom_template, name='create_bom_template'),
    path('bom-template/<int:template_id>/update/', views.update_bom_template, name='update_bom_template'),
    path('bom-template/<int:template_id>/delete/', views.delete_bom_template, name='delete_bom_template'),
    path('bom-template/<int:template_id>/', views.get_bom_template_data, name='get_bom_template_data'),
    path('bom-template/<int:template_id>/next-serial/', views.get_available_serial_numbers, name='get_available_serial_numbers'),
    path('bom-template/<int:template_id>/items/', views.get_bom_template_items, name='get_bom_template_items'),
    
    # ==============================================
    # BOM TEMPLATE ITEM CRUD OPERATIONS
    # ==============================================
    path('bom-item/create/', views.create_bom_template_item, name='create_bom_template_item'),
    path('bom-item/<int:item_id>/update/', views.update_bom_template_item, name='update_bom_template_item'),
    path('bom-item/<int:item_id>/delete/', views.delete_bom_template_item, name='delete_bom_template_item'),
    path('bom-item/<int:item_id>/', views.get_bom_template_item_data, name='get_bom_template_item_data'),
    
    # ==============================================
    # PRODUCT MEDIA CRUD OPERATIONS
    # ==============================================
    path('product-media/create/', views.create_product_media, name='create_product_media'),
    path('product-media/<int:media_id>/update/', views.update_product_media, name='update_product_media'),
    path('product-media/<int:media_id>/delete/', views.delete_product_media, name='delete_product_media'),
    path('product-media/<int:media_id>/', views.get_product_media_data, name='get_product_media_data'),
    
    # ==============================================
    # BULK UPLOAD ENDPOINTS
    # ==============================================
    path('bom-template/<int:template_id>/upload-excel/', views.upload_bom_items_excel, name='upload_bom_items_excel'),
    path('product-media/upload-zip/', views.upload_product_media_zip, name='upload_product_media_zip'),
    
    # ==============================================
    # AJAX HELPER ENDPOINTS
    # ==============================================
    path('ajax/product/<int:product_id>/stages/', views.get_stages_for_product, name='get_stages_for_product'),
    path('ajax/product/<int:product_id>/processes/', views.get_processes_for_product, name='get_processes_for_product'),
    path('ajax/stage/<int:stage_id>/processes/', views.get_processes_for_stage, name='get_processes_for_stage'),



    path('<int:station_id>/trigger-stations-reload/', 
         views.TriggerStationsReloadView.as_view(), 
         name='trigger_stations_reload'),
    
    path('<int:station_id>/check-reload-signal/', 
         views.CheckReloadSignalView.as_view(), 
         name='check_reload_signal'),




    path('<int:station_id>/sync-bom-pagination/', 
         views.sync_bom_pagination, 
         name='sync_bom_pagination'),

    path('<int:station_id>/check-bom-sync/', 
         views.check_bom_sync, 
         name='check_bom_sync'),


]