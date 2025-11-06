
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




class ProductStage(models.Model):
    """Product-specific assembly stages"""
    STAGE_TYPE_CHOICES = [
        ('BOM_DISPLAY', 'BOM Display'),
        ('SUB_ASSEMBLY', 'Sub Assembly'),
        ('FINAL_ASSEMBLY', 'Final Assembly'),

    ]
    
    product = models.ForeignKey(Product, related_name='product_stages', on_delete=models.CASCADE)
    stage_code = models.CharField(max_length=50, help_text="e.g., 'SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2'")
    stage_type = models.CharField(max_length=20, choices=STAGE_TYPE_CHOICES)
    display_name = models.CharField(max_length=100, help_text="e.g., 'Sub Assembly 1', 'Final Assembly'")
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(help_text="Order of this stage in the product assembly")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'order']
        unique_together = ['product', 'stage_code']
    
    def __str__(self):
        return f"{self.product.code} - {self.display_name}"

class ProductAssemblyProcess(models.Model):
    """Product-specific assembly processes within each product stage"""
    LOCATION_CHOICES = [
        ('IN_ASSEMBLY_ROOM', 'In Assembly Room'),
        ('OUTSIDE_ASSEMBLY_ROOM', 'Outside Assembly Room'),
        ('QUALITY_STATION', 'Quality Station'),
        ('PACKAGING_AREA', 'Packaging Area'),
    ]
    
    product = models.ForeignKey(Product, related_name='product_processes', on_delete=models.CASCADE)
    stage = models.ForeignKey(ProductStage, related_name='product_processes', on_delete=models.CASCADE)
    
    process_name = models.CharField(max_length=100, help_text="e.g., 'PROCESS_1_OF_11'")
    display_name = models.CharField(max_length=200, help_text="e.g., 'HOGO Final Assembly (Process 1 of 11)'")
    location = models.CharField(max_length=30, choices=LOCATION_CHOICES, default='IN_ASSEMBLY_ROOM')
    order = models.PositiveIntegerField(help_text="Order within the stage")
    
    # Process control properties
    is_looped = models.BooleanField(default=False, help_text="Should loop until manually advanced")
    loop_group = models.CharField(max_length=50, blank=True, null=True, help_text="Group processes that loop together")
    duration = models.PositiveIntegerField(default=20, help_text="Duration in seconds")
    auto_advance = models.BooleanField(default=False, help_text="Auto advance after duration")
    
    # Display assignments
    display_screen_1 = models.BooleanField(default=False, help_text="Show on Display Screen 1")
    display_screen_2 = models.BooleanField(default=False, help_text="Show on Display Screen 2")
    display_screen_3 = models.BooleanField(default=False, help_text="Show on Display Screen 3")
    
    # Additional info
    notes = models.TextField(blank=True, null=True, help_text="Special instructions or notes")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'stage__order', 'order']
        unique_together = ['stage', 'order']
    
    def __str__(self):
        return f"{self.product.code} - {self.stage.display_name} - {self.display_name}"

