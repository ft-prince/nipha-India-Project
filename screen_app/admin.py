from django.contrib import admin
from django.utils.html import format_html
from django import forms
from .models import (Product, AssemblyStage, AssemblyProcess, BillOfMaterial, 
                    ProductMedia, Station, AssemblySession)

@admin.register(AssemblyStage)
class AssemblyStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'display_name', 'process_count')
    list_editable = ('display_name',)
    ordering = ('order',)
    
    def process_count(self, obj):
        return obj.processes.count()
    process_count.short_description = 'Processes'

class AssemblyProcessInline(admin.TabularInline):
    model = AssemblyProcess
    extra = 1
    fields = ['name', 'display_name', 'location', 'order', 'is_looped', 'loop_group']

@admin.register(AssemblyProcess)
class AssemblyProcessAdmin(admin.ModelAdmin):
    list_display = ('stage', 'order', 'name', 'location', 'is_looped', 'loop_group')
    list_filter = ('stage', 'location', 'is_looped')
    list_editable = ('order', 'name', 'location', 'is_looped', 'loop_group')
    ordering = ('stage__order', 'order')

@admin.register(BillOfMaterial)
class BillOfMaterialAdmin(admin.ModelAdmin):
    list_display = ('product', 'bom_type', 'stage', 'file')
    list_filter = ('bom_type', 'stage', 'product')
    search_fields = ('product__code', 'product__name')

class ProductMediaInline(admin.TabularInline):
    model = ProductMedia
    extra = 1
    fields = ['media_type', 'file', 'file_preview', 'duration', 'process', 'bom', 
             'display_screen_1', 'display_screen_2', 'display_screen_3']
    readonly_fields = ['file_preview']

    def file_preview(self, obj):
        if obj.file:
            file_url = obj.file.url
            file_name = obj.file.name.lower()
            if file_name.endswith('.pdf'):
                return format_html('<a href="{}" target="_blank">📄 View PDF</a>', file_url)
            elif file_name.endswith(('.mp4', '.mov')):
                return format_html('<video width="100" height="60" controls><source src="{}" type="video/mp4"></video>', file_url)
            elif file_name.endswith(('.xlsx', '.docx')):
                return format_html('<a href="{}" target="_blank">📊 Download</a>', file_url)
            else:
                return format_html('<a href="{}">📁 View File</a>', file_url)
        return "No file"
    file_preview.short_description = 'Preview'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'media_count', 'bom_count')
    search_fields = ('code', 'name')
    inlines = [ProductMediaInline]

    def media_count(self, obj):
        return obj.media.count()
    media_count.short_description = 'Media Files'
    
    def bom_count(self, obj):
        return obj.boms.count()
    bom_count.short_description = 'BOMs'

@admin.register(ProductMedia)
class ProductMediaAdmin(admin.ModelAdmin):
    list_display = ['product', 'media_type', 'process', 'bom', 'file_preview', 'display_assignment', 'duration']
    list_filter = ['media_type', 'product', 'process__stage', 'display_screen_1', 'display_screen_2', 'display_screen_3']
    search_fields = ['product__code', 'product__name', 'file']
    readonly_fields = ['file_preview']

    def file_preview(self, obj):
        if obj.file:
            file_url = obj.file.url
            file_name = obj.file.name.lower()
            if file_name.endswith('.pdf'):
                return format_html('<a href="{}" target="_blank">📄 PDF</a>', file_url)
            elif file_name.endswith(('.mp4', '.mov')):
                return format_html('<video width="100" height="60" controls><source src="{}" type="video/mp4"></video>', file_url)
            else:
                return format_html('<a href="{}">📁 File</a>', file_url)
        return "No file"
    file_preview.short_description = 'Preview'
    
    def display_assignment(self, obj):
        displays = obj.get_assigned_displays()
        if displays:
            display_badges = []
            for display in displays:
                color = ['red', 'blue', 'green'][display-1]
                display_badges.append(f'<span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; margin: 1px;">D{display}</span>')
            return format_html(' '.join(display_badges))
        return format_html('<span style="color: gray;">None</span>')
    display_assignment.short_description = 'Displays'

