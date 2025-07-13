# models.py - Enhanced with Database BOM System

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.urls import reverse
import zipfile
import os
from django.core.files.base import ContentFile

class Product(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.code} - {self.name}"

class AssemblyStage(models.Model):
    """Main assembly stages (Sub Assembly 1, Sub Assembly 2, Final Assembly)"""
    STAGE_CHOICES = [
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
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
    
    def generate_bom_for_quantity(self, quantity=1):
        """Generate BOM items with calculated quantities"""
        bom_items = []
        for item_line in self.bom_items.filter(is_active=True).order_by('serial_number'):
            calculated_qty = item_line.base_quantity * quantity
            
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
    base_quantity = models.DecimalField(max_digits=10, decimal_places=4, help_text="Quantity for single unit")
    
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

# Updated BillOfMaterial to support both PDF and Database modes
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

#  Pervious One <>No need to change here<>



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
    
    # Control settings
    clicker_enabled = models.BooleanField(default=True, help_text="Enable clicker support")
    auto_advance = models.BooleanField(default=False, help_text="Auto advance after media duration")
    loop_mode = models.BooleanField(default=False, help_text="Currently in loop mode (for processes 1A, 1B, 1C)")
    
    class Meta:
        unique_together = ['name', 'display_number']
    
    def __str__(self):
        return f"{self.name} - Display {self.display_number}"
    
    def get_current_bom_data(self):
        """Get current BOM data based on station settings and quantity - FIXED VERSION"""
        if not self.current_product:
            return None

        # Priority order for BOM selection:
        # 1. Stage-specific BOM (highest priority if current stage exists)
        # 2. Single unit BOM (if enabled)
        # 3. Batch BOM (if enabled)
        
        quantity = self.product_quantity
        
        # First, check if we have a stage-specific BOM and we're in a specific stage
        if self.current_stage:
            stage_bom_type = self.current_stage.name  # SUB_ASSEMBLY_1, SUB_ASSEMBLY_2, FINAL_ASSEMBLY
            try:
                stage_template = BOMTemplate.objects.get(
                    product=self.current_product,
                    bom_type=stage_bom_type,
                    is_active=True
                )
                print(f"DEBUG: Found stage-specific BOM: {stage_bom_type}")
                # Found stage-specific BOM, use it with current quantity
                return stage_template.generate_bom_for_quantity(quantity)
            except BOMTemplate.DoesNotExist:
                print(f"DEBUG: No stage-specific BOM found for {stage_bom_type}")
                # No stage-specific BOM found, fall back to general BOMs
                pass
        
        # Fall back to general BOM settings
        bom_type = None
        if self.show_single_unit_bom:
            bom_type = 'SINGLE_UNIT'
            quantity = 1
            print(f"DEBUG: Using single unit BOM")
        elif self.show_batch_bom:
            bom_type = 'BATCH_50'
            quantity = self.product_quantity
            print(f"DEBUG: Using batch BOM with quantity {quantity}")
        else:
            print(f"DEBUG: No BOM type selected")
            return None
        
        # Find the general BOM template
        try:
            bom_template = BOMTemplate.objects.get(
                product=self.current_product,
                bom_type=bom_type,
                is_active=True
            )
            print(f"DEBUG: Found general BOM template: {bom_type}")
            return bom_template.generate_bom_for_quantity(quantity)
        except BOMTemplate.DoesNotExist:
            print(f"DEBUG: No BOM template found for {bom_type}")
            return None

    def get_current_bom_info(self):
        """Get information about the currently selected BOM"""
        if not self.current_product:
            return None
        
        # Check for stage-specific BOM first
        if self.current_stage:
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
                    'items_count': stage_template.bom_items.filter(is_active=True).count()
                }
            except BOMTemplate.DoesNotExist:
                pass
        
        # Fall back to general BOM
        if self.show_single_unit_bom:
            try:
                template = BOMTemplate.objects.get(
                    product=self.current_product,
                    bom_type='SINGLE_UNIT',
                    is_active=True
                )
                return {
                    'template': template,
                    'type': 'single_unit',
                    'display_name': 'Single Unit',
                    'quantity': 1,
                    'items_count': template.bom_items.filter(is_active=True).count()
                }
            except BOMTemplate.DoesNotExist:
                pass
        elif self.show_batch_bom:
            try:
                template = BOMTemplate.objects.get(
                    product=self.current_product,
                    bom_type='BATCH_50',
                    is_active=True
                )
                return {
                    'template': template,
                    'type': 'batch',
                    'display_name': f'{self.product_quantity} Units Batch',
                    'quantity': self.product_quantity,
                    'items_count': template.bom_items.filter(is_active=True).count()
                }
            except BOMTemplate.DoesNotExist:
                pass
        
        return None

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