from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.urls import reverse
import zipfile
import os
from django.core.files.base import ContentFile
import math

class Product(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"



class AssemblyStage(models.Model):
    """Main assembly stages (Sub Assembly 1, Sub Assembly 2, Final Assembly)"""
    STAGE_CHOICES = [
        
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
        ('BOM_DISPLAY', 'BOM_DISPLAY'),
        ('SUB_ASSEMBLY_2', 'Sub Assembly 2'),
        ('SUB_ASSEMBLY_3', 'Sub Assembly 3'),
        ('SUB_ASSEMBLY_4', 'Sub Assembly 4'),
 
        ('FINAL_ASSEMBLY', 'Final Assembly'),
    ]
    product = models.ForeignKey(Product, related_name='assembly_product', on_delete=models.CASCADE,blank=True, null=True)
    name = models.CharField(max_length=500)
    display_name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.display_name 

class AssemblyProcess(models.Model):
    """Individual processes within each stage"""
    LOCATION_CHOICES = [
        ('ASSEMBLY_ROOM', 'Assembly Room'),
        ('OUTSIDE_ASSEMBLY_ROOM', 'Outside Assembly Room'),
    ]
    
    stage = models.ForeignKey(AssemblyStage, related_name='processes', on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=200, blank=True, null=True)
    location = models.CharField(max_length=30, choices=LOCATION_CHOICES, blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    
    # Special properties
    is_looped = models.BooleanField(default=False, help_text="Should loop until manually advanced")
    loop_group = models.CharField(max_length=50, blank=True, null=True, help_text="Group processes that loop together")
    
    class Meta:
        ordering = ['stage__order', 'order']
        unique_together = ['stage', 'order']
    
    def __str__(self):
        return f"{self.stage.display_name} - {self.name}"

# NEW: Database BOM System
class BOMItem(models.Model):
    """Master list of all BOM items"""
    item_code = models.CharField(max_length=50, unique=True, help_text="Internal item code for tracking")
    item_description = models.CharField(max_length=200)
    part_number = models.CharField(max_length=50, help_text="Part number (can be B.O. for bought out)")
    unit_of_measure = models.CharField(max_length=20, default='NO.', help_text="Unit (NO., KGS, GM, etc.)")
    
    # Item photo
    item_photo = models.ImageField(upload_to='bom_items/', blank=True, null=True, help_text="Item photograph")
    
    # Additional details
    supplier = models.CharField(max_length=100, blank=True, null=True)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    weight_per_unit = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True, help_text="Weight in KG")
    
    # Meta information
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['item_description']
    
    def __str__(self):
        return f"{self.item_code} - {self.item_description}"




class BOMTemplate(models.Model):
    """BOM Templates for different products and stages"""
    BOM_TYPE_CHOICES = [
        ('SINGLE_UNIT', 'Single Unit'),
        ('BATCH_50', '50 Units'),
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
        ('SUB_ASSEMBLY_3', 'Sub Assembly 3'),
        ('SUB_ASSEMBLY_4', 'Sub Assembly 4'),
        ('SUB_ASSEMBLY_2', 'Sub Assembly 2'),
        ('FINAL_ASSEMBLY', 'Final Assembly'),
    ]
    
    product = models.ForeignKey(Product, related_name='bom_templates', on_delete=models.CASCADE)
    bom_type = models.CharField(max_length=20, choices=BOM_TYPE_CHOICES)
    stage = models.ForeignKey(AssemblyStage, related_name='bom_templates', on_delete=models.CASCADE, null=True, blank=True)
    
    # Template details
    template_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    
    # duration 
    duration =models.PositiveIntegerField(default=20, blank=True,help_text="Duration in seconds")
    is_duration_active=models.BooleanField(default=False, help_text="Should loop until manually advanced",blank=True)    
    # Display settings
    display_screen_1 = models.BooleanField(default=False, help_text="Show on Display Screen 1")
    display_screen_2 = models.BooleanField(default=False, help_text="Show on Display Screen 2")
    display_screen_3 = models.BooleanField(default=False, help_text="Show on Display Screen 3")
    
    # Metadata
    created_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['product', 'bom_type', 'stage']
        ordering = ['product', 'bom_type']
    
    def __str__(self):
        return f"{self.product.code} - {self.get_bom_type_display()}"
    
    def should_split_across_displays(self):
        """Determine if this BOM should be split across displays"""
        return self.bom_type in ['SINGLE_UNIT', 'BATCH_50']
    
# FIXED: Replace your BOMTemplate.get_items_for_display method with this:

    def get_calculated_items(self, quantity=1):
        """
        Returns BOM items with calculated quantity based on product quantity.
        Assumes BOMItem model has a field like quantity_per_unit.
        """
        items = self.bom_items.filter(is_active=True)  # or whatever related name you use
        calculated = []
        for item in items:
            calculated.append({
                'id': item.id,
                'item_code': item.item_code,
                'item_description': item.item_description,
                'part_number': item.part_number,
                'unit_of_measure': item.unit_of_measure,
                'supplier': item.supplier,
                'cost_per_unit': float(item.cost_per_unit) if item.cost_per_unit else None,
                'weight_per_unit': float(item.weight_per_unit) if item.weight_per_unit else None,
                'item_photo_url': item.item_photo.url if item.item_photo else None,
                'calculated_quantity': item.quantity_per_unit * quantity if hasattr(item, 'quantity_per_unit') else None,
            })
        return calculated

    def get_items_for_display(self, display_number, quantity=1, page=1, items_per_screen=8):
        """Get BOM items specific to a display number with pagination - FIXED WITH STAGE-SPECIFIC PAGINATION"""
        
        if not self.should_split_across_displays():
            # Stage-specific BOMs (SUB_ASSEMBLY_1, SUB_ASSEMBLY_2, FINAL_ASSEMBLY) - pagination on Display 1 only
            if display_number == 1:
                all_items = self.generate_bom_for_quantity(quantity)
                total_items = len(all_items)
                
                # Apply pagination on Display 1 for stage-specific BOMs
                start_idx = (page - 1) * items_per_screen
                end_idx = min(start_idx + items_per_screen, total_items)
                
                if start_idx >= total_items:
                    result = []
                else:
                    result = all_items[start_idx:end_idx]
                
                return result
            else:
                return []
        
        # Split logic for SINGLE_UNIT and BATCH_50 with FIXED 8 items per display per page
        all_items = self.generate_bom_for_quantity(quantity)
        total_items = len(all_items)
        
        
        if total_items == 0:
            return []
        
        # FIXED LOGIC: Always 8 items per display, with pagination
        max_items_per_display = 8
        items_per_page = max_items_per_display * 3  # 8 items × 3 displays = 24 items per page
        
        # Calculate which items belong to this page
        page_start_idx = (page - 1) * items_per_page
        page_end_idx = min(page_start_idx + items_per_page, total_items)
        page_items = all_items[page_start_idx:page_end_idx]
        
        
        if len(page_items) == 0:
            return []
        
        # Calculate which items from this page belong to this display
        display_start_idx = (display_number - 1) * max_items_per_display
        display_end_idx = min(display_start_idx + max_items_per_display, len(page_items))
        
        if display_start_idx >= len(page_items):
            result = []
        else:
            result = page_items[display_start_idx:display_end_idx]
            # Calculate actual item numbers for debugging
            actual_start = page_start_idx + display_start_idx + 1
            actual_end = page_start_idx + display_end_idx        
        return result

    def get_pagination_info_for_split(self, quantity=1, items_per_screen=8):
        """Get pagination information for split BOMs - UPDATED FOR STAGE-SPECIFIC PAGINATION"""
        total_items = len(self.generate_bom_for_quantity(quantity))
        
        if not self.should_split_across_displays():
            # Stage-specific BOMs: pagination on Display 1 only
            total_pages = math.ceil(total_items / items_per_screen) if total_items > 0 else 1
            return {
                'total_pages': total_pages,
                'items_per_page': items_per_screen,  # Items per page on Display 1
                'items_per_screen': items_per_screen,
                'total_items': total_items
            }
        
        # BOM Display BOMs: pagination across 3 displays (8 items each = 24 per page)
        max_items_per_display = 8
        items_per_page = max_items_per_display * 3  # 24 items per page (8 per display)
        
        total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1
        
        return {
            'total_pages': total_pages,
            'items_per_page': items_per_page,
            'items_per_screen': max_items_per_display,
            'total_items': total_items
        }

    def get_display_info_for_split(self, page=1, quantity=1):
        """Get information about how items are distributed across displays for a specific page"""
        if not self.should_split_across_displays():
            return None
        
        all_items = self.generate_bom_for_quantity(quantity)
        total_items = len(all_items)
        
        max_items_per_display = 8
        items_per_page = max_items_per_display * 3  # 24 items per page
        
        # Calculate which items belong to this page
        page_start_idx = (page - 1) * items_per_page
        page_end_idx = min(page_start_idx + items_per_page, total_items)
        page_items_count = page_end_idx - page_start_idx
        
        distribution = {}
        
        for display in [1, 2, 3]:
            display_start_idx = (display - 1) * max_items_per_display
            display_end_idx = min(display_start_idx + max_items_per_display, page_items_count)
            
            if display_start_idx < page_items_count:
                item_count = display_end_idx - display_start_idx
                # Calculate actual serial numbers
                actual_start_serial = page_start_idx + display_start_idx + 1
                actual_end_serial = page_start_idx + display_end_idx
                
                distribution[f'display_{display}'] = {
                    'start_serial': actual_start_serial,
                    'end_serial': actual_end_serial,
                    'item_count': item_count
                }
            else:
                distribution[f'display_{display}'] = {
                    'start_serial': 0,
                    'end_serial': 0,
                    'item_count': 0
                }
        
        return distribution

    def generate_bom_for_quantity(self, quantity=1):
        """Generate BOM items with calculated quantities"""
        bom_items = []
        
        # FIXED: For stage-specific BOMs, always use quantity = 1 (don't multiply)
        stage_specific_bom_types = ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'SUB_ASSEMBLY_3','SUB_ASSEMBLY_4','FINAL_ASSEMBLY']
        
        if self.bom_type in stage_specific_bom_types:
            # For stage-specific BOMs, always use base quantity (no multiplication)
            effective_quantity = 1
        else:
            # For unit-based BOMs (SINGLE_UNIT, BATCH_50), use the provided quantity
            effective_quantity = quantity
        
        for item_line in self.bom_items.filter(is_active=True).order_by('serial_number'):
            calculated_qty = item_line.base_quantity * effective_quantity
            
            # Handle different unit types
            if item_line.item.unit_of_measure in ['KGS', 'GM', 'LTR']:
                # For weight/volume, keep decimal precision
                formatted_qty = f"{calculated_qty:.3f} {item_line.item.unit_of_measure}"
            else:
                # For count items, show as integer
                formatted_qty = f"{int(calculated_qty)} {item_line.item.unit_of_measure}"
            
            bom_items.append({
                'serial_number': item_line.serial_number,
                'item': item_line.item,
                'base_quantity': item_line.base_quantity,
                'calculated_quantity': calculated_qty,
                'formatted_quantity': formatted_qty,
                'notes': item_line.notes
            })
        
        return bom_items
    
    
    
    