class StationAdminForm(forms.ModelForm):
    class Meta:
        model = Station
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.current_product:
            # Filter current_stage and current_process based on selected product
            self.fields['current_stage'].queryset = AssemblyStage.objects.all()
            if self.instance.current_stage:
                self.fields['current_process'].queryset = self.instance.current_stage.processes.all()
            else:
                self.fields['current_process'].queryset = AssemblyProcess.objects.none()

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    form = StationAdminForm
    list_display = ('name', 'display_number', 'current_product', 'current_stage', 'current_process', 
                   'product_quantity', 'display_status', 'clicker_status')
    list_filter = ('display_number', 'clicker_enabled', 'loop_mode', 'current_stage')
    search_fields = ('name',)
    
    fieldsets = (
        ('Display Configuration', {
            'fields': ('name', 'display_number', 'manager', 'products')
        }),
        ('Current Assembly State', {
            'fields': ('current_product', 'current_stage', 'current_process', 'product_quantity'),
            'description': 'Set the current assembly status'
        }),
        ('BOM Display Settings', {
            'fields': ('show_single_unit_bom', 'show_batch_bom'),
            'description': 'Choose which BOMs to display'
        }),
        ('Control Settings', {
            'fields': ('clicker_enabled', 'auto_advance', 'loop_mode'),
            'description': 'Control and automation settings'
        }),
    )
    
    def display_status(self, obj):
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        color = colors[obj.display_number - 1] if obj.display_number <= 3 else '#666'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">Display {}</span>',
            color, obj.display_number
        )
    display_status.short_description = 'Display'
    
    def clicker_status(self, obj):
        if obj.clicker_enabled:
            loop_text = " 🔄" if obj.loop_mode else ""
            return format_html('<span style="color: green;">✓ Enabled{}</span>', loop_text)
        return format_html('<span style="color: red;">✗ Disabled</span>')
    clicker_status.short_description = 'Clicker'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        station = self.get_object(request, object_id)
        if station:
            # Show current media for this display
            current_media = station.get_current_media()
            extra_context['current_media'] = current_media
            extra_context['next_process'] = station.get_next_process()
            extra_context['previous_process'] = station.get_previous_process()
            
            # Show workflow information
            if station.current_product:
                workflow_info = {
                    'stages': AssemblyStage.objects.all().order_by('order'),
                    'current_stage_processes': station.current_stage.processes.all() if station.current_stage else None,
                }
                extra_context['workflow_info'] = workflow_info
                
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(AssemblySession)
class AssemblySessionAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'current_stage', 'current_process', 'start_time', 
                   'completed', 'display_stations')
    list_filter = ('completed', 'product', 'current_stage', 'start_time')
    readonly_fields = ('start_time',)
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Session Info', {
            'fields': ('product', 'quantity', 'start_time', 'end_time', 'completed')
        }),
        ('Current Status', {
            'fields': ('current_stage', 'current_process')
        }),
        ('Display Stations', {
            'fields': ('display_1_station', 'display_2_station', 'display_3_station'),
            'description': 'Stations assigned to each display for this session'
        }),
    )
    
    def display_stations(self, obj):
        stations = []
        if obj.display_1_station:
            stations.append(f'D1: {obj.display_1_station.name}')
        if obj.display_2_station:
            stations.append(f'D2: {obj.display_2_station.name}')
        if obj.display_3_station:
            stations.append(f'D3: {obj.display_3_station.name}')
        return ' | '.join(stations) if stations else 'No stations assigned'
    display_stations.short_description = 'Assigned Stations'

# Custom admin actions
@admin.action(description='Enable loop mode for selected stations')
def enable_loop_mode(modeladmin, request, queryset):
    queryset.update(loop_mode=True)

@admin.action(description='Disable loop mode for selected stations')
def disable_loop_mode(modeladmin, request, queryset):
    queryset.update(loop_mode=False)

StationAdmin.actions = [enable_loop_mode, disable_loop_mode]