class AssemblyStage(models.Model):
    """Main assembly stages (Sub Assembly 1, Sub Assembly 2, Final Assembly)"""
    STAGE_CHOICES = [
        
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
        ('BOM_DISPLAY', 'BOM_DISPLAY'),
        ('SUB_ASSEMBLY_2', 'Sub Assembly 2'), 
        ('FINAL_ASSEMBLY', 'Final Assembly'),
    ]
    
    name = models.CharField(max_length=50, choices=STAGE_CHOICES, unique=True)
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

    def get_items_for_display(self, display_number, quantity=1, page=1, items_per_screen=8):
        """Get BOM items specific to a display number with pagination - FIXED WITH STAGE-SPECIFIC PAGINATION"""
        print(f"DEBUG TEMPLATE: get_items_for_display called for display {display_number}, quantity {quantity}, page {page}")
        print(f"DEBUG TEMPLATE: BOM type: {self.bom_type}, should_split: {self.should_split_across_displays()}")
        
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
                    print(f"DEBUG TEMPLATE: Stage-specific BOM Display 1, Page {page}: No items (beyond range)")
                else:
                    result = all_items[start_idx:end_idx]
                    print(f"DEBUG TEMPLATE: Stage-specific BOM Display 1, Page {page}: items {start_idx+1} to {end_idx} ({len(result)} items)")
                
                return result
            else:
                print(f"DEBUG TEMPLATE: Stage-specific BOM on display {display_number}: 0 items (only Display 1 gets data)")
                return []
        
        # Split logic for SINGLE_UNIT and BATCH_50 with FIXED 8 items per display per page
        all_items = self.generate_bom_for_quantity(quantity)
        total_items = len(all_items)
        
        print(f"DEBUG TEMPLATE: Total items to split: {total_items}")
        
        if total_items == 0:
            return []
        
        # FIXED LOGIC: Always 8 items per display, with pagination
        max_items_per_display = 8
        items_per_page = max_items_per_display * 3  # 8 items × 3 displays = 24 items per page
        
        # Calculate which items belong to this page
        page_start_idx = (page - 1) * items_per_page
        page_end_idx = min(page_start_idx + items_per_page, total_items)
        page_items = all_items[page_start_idx:page_end_idx]
        
        print(f"DEBUG TEMPLATE: Page {page} contains items {page_start_idx + 1} to {page_end_idx} ({len(page_items)} items)")
        
        if len(page_items) == 0:
            print(f"DEBUG TEMPLATE: No items for page {page}, display {display_number}")
            return []
        
        # Calculate which items from this page belong to this display
        display_start_idx = (display_number - 1) * max_items_per_display
        display_end_idx = min(display_start_idx + max_items_per_display, len(page_items))
        
        if display_start_idx >= len(page_items):
            result = []
            print(f"DEBUG TEMPLATE: Page {page}, Display {display_number} gets no items (beyond page range)")
        else:
            result = page_items[display_start_idx:display_end_idx]
            # Calculate actual item numbers for debugging
            actual_start = page_start_idx + display_start_idx + 1
            actual_end = page_start_idx + display_end_idx
            print(f"DEBUG TEMPLATE: Page {page}, Display {display_number} gets items {actual_start} to {actual_end} ({len(result)} items)")
        
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
        stage_specific_bom_types = ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']
        
        if self.bom_type in stage_specific_bom_types:
            # For stage-specific BOMs, always use base quantity (no multiplication)
            effective_quantity = 1
            print(f"DEBUG BOM: Stage-specific BOM ({self.bom_type}) - using quantity = 1 (not {quantity})")
        else:
            # For unit-based BOMs (SINGLE_UNIT, BATCH_50), use the provided quantity
            effective_quantity = quantity
            print(f"DEBUG BOM: Unit-based BOM ({self.bom_type}) - using quantity = {quantity}")
        
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
        
        print(f"DEBUG BOM: Generated {len(bom_items)} items for {self.bom_type} with effective quantity {effective_quantity}")
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
    products = models.ManyToManyField(Product, related_name='assembly_stations', blank=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    
    # Current assembly state
    current_product = models.ForeignKey(Product, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    current_stage = models.ForeignKey(AssemblyStage, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    current_process = models.ForeignKey(AssemblyProcess, related_name='active_stations', on_delete=models.SET_NULL, null=True, blank=True)
    product_quantity = models.PositiveIntegerField(default=50, help_text="Quantity being assembled")
    
    # BOM selection
    show_single_unit_bom = models.BooleanField(default=False, help_text="Show single unit BOM for reference")
    show_batch_bom = models.BooleanField(default=True, help_text="Show batch quantity BOM")
    
    # Control settings
    clicker_enabled = models.BooleanField(default=True, help_text="Enable clicker support")
    auto_advance = models.BooleanField(default=False, help_text="Auto advance after media duration")
    loop_mode = models.BooleanField(default=False, help_text="Currently in loop mode (for processes 1A, 1B, 1C)")
    
    class Meta:
        unique_together = ['name', 'display_number']
    
    def __str__(self):
        return f"{self.name} - Display {self.display_number}"
    
# FIXED: Station.get_current_bom_data method - No split for assembly stages

    def get_current_bom_data(self, page=1):
        """Get current BOM data with pagination support - FIXED PAGINATION"""
        if not self.current_product or not self.display_number:
            return None

        print(f"DEBUG BOM: Station {self.name}, Display {self.display_number}, Page {page}")
        print(f"DEBUG BOM: Current stage: {self.current_stage.name if self.current_stage else 'None'}")
        print(f"DEBUG BOM: Current process: {self.current_process.name if self.current_process else 'None'}")
        
        quantity = self.product_quantity
        
        # PRIORITY 1: Stage-specific BOM (pagination on Display 1 only)
        if self.current_stage and self.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            # For assembly stages, ONLY Display 1 gets BOM, others get nothing
            if self.display_number == 1:
                stage_bom_type = self.current_stage.name
                try:
                    stage_template = BOMTemplate.objects.get(
                        product=self.current_product,
                        bom_type=stage_bom_type,
                        is_active=True
                    )
                    print(f"DEBUG BOM: Found stage-specific BOM: {stage_bom_type} for Display 1 with pagination")
                    # FIXED: Use get_items_for_display with pagination instead of generate_bom_for_quantity
                    result = stage_template.get_items_for_display(
                        display_number=self.display_number,
                        quantity=quantity,
                        page=page,
                        items_per_screen=8
                    )
                    print(f"DEBUG BOM: Stage BOM returned {len(result)} items for Display 1, Page {page}")
                    return result
                except BOMTemplate.DoesNotExist:
                    print(f"DEBUG BOM: No stage-specific BOM found for {stage_bom_type}")
                    # No stage-specific BOM found, still only show on Display 1
                    pass
            else:
                # Displays 2 and 3 get NO BOM in assembly stages
                print(f"DEBUG BOM: Assembly stage - Display {self.display_number} gets NO BOM")
                return None
        
        # PRIORITY 2: BOM Display stage (split across displays WITH pagination)
        elif self.current_stage and self.current_stage.name == 'BOM_DISPLAY':
            # Only in BOM_DISPLAY stage do we split across displays with pagination
            bom_type = None
            if self.show_single_unit_bom:
                bom_type = 'SINGLE_UNIT'
                quantity = 1
                print(f"DEBUG BOM: BOM Display stage - Using single unit BOM (split across displays with pagination)")
            elif self.show_batch_bom:
                bom_type = 'BATCH_50'
                quantity = self.product_quantity
                print(f"DEBUG BOM: BOM Display stage - Using batch BOM (split across displays with pagination)")
            else:
                print(f"DEBUG BOM: BOM Display stage - No BOM type selected")
                return None
            
            try:
                bom_template = BOMTemplate.objects.get(
                    product=self.current_product,
                    bom_type=bom_type,
                    is_active=True
                )
                print(f"DEBUG BOM: Found BOM template for BOM Display: {bom_type}")
                
                # Split across displays WITH pagination ONLY in BOM_DISPLAY stage
                display_items = bom_template.get_items_for_display(
                    display_number=self.display_number, 
                    quantity=quantity,
                    page=page,
                    items_per_screen=8  # Fixed at 8 items per screen
                )
                print(f"DEBUG BOM: BOM Display - Display {self.display_number}, Page {page} gets {len(display_items)} items")
                
                return display_items
                
            except BOMTemplate.DoesNotExist:
                print(f"DEBUG BOM: No BOM template found for {bom_type}")
                return None
        
        # PRIORITY 3: Other stages - no BOM
        else:
            print(f"DEBUG BOM: Other stage ({self.current_stage.name if self.current_stage else 'None'}) - No BOM")
            return None

    def get_current_bom_info(self, page=1):
        """Get information about the currently selected BOM including split info - UPDATED WITH PAGINATION"""
        if not self.current_product:
            return None
        
        # Check for stage-specific BOM first (only on Display 1, no pagination)
        if self.current_stage and self.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY'] and self.display_number == 1:
            try:
                stage_template = BOMTemplate.objects.get(
                    product=self.current_product,
                    bom_type=self.current_stage.name,
                    is_active=True
                )
                return {
                    'template': stage_template,
                    'type': 'stage_specific',
                    'display_name': f"{self.current_stage.display_name}",
                    'quantity': self.product_quantity,
                    'items_count': stage_template.bom_items.filter(is_active=True).count(),
                    'is_split': False,
                    'display_info': f"Complete BOM on Display {self.display_number}",
                    'pagination_info': {
                        'total_pages': 1,
                        'current_page': 1,
                        'items_per_page': stage_template.bom_items.filter(is_active=True).count()
                    }
                }
            except BOMTemplate.DoesNotExist:
                pass
        
        # BOM Display stage with pagination
        elif self.current_stage and self.current_stage.name == 'BOM_DISPLAY':
            bom_type = None
            quantity = self.product_quantity
            
            if self.show_single_unit_bom:
                bom_type = 'SINGLE_UNIT'
                quantity = 1
            elif self.show_batch_bom:
                bom_type = 'BATCH_50'
                quantity = self.product_quantity
            
            if bom_type:
                try:
                    template = BOMTemplate.objects.get(
                        product=self.current_product,
                        bom_type=bom_type,
                        is_active=True
                    )
                    
                    # Get pagination info
                    pagination_info = template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
        
                    # Get split information for current page
                    split_info = template.get_display_info_for_split(page=page, quantity=quantity)
                    current_display_info = split_info[f'display_{self.display_number}'] if split_info else None
                    
                    display_name = 'Single Unit BOM' if bom_type == 'SINGLE_UNIT' else f'{quantity} Units BOM'
                    if self.display_number in [2, 3]:
                        display_name += ' (Split)'
                    
                    return {
                        'template': template,
                        'type': bom_type.lower(),
                        'display_name': display_name,
                        'quantity': quantity,
                        'items_count': current_display_info['item_count'] if current_display_info else 0,
                        'is_split': True,
                        'display_info': f"Page {page} - Items {current_display_info['start_serial']}-{current_display_info['end_serial']}" if current_display_info and current_display_info['item_count'] > 0 else f"Page {page} - No items",
                        'split_info': split_info,
                        'pagination_info': pagination_info
                    }
                except BOMTemplate.DoesNotExist:
                    pass
        
        return None

    def get_bom_pagination_info(self):
        """Get pagination information for the current BOM"""
        if not self.current_product:
            return None
        
        # Stage-specific BOMs don't paginate
        if self.current_stage and self.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            return {
                'total_pages': 1,
                'items_per_page': 0,  # Will be filled by template
                'supports_pagination': False
            }
        
        # BOM Display stage supports pagination
        elif self.current_stage and self.current_stage.name == 'BOM_DISPLAY':
            bom_type = None
            quantity = self.product_quantity
            
            if self.show_single_unit_bom:
                bom_type = 'SINGLE_UNIT'
                quantity = 1
            elif self.show_batch_bom:
                bom_type = 'BATCH_50'
                quantity = self.product_quantity
            
            if bom_type:
                try:
                    template = BOMTemplate.objects.get(
                        product=self.current_product,
                        bom_type=bom_type,
                        is_active=True
                    )
                    pagination_info = template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
                    pagination_info['supports_pagination'] = True
                    return pagination_info
                except BOMTemplate.DoesNotExist:
                    pass
        
        return {
            'total_pages': 1,
            'items_per_page': 0,
            'supports_pagination': False
        }
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
            # No current stage, start with first stage and first process
            first_stage = AssemblyStage.objects.first()
            if first_stage:
                return first_stage.processes.first()
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
                # Move to next stage
                next_stage = AssemblyStage.objects.filter(
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
        # Look for previous process in current stage 
        prev_process = AssemblyProcess.objects.filter(
            stage=self.current_stage,
            order__lt=self.current_process.order
        ).order_by('-order').first()
        
        if prev_process:
            return prev_process
        else:
            # Move to previous stage's last process
            prev_stage = AssemblyStage.objects.filter(
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
            # Update stage if process belongs to different stage
            if next_process.stage != self.current_stage:
                self.current_stage = next_process.stage
                # Auto-disable loop mode when moving to new stage
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
            # Update stage if process belongs to different stage
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
    
    
    
    
    
    
    
class ProductStageManager:
    """Helper functions to manage product-specific stages without breaking existing code"""
    
    @staticmethod
    def get_product_stages(product):
        """Get all stages for a specific product in order"""
        return ProductStage.objects.filter(
            product=product, 
            is_active=True
        ).order_by('order')
    
    @staticmethod
    def sync_product_stages_to_assembly_stages(product):
        """
        Create AssemblyStage entries from ProductStage for backward compatibility
        This keeps your existing views working
        """
        product_stages = ProductStageManager.get_product_stages(product)
        
        for product_stage in product_stages:
            # Create or update corresponding AssemblyStage
            assembly_stage, created = AssemblyStage.objects.get_or_create(
                name=product_stage.stage_code,
                defaults={
                    'display_name': product_stage.display_name,
                    'description': product_stage.description,
                    'order': product_stage.order
                }
            )
            
            # Update if not created and different
            if not created:
                assembly_stage.display_name = product_stage.display_name
                assembly_stage.description = product_stage.description
                assembly_stage.order = product_stage.order
                assembly_stage.save()
    
    @staticmethod
    def sync_product_processes_to_assembly_processes(product):
        """
        Create AssemblyProcess entries from ProductAssemblyProcess for backward compatibility
        """
        product_processes = ProductAssemblyProcess.objects.filter(
            product=product,
            is_active=True
        ).order_by('stage__order', 'order')
        
        for product_process in product_processes:
            # Get corresponding AssemblyStage
            try:
                assembly_stage = AssemblyStage.objects.get(name=product_process.stage.stage_code)
                
                # Create or update corresponding AssemblyProcess
                assembly_process, created = AssemblyProcess.objects.get_or_create(
                    stage=assembly_stage,
                    name=product_process.process_name,
                    defaults={
                        'display_name': product_process.display_name,
                        'location': 'ASSEMBLY_ROOM' if product_process.location == 'IN_ASSEMBLY_ROOM' else 'OUTSIDE_ASSEMBLY_ROOM',
                        'order': product_process.order,
                        'is_looped': product_process.is_looped,
                        'loop_group': product_process.loop_group
                    }
                )
                
                # Update if not created
                if not created:
                    assembly_process.display_name = product_process.display_name
                    assembly_process.location = 'ASSEMBLY_ROOM' if product_process.location == 'IN_ASSEMBLY_ROOM' else 'OUTSIDE_ASSEMBLY_ROOM'
                    assembly_process.order = product_process.order
                    assembly_process.is_looped = product_process.is_looped
                    assembly_process.loop_group = product_process.loop_group
                    assembly_process.save()
                    
            except AssemblyStage.DoesNotExist:
                continue
    
    @staticmethod
    def setup_hogo_product():
        """Setup HOGO product stages and processes based on Excel data"""
        try:
            hogo = Product.objects.get(code='HOGO')
        except Product.DoesNotExist:
            print("HOGO product not found")
            return
        
        # Clear existing product stages
        ProductStage.objects.filter(product=hogo).delete()
        
        # Create BOM Display Stage
        bom_stage = ProductStage.objects.create(
            product=hogo,
            stage_code='BOM_DISPLAY',
            stage_type='BOM_DISPLAY',
            display_name='BOM Display',
            order=1
        )
        
        # Create Sub Assembly 1 Stage
        sub1_stage = ProductStage.objects.create(
            product=hogo,
            stage_code='SUB_ASSEMBLY_1',
            stage_type='SUB_ASSEMBLY',
            display_name='Sub Assembly 1',
            order=2
        )
        # Add processes for Sub Assembly 1
        ProductAssemblyProcess.objects.create(
            product=hogo, stage=sub1_stage,
            process_name='PROCESS_1_OF_2',
            display_name='HOGO Sub Assembly-1 (Process 1 of 2)',
            order=1, location='OUTSIDE_ASSEMBLY_ROOM',
            display_screen_2=True, display_screen_3=True
        )
        ProductAssemblyProcess.objects.create(
            product=hogo, stage=sub1_stage,
            process_name='PROCESS_2_OF_2',
            display_name='HOGO Sub Assembly-1 (Process 2 of 2)',
            order=2, location='OUTSIDE_ASSEMBLY_ROOM',
            display_screen_2=True, display_screen_3=True
        )
        
        # Create Sub Assembly 2 Stage
        sub2_stage = ProductStage.objects.create(
            product=hogo,
            stage_code='SUB_ASSEMBLY_2',
            stage_type='SUB_ASSEMBLY',
            display_name='Sub Assembly 2',
            order=3
        )
        ProductAssemblyProcess.objects.create(
            product=hogo, stage=sub2_stage,
            process_name='PROCESS_1_OF_1',
            display_name='HOGO Sub Assembly-2 (Process 1 of 1)',
            order=1, location='OUTSIDE_ASSEMBLY_ROOM',
            display_screen_2=True, display_screen_3=True
        )
        
        # Create Sub Assembly 3 Stage
        sub3_stage = ProductStage.objects.create(
            product=hogo,
            stage_code='SUB_ASSEMBLY_3',
            stage_type='SUB_ASSEMBLY',
            display_name='Sub Assembly 3',
            order=4
        )
        ProductAssemblyProcess.objects.create(
            product=hogo, stage=sub3_stage,
            process_name='PROCESS_1_OF_1',
            display_name='HOGO Sub Assembly-3 (Process 1 of 1)',
            order=1, location='OUTSIDE_ASSEMBLY_ROOM',
            display_screen_2=True, display_screen_3=True,
            notes='Loop Videos with the CAPA\'s'
        )
        
        # Create Final Assembly Stage
        final_stage = ProductStage.objects.create(
            product=hogo,
            stage_code='FINAL_ASSEMBLY',
            stage_type='FINAL_ASSEMBLY',
            display_name='Final Assembly',
            order=5
        )
        # Add all 11 final assembly processes
        for i in range(1, 12):
            location = 'IN_ASSEMBLY_ROOM' if i <= 8 else 'OUTSIDE_ASSEMBLY_ROOM'
            notes = 'Loop Videos with the CAPA\'s' if i in [1, 2] else None
            
            ProductAssemblyProcess.objects.create(
                product=hogo, stage=final_stage,
                process_name=f'PROCESS_{i}_OF_11',
                display_name=f'HOGO Final Assembly (Process {i} of 11)',
                order=i, location=location,
                display_screen_2=True, display_screen_3=True,
                notes=notes
            )
        
        # Sync to legacy models for backward compatibility
        ProductStageManager.sync_product_stages_to_assembly_stages(hogo)
        ProductStageManager.sync_product_processes_to_assembly_processes(hogo)
        
        print(f"Successfully created {ProductStage.objects.filter(product=hogo).count()} stages and {ProductAssemblyProcess.objects.filter(product=hogo).count()} processes for HOGO")
    
    @staticmethod
    def setup_brg_product():
        """Setup BRG product stages and processes based on Excel data"""
        try:
            brg = Product.objects.get(code='BRG_40K')
        except Product.DoesNotExist:
            print("BRG_40K product not found")
            return
        
        # Clear existing product stages
        ProductStage.objects.filter(product=brg).delete()
        
        # Create BOM Display Stage
        bom_stage = ProductStage.objects.create(
            product=brg,
            stage_code='BOM_DISPLAY',
            stage_type='BOM_DISPLAY',
            display_name='BOM Display',
            order=1
        )
        
        # Create Sub Assembly 1 Stage (3 processes)
        sub1_stage = ProductStage.objects.create(
            product=brg,
            stage_code='SUB_ASSEMBLY_1',
            stage_type='SUB_ASSEMBLY',
            display_name='Sub Assembly 1',
            order=2
        )
        for i in range(1, 4):
            ProductAssemblyProcess.objects.create(
                product=brg, stage=sub1_stage,
                process_name=f'PROCESS_{i}_OF_3',
                display_name=f'BRG Assembly 40K, Sub Assembly-1 (Process {i} of 3)',
                order=i, location='OUTSIDE_ASSEMBLY_ROOM',
                display_screen_2=True, display_screen_3=True
            )
        
        # Create Sub Assembly 2 Stage (1 process)
        sub2_stage = ProductStage.objects.create(
            product=brg,
            stage_code='SUB_ASSEMBLY_2',
            stage_type='SUB_ASSEMBLY',
            display_name='Sub Assembly 2',
            order=3
        )
        ProductAssemblyProcess.objects.create(
            product=brg, stage=sub2_stage,
            process_name='PROCESS_1_OF_1',
            display_name='BRG Assembly 40K, Sub Assembly-2 (Process 1 of 1)',
            order=1, location='OUTSIDE_ASSEMBLY_ROOM',
            display_screen_2=True, display_screen_3=True
        )
        
        # Create Final Assembly Stage (6 processes with loop group)
        final_stage = ProductStage.objects.create(
            product=brg,
            stage_code='FINAL_ASSEMBLY',
            stage_type='FINAL_ASSEMBLY',
            display_name='Final Assembly',
            order=4
        )
        
        # Process 1A, 1B, 1C (loop group)
        for i, process_code in enumerate(['1A', '1B', '1C'], 1):
            ProductAssemblyProcess.objects.create(
                product=brg, stage=final_stage,
                process_name=f'PROCESS_{process_code}_OF_6',
                display_name=f'BRG Assembly 40K, Final Assembly (Process {process_code} of 6)',
                order=i, location='IN_ASSEMBLY_ROOM',
                is_looped=True, loop_group='1ABC',
                display_screen_2=True, display_screen_3=True,
                notes='in display 2nd, all the 3 files should be in loop until we move on to process 4' if i == 1 else None
            )
        
        # Processes 2-6
        for i in range(2, 7):
            location = 'IN_ASSEMBLY_ROOM' if i == 2 else 'OUTSIDE_ASSEMBLY_ROOM'
            ProductAssemblyProcess.objects.create(
                product=brg, stage=final_stage,
                process_name=f'PROCESS_{i}_OF_6',
                display_name=f'BRG Assembly 40K, Final Assembly (Process {i} of 6)',
                order=i+2, location=location,  # +2 because 1A,1B,1C take orders 1,2,3
                display_screen_2=True, display_screen_3=True
            )
        
        # Sync to legacy models for backward compatibility
        ProductStageManager.sync_product_stages_to_assembly_stages(brg)
        ProductStageManager.sync_product_processes_to_assembly_processes(brg)
        
        print(f"Successfully created {ProductStage.objects.filter(product=brg).count()} stages and {ProductAssemblyProcess.objects.filter(product=brg).count()} processes for BRG")
    