class BOMTemplateItem(models.Model):
    """Items within a BOM template"""
    bom_template = models.ForeignKey(BOMTemplate, related_name='bom_items', on_delete=models.CASCADE)
    item = models.ForeignKey(BOMItem, on_delete=models.CASCADE)
    
    # Quantity for single unit (will be multiplied based on production quantity)
    base_quantity = models.DecimalField(max_digits=10, default=1,decimal_places=4, help_text="Quantity for single unit")
    
    # BOM line details
    serial_number = models.PositiveIntegerField(help_text="S.NO in BOM")
    notes = models.TextField(blank=True, null=True, help_text="Special instructions or notes")
    
    # Status
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['bom_template', 'serial_number']
        ordering = ['serial_number']
    
    def __str__(self):
        return f"{self.bom_template} - {self.serial_number:02d} - {self.item.item_description}"
    
    def calculate_quantity_for_production(self, production_quantity=1):
        """Calculate quantity needed for given production quantity"""
        return self.base_quantity * production_quantity




class BillOfMaterial(models.Model):
    """Bill of Materials - supports both PDF files and database templates"""
    BOM_TYPE_CHOICES = [
        ('SINGLE_UNIT', 'Single Unit'),
        ('BATCH_50', '50 Units'),
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
        ('SUB_ASSEMBLY_2', 'Sub Assembly 2'),
        ('SUB_ASSEMBLY_3', 'Sub Assembly 3'),
        ('SUB_ASSEMBLY_4', 'Sub Assembly 4'),
        ('FINAL_ASSEMBLY', 'Final Assembly'),
    ]
    
    BOM_SOURCE_CHOICES = [
        ('PDF', 'PDF File'),
        ('DATABASE', 'Database Template'),
    ]
    
    product = models.ForeignKey(Product, related_name='boms', on_delete=models.CASCADE)
    bom_type = models.CharField(max_length=20, choices=BOM_TYPE_CHOICES)
    stage = models.ForeignKey(AssemblyStage, related_name='boms', on_delete=models.CASCADE, null=True, blank=True)
    
    # Source type
    source_type = models.CharField(max_length=10, choices=BOM_SOURCE_CHOICES, default='DATABASE')
    
    # For PDF-based BOMs (legacy)
    file = models.FileField(
        upload_to='bom_files/', 
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'xlsx', 'docx'])],
        blank=True, null=True
    )
    
    # For database-based BOMs
    bom_template = models.ForeignKey(BOMTemplate, on_delete=models.CASCADE, blank=True, null=True)
    
    def __str__(self):
        return f"{self.product.code} - {self.get_bom_type_display()}"
    
    def get_bom_data_for_quantity(self, quantity=1):
        """Get BOM data for specified quantity"""
        if self.source_type == 'DATABASE' and self.bom_template:
            return self.bom_template.generate_bom_for_quantity(quantity)
        else:
            # For PDF-based BOMs, return file path
            return None

