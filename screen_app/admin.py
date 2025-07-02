# admin.py - Enhanced with Database BOM Management

from django.contrib import admin
from django.utils.html import format_html
from django import forms
from django.db import models
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import (
    Product, AssemblyStage, AssemblyProcess, BillOfMaterial, 
    ProductMedia, Station, AssemblySession,
    # New models
    BOMItem, BOMTemplate, BOMTemplateItem
)

# BOM Item Management
@admin.register(BOMItem)
class BOMItemAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'item_description', 'part_number', 'unit_of_measure', 'cost_per_unit', 'item_photo_preview', 'is_active')
    list_filter = ('unit_of_measure', 'is_active', 'supplier')
    search_fields = ('item_code', 'item_description', 'part_number')
    list_editable = ('is_active', 'cost_per_unit')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('item_code', 'item_description', 'part_number', 'unit_of_measure')
        }),
        ('Visual', {
            'fields': ('item_photo',),
            'description': 'Upload clear photos of items for BOM display'
        }),
        ('Additional Details', {
            'fields': ('supplier', 'cost_per_unit', 'weight_per_unit'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def item_photo_preview(self, obj):
        if obj.item_photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;"/>',
                obj.item_photo.url
            )
        return "No photo"
    item_photo_preview.short_description = 'Photo'

# BOM Template Item Inline
class BOMTemplateItemInline(admin.TabularInline):
    model = BOMTemplateItem
    extra = 1
    fields = ['serial_number', 'item', 'base_quantity', 'notes', 'is_active']
    ordering = ['serial_number']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "item":
            kwargs["queryset"] = BOMItem.objects.filter(is_active=True).order_by('item_description')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

# BOM Template Management
@admin.register(BOMTemplate)
class BOMTemplateAdmin(admin.ModelAdmin):
    list_display = ('template_name', 'product', 'bom_type', 'stage', 'item_count', 'display_assignment', 'is_active')
    list_filter = ('product', 'bom_type', 'stage', 'is_active')
    search_fields = ('template_name', 'product__code', 'product__name')
    list_editable = ('is_active',)
    inlines = [BOMTemplateItemInline]
    
    fieldsets = (
        ('Template Information', {
            'fields': ('template_name', 'product', 'bom_type', 'stage', 'description')
        }),
        ('Display Assignment', {
            'fields': ('display_screen_1', 'display_screen_2', 'display_screen_3'),
            'description': 'Select which displays should show this BOM'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def item_count(self, obj):
        return obj.bom_items.filter(is_active=True).count()
    item_count.short_description = 'Items'
    
    def display_assignment(self, obj):
        displays = []
        if obj.display_screen_1: displays.append('D1')
        if obj.display_screen_2: displays.append('D2')
        if obj.display_screen_3: displays.append('D3')
        
        if displays:
            display_badges = []
            colors = ['red', 'blue', 'green']
            for i, display in enumerate(displays):
                color = colors[i] if i < len(colors) else 'gray'
                display_badges.append(f'<span style="background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; margin: 1px;">{display}</span>')
            return format_html(' '.join(display_badges))
        return format_html('<span style="color: gray;">None</span>')
    display_assignment.short_description = 'Displays'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/preview-bom/', self.admin_site.admin_view(self.preview_bom_view), name='bomtemplate_preview'),
        ]
        return custom_urls + urls
    
    def preview_bom_view(self, request, object_id):
        """Preview BOM for different quantities"""
        template = self.get_object(request, object_id)
        quantity = int(request.GET.get('quantity', 1))
        
        bom_data = template.generate_bom_for_quantity(quantity)
        
        context = {
            'template': template,
            'quantity': quantity,
            'bom_data': bom_data,
            'title': f'BOM Preview - {template.template_name}',
        }
        
        return render(request, 'admin/bom_preview.html', context)

# Enhanced BOM Template Item Admin
@admin.register(BOMTemplateItem)
class BOMTemplateItemAdmin(admin.ModelAdmin):
    list_display = ('bom_template', 'serial_number', 'item', 'base_quantity', 'formatted_quantity_50', 'is_active')
    list_filter = ('bom_template__product', 'bom_template__bom_type', 'is_active')
    search_fields = ('item__item_description', 'bom_template__template_name')
    ordering = ['bom_template', 'serial_number']
    
    fieldsets = (
        ('BOM Line Information', {
            'fields': ('bom_template', 'serial_number', 'item', 'base_quantity')
        }),
        ('Additional Details', {
            'fields': ('notes', 'is_active')
        }),
    )
    
    def formatted_quantity_50(self, obj):
        """Show what quantity would be for 50 units"""
        calc_qty = obj.calculate_quantity_for_production(50)
        if obj.item.unit_of_measure in ['KGS', 'GM', 'LTR']:
            return f"{calc_qty:.3f} {obj.item.unit_of_measure}"
        else:
            return f"{int(calc_qty)} {obj.item.unit_of_measure}"
    formatted_quantity_50.short_description = 'Qty for 50 Units'

# Enhanced existing admins
@admin.register(AssemblyStage)
class AssemblyStageAdmin(admin.ModelAdmin):
    list_display = ('order', 'name', 'display_name', 'process_count', 'bom_template_count')
    list_editable = ('display_name',)
    ordering = ('order',)
    
    def process_count(self, obj):
        return obj.processes.count()
    process_count.short_description = 'Processes'
    
    def bom_template_count(self, obj):
        return obj.bom_templates.count()
    bom_template_count.short_description = 'BOM Templates'

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
    list_display = ('product', 'bom_type', 'stage', 'source_type', 'file_or_template', 'preview_link')
    list_filter = ('bom_type', 'stage', 'product', 'source_type')
    search_fields = ('product__code', 'product__name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('product', 'bom_type', 'stage', 'source_type')
        }),
        ('PDF Source (Legacy)', {
            'fields': ('file',),
            'classes': ('collapse',),
            'description': 'Use for PDF-based BOMs'
        }),
        ('Database Source (Recommended)', {
            'fields': ('bom_template',),
            'description': 'Link to database BOM template for dynamic quantity calculation'
        }),
    )
    
    def file_or_template(self, obj):
        if obj.source_type == 'PDF' and obj.file:
            return format_html('<a href="{}" target="_blank">📄 PDF File</a>', obj.file.url)
        elif obj.source_type == 'DATABASE' and obj.bom_template:
            return format_html('📊 {}', obj.bom_template.template_name)
        return "Not configured"
    file_or_template.short_description = 'Source'
    
    def preview_link(self, obj):
        if obj.source_type == 'DATABASE' and obj.bom_template:
            return format_html(
                '<a href="{}?quantity=1" target="_blank">Preview 1x</a> | '
                '<a href="{}?quantity=50" target="_blank">Preview 50x</a>',
                f'/admin/screen_app/bomtemplate/{obj.bom_template.id}/preview-bom/',
                f'/admin/screen_app/bomtemplate/{obj.bom_template.id}/preview-bom/'
            )
        return "N/A"
    preview_link.short_description = 'Preview'

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
    list_display = ('code', 'name', 'media_count', 'bom_count', 'bom_template_count')
    search_fields = ('code', 'name')
    inlines = [ProductMediaInline]

    def media_count(self, obj):
        return obj.media.count()
    media_count.short_description = 'Media Files'
    
    def bom_count(self, obj):
        return obj.boms.count()
    bom_count.short_description = 'BOMs'
    
    def bom_template_count(self, obj):
        return obj.bom_templates.count()
    bom_template_count.short_description = 'BOM Templates'

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
                   'product_quantity', 'display_status', 'clicker_status', 'bom_data_available')
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
    
    def bom_data_available(self, obj):
        bom_data = obj.get_current_bom_data()
        if bom_data:
            return format_html('<span style="color: green;">✓ {} items</span>', len(bom_data))
        return format_html('<span style="color: orange;">⚠ No BOM data</span>')
    bom_data_available.short_description = 'BOM Data'

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        station = self.get_object(request, object_id)
        if station:
            # Show current media for this display
            current_media = station.get_current_media()
            extra_context['current_media'] = current_media
            extra_context['next_process'] = station.get_next_process()
            extra_context['previous_process'] = station.get_previous_process()
            
            # Show BOM data
            bom_data = station.get_current_bom_data()
            extra_context['current_bom_data'] = bom_data
            
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

@admin.action(description='Clone BOM template with items')
def clone_bom_template(modeladmin, request, queryset):
    for template in queryset:
        # Create new template
        new_template = BOMTemplate.objects.create(
            product=template.product,
            bom_type=template.bom_type,
            stage=template.stage,
            template_name=f"{template.template_name} (Copy)",
            description=f"Copy of {template.template_name}",
            display_screen_1=template.display_screen_1,
            display_screen_2=template.display_screen_2,
            display_screen_3=template.display_screen_3,
            is_active=False  # Set as inactive by default
        )
        
        # Copy all items
        for item in template.bom_items.all():
            BOMTemplateItem.objects.create(
                bom_template=new_template,
                item=item.item,
                base_quantity=item.base_quantity,
                serial_number=item.serial_number,
                notes=item.notes,
                is_active=item.is_active
            )
    
    messages.success(request, f'Successfully cloned {queryset.count()} BOM template(s)')

StationAdmin.actions = [enable_loop_mode, disable_loop_mode]
BOMTemplateAdmin.actions = [clone_bom_template]

# Custom admin site title
admin.site.site_header = "BRG Assembly Management System"
admin.site.site_title = "BRG Assembly Admin"
admin.site.index_title = "Welcome to BRG Assembly Management"