class ProductMedia(models.Model):
    """Media files for products and processes"""
    MEDIA_TYPE_CHOICES = [
        ('BOM', 'Bill of Material'),
        ('PROCESS_DOC', 'Process Document'),
        ('VIDEO', 'Video'),
        ('INSTRUCTION', 'Instruction Manual'),
    ]
    
    product = models.ForeignKey(Product, related_name='media', on_delete=models.CASCADE)
    process = models.ForeignKey(AssemblyProcess, related_name='media', on_delete=models.CASCADE, null=True, blank=True)
    bom = models.ForeignKey(BillOfMaterial, related_name='media', on_delete=models.CASCADE, null=True, blank=True)
    
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='PROCESS_DOC')
    file = models.FileField(
        upload_to='product_media/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'mp4', 'mov', 'xlsx', 'docx'])],
        blank=True, null=True  # Made optional for database BOMs
    )
    duration = models.PositiveIntegerField(default=15, blank=True, help_text="Duration in seconds (for videos)")
    
    # Display assignment
    display_screen_1 = models.BooleanField(default=False, help_text="Show on Display Screen 1")
    display_screen_2 = models.BooleanField(default=False, help_text="Show on Display Screen 2") 
    display_screen_3 = models.BooleanField(default=False, help_text="Show on Display Screen 3")

    def __str__(self):
        process_info = f" - {self.process.name}" if self.process else ""
        bom_info = f" - {self.bom.get_bom_type_display()}" if self.bom else ""
        return f"{self.product.code}{process_info}{bom_info} - {self.get_media_type_display()}"
    
    def get_assigned_displays(self):
        displays = []
        if self.display_screen_1: displays.append(1)
        if self.display_screen_2: displays.append(2)
        if self.display_screen_3: displays.append(3)
        return displays
  



class Station(models.Model):
    """Assembly stations with multi-display support"""
    DISPLAY_CHOICES = [
        (1, 'Display Screen 1'),
        (2, 'Display Screen 2'),
        (3, 'Display Screen 3'),
    ]
    
    name = models.CharField(max_length=100)
    display_number = models.PositiveIntegerField(choices=DISPLAY_CHOICES, help_text="Which display screen this station represents", blank=True, null=True)
    products = models.ManyToManyField(Product, related_name='stations', blank=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    
    # Current assembly state
    current_product = models.ForeignKey(Product, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    current_stage = models.ForeignKey(AssemblyStage, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    current_process = models.ForeignKey(AssemblyProcess, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    product_quantity = models.PositiveIntegerField(default=50, help_text="Quantity being assembled")
    
    # BOM selection
    show_single_unit_bom = models.BooleanField(default=False, help_text="Show single unit BOM for reference")
    show_batch_bom = models.BooleanField(default=True, help_text="Show batch quantity BOM")
    # ⭐ NEW: BOM Pagination state - shared across all displays of the same product
    current_bom_page = models.PositiveIntegerField(default=1, help_text="Current BOM page number (shared across displays)")
    bom_page_updated_at = models.DateTimeField(auto_now=True, help_text="Last time BOM page was changed")

    # Control settings
    clicker_enabled = models.BooleanField(default=True, help_text="Enable clicker support")
    auto_advance = models.BooleanField(default=False, help_text="Auto advance after media duration")
    loop_mode = models.BooleanField(default=False, help_text="Currently in loop mode (for processes 1A, 1B, 1C)")
    
    class Meta:
        unique_together = ['name', 'display_number']
    
    def __str__(self):
        return f"{self.name} - Display {self.display_number}"
    

    def get_current_bom_data(self, page=1):
        if not self.current_product or not self.display_number:
            return None

        quantity = 1 if self.show_single_unit_bom else self.product_quantity
        bom_type = 'SINGLE_UNIT' if self.show_single_unit_bom else 'BATCH_50' if self.show_batch_bom else None

        # Try stage-specific BOM first
        stage_template = None
        if self.current_stage:
            stage_template = BOMTemplate.objects.filter(
                product=self.current_product,
                stage=self.current_stage,
                is_active=True
            ).first()

        # Fallback to non-stage BOM
        if not stage_template:
            stage_template = BOMTemplate.objects.filter(
                product=self.current_product,
                is_active=True
            ).first()

        # If still nothing, return None
        if not stage_template:
            return None

        return stage_template.get_items_for_display(
            display_number=self.display_number,
            quantity=quantity,
            page=page,
            items_per_screen=8
        )


    def get_current_bom_info(self, page=1):
        if not self.current_product:
            return None

        quantity = 1 if self.show_single_unit_bom else self.product_quantity
        bom_type = 'SINGLE_UNIT' if self.show_single_unit_bom else 'BATCH_50' if self.show_batch_bom else None

        # Try to get stage-specific BOM
        template = None
        if self.current_stage:
            template = BOMTemplate.objects.filter(
                product=self.current_product,
                stage=self.current_stage,
                is_active=True
            ).first()

        # Fallback to any BOM for the product
        if not template:
            template = BOMTemplate.objects.filter(
                product=self.current_product,
                is_active=True
            ).first()

        if not template:
            return None

        # Pagination and split info
        pagination_info = template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
        split_info = template.get_display_info_for_split(page=page, quantity=quantity)
        current_display_info = split_info.get(f'display_{self.display_number}') if split_info else None

        is_split = len(split_info) > 1 if split_info else False

        return {
            'template': template,
            'type': bom_type.lower() if bom_type else 'unknown',
            'display_name': f"{quantity} Units BOM" + (" (Split)" if is_split else ""),
            'quantity': quantity,
            'items_count': current_display_info['item_count'] if current_display_info else 0,
            'is_split': is_split,
            'display_info': (
                f"Page {page} - Items {current_display_info['start_serial']}-{current_display_info['end_serial']}"
                if current_display_info and current_display_info['item_count'] > 0
                else f"Page {page} - No items"
            ),
            'split_info': split_info,
            'pagination_info': pagination_info
        }
  
    def get_bom_pagination_info(self):
        if not self.current_product:
            return None

        quantity = 1 if self.show_single_unit_bom else self.product_quantity
        bom_type = 'SINGLE_UNIT' if self.show_single_unit_bom else 'BATCH_50' if self.show_batch_bom else None

        template = None
        if self.current_stage:
            template = BOMTemplate.objects.filter(
                product=self.current_product,
                stage=self.current_stage,
                is_active=True
            ).first()

        if not template:
            template = BOMTemplate.objects.filter(
                product=self.current_product,
                is_active=True
            ).first()

        if not template:
            return {
                'total_pages': 1,
                'items_per_page': 0,
                'supports_pagination': False
            }

        pagination_info = template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
        pagination_info['supports_pagination'] = True
        return pagination_info


# Replace the get_current_media method in your Station model

    def get_current_media(self):
        """Get media for current state based on display number - UPDATED: No PDF BOMs"""
        if not self.current_product:
            return ProductMedia.objects.none()
        
        # Start with base query
        media_query = ProductMedia.objects.filter(product=self.current_product)
        
        # Filter by display screen
        if self.display_number == 1:
            media_query = media_query.filter(display_screen_1=True)
        elif self.display_number == 2:
            media_query = media_query.filter(display_screen_2=True)
        elif self.display_number == 3:
            media_query = media_query.filter(display_screen_3=True)
        else:
            return ProductMedia.objects.none()
        
        # Filter by current process if set
        if self.current_process:
            process_media = media_query.filter(process=self.current_process)
        else:
            process_media = ProductMedia.objects.none()
        
        # REMOVED: PDF BOM media logic since we're using database BOMs
        # Only return process-specific media (videos, documents, but not BOMs)
        non_bom_media = media_query.exclude(media_type='BOM')
        
        if process_media.exists():
            # Return process-specific media (excluding BOMs)
            return process_media.exclude(media_type='BOM')
        else:
            # Return any non-BOM media for this display
            return non_bom_media
            
    def get_next_process(self):
        """Get next process, handling loops and stage transitions"""
        if not self.current_stage:
            # No current stage, start with first stage of the current product
            if self.current_product:
                first_stage = AssemblyStage.objects.filter(product=self.current_product).order_by('order').first()
                if first_stage:
                    return first_stage.processes.order_by('order').first()
            return None

        # If in loop mode and current process has loop_group, stay in loop
        if self.loop_mode and self.current_process and self.current_process.loop_group:
            loop_processes = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                loop_group=self.current_process.loop_group
            ).order_by('order')

            if loop_processes.exists():
                process_list = list(loop_processes)
                try:
                    current_index = process_list.index(self.current_process)
                    next_index = (current_index + 1) % len(process_list)
                    return process_list[next_index]
                except ValueError:
                    # Current process not in loop, return first loop process
                    return process_list[0]

        # Normal next process logic
        if self.current_process:
            # Look for next process in current stage
            next_process = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                order__gt=self.current_process.order
            ).order_by('order').first()

            if next_process:
                return next_process
            else:
                # Move to next stage of the current product
                next_stage = AssemblyStage.objects.filter(
                    product=self.current_product,
                    order__gt=self.current_stage.order
                ).order_by('order').first()
                if next_stage:
                    return next_stage.processes.order_by('order').first()
        else:
            # No current process, return first process of current stage
            return self.current_stage.processes.order_by('order').first()

        return None

    
    
    def get_previous_process(self):
        """Get previous process, handling loops and stage transitions"""
        if not self.current_process:
            return None

        # If in loop mode and current process has loop_group, navigate within loop
        if self.loop_mode and self.current_process.loop_group:
            loop_processes = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                loop_group=self.current_process.loop_group
            ).order_by('order')

            if loop_processes.exists():
                process_list = list(loop_processes)
                try:
                    current_index = process_list.index(self.current_process)
                    prev_index = (current_index - 1) % len(process_list)
                    return process_list[prev_index]
                except ValueError:
                    # Current process not in loop, return last loop process
                    return process_list[-1]

        # Normal previous process logic
        prev_process = AssemblyProcess.objects.filter(
            stage=self.current_stage,
            order__lt=self.current_process.order
        ).order_by('-order').first()

        if prev_process:
            return prev_process
        else:
            # Move to previous stage of the current product
            prev_stage = AssemblyStage.objects.filter(
                product=self.current_product,
                order__lt=self.current_stage.order
            ).order_by('-order').first()
            if prev_stage:
                return prev_stage.processes.order_by('-order').first()

        return None

    
    def advance_to_next_process(self):
        """Advance station to next process and update stage if necessary"""
        next_process = self.get_next_process()
        if next_process:
            self.current_process = next_process

            # Update stage if process belongs to a different stage
            if next_process.stage != self.current_stage:
                self.current_stage = next_process.stage

                # Auto-disable loop mode when leaving a loop group
                if self.loop_mode and not next_process.loop_group:
                    self.loop_mode = False

            # Auto-enable loop mode for looped processes
            if next_process.is_looped and next_process.loop_group:
                self.loop_mode = True

            self.save()
            return True
        return False
    
    
    def go_back_to_previous_process(self):
        """Go back to previous process and update stage if necessary"""
        prev_process = self.get_previous_process()
        if prev_process:
            self.current_process = prev_process

            # Update stage if process belongs to a different stage
            if prev_process.stage != self.current_stage:
                self.current_stage = prev_process.stage

            # Handle loop mode
            if prev_process.is_looped and prev_process.loop_group:
                self.loop_mode = True
            elif not prev_process.loop_group:
                self.loop_mode = False

            self.save()
            return True
        return False

    
    def toggle_loop_mode(self):
        """Toggle loop mode if current process supports it"""
        if (self.current_process and 
            self.current_process.is_looped and 
            self.current_process.loop_group):
            self.loop_mode = not self.loop_mode
            self.save()
            return self.loop_mode
        return None
    
    def set_assembly_state(self, product=None, stage=None, process=None, quantity=None):
        """Set the assembly state for this station"""
        if product:
            self.current_product = product
        if stage:
            self.current_stage = stage
        if process:
            self.current_process = process
            # Auto-update stage if process belongs to different stage
            if process.stage != self.current_stage:
                self.current_stage = process.stage
        if quantity is not None:
            self.product_quantity = quantity
        
        # Handle loop mode
        if self.current_process:
            if (self.current_process.is_looped and 
                self.current_process.loop_group == 'final_assembly_1abc'):
                self.loop_mode = True
            else:
                self.loop_mode = False
        
        self.save()
    
    def get_assembly_progress(self):
        """Get current assembly progress information"""
        if not self.current_stage or not self.current_process:
            return None
        
        # Get all processes in current stage
        stage_processes = self.current_stage.processes.order_by('order')
        total_processes = stage_processes.count()
        
        if total_processes == 0:
            return None
        
        # Find current process position
        try:
            process_list = list(stage_processes)
            current_position = process_list.index(self.current_process) + 1
        except ValueError:
            current_position = 1
        
        # Get all stages for overall progress
        all_stages = AssemblyStage.objects.order_by('order')
        total_stages = all_stages.count()
        
        try:
            stage_list = list(all_stages)
            current_stage_position = stage_list.index(self.current_stage) + 1
        except ValueError:
            current_stage_position = 1
        
        return {
            'current_stage': self.current_stage.display_name,
            'current_process': self.current_process.display_name,
            'stage_progress': {
                'current': current_position,
                'total': total_processes,
                'percentage': round((current_position / total_processes) * 100, 1)
            },
            'overall_progress': {
                'current_stage': current_stage_position,
                'total_stages': total_stages,
                'stage_percentage': round((current_stage_position / total_stages) * 100, 1)
            },
            'is_loop_mode': self.loop_mode,
            'can_loop': (self.current_process.is_looped if self.current_process else False)
        }
    
    def get_available_next_steps(self):
        """Get information about available next steps"""
        next_process = self.get_next_process()
        prev_process = self.get_previous_process()
        
        return {
            'can_advance': next_process is not None,
            'can_go_back': prev_process is not None,
            'next_process': {
                'name': next_process.name,
                'display_name': next_process.display_name,
                'stage': next_process.stage.display_name,
                'is_new_stage': next_process.stage != self.current_stage
            } if next_process else None,
            'previous_process': {
                'name': prev_process.name,
                'display_name': prev_process.display_name,
                'stage': prev_process.stage.display_name,
                'is_different_stage': prev_process.stage != self.current_stage
            } if prev_process else None,
            'loop_info': {
                'is_loop_mode': self.loop_mode,
                'can_toggle_loop': (
                    self.current_process and 
                    self.current_process.is_looped and 
                    self.current_process.loop_group is not None
                ) if self.current_process else False,
                'loop_group': self.current_process.loop_group if self.current_process else None
            }
        }
     
  
class AssemblySession(models.Model):
    """Track assembly sessions across all displays"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    current_stage = models.ForeignKey(AssemblyStage, on_delete=models.SET_NULL, null=True, blank=True)
    current_process = models.ForeignKey(AssemblyProcess, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Track all three displays
    display_1_station = models.ForeignKey(Station, related_name='sessions_display_1', on_delete=models.SET_NULL, null=True, blank=True)
    display_2_station = models.ForeignKey(Station, related_name='sessions_display_2', on_delete=models.SET_NULL, null=True, blank=True)
    display_3_station = models.ForeignKey(Station, related_name='sessions_display_3', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        status = "Completed" if self.completed else "In Progress"
        return f"{self.product.code} - {self.quantity} units - {status}"
