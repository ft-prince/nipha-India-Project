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
    display_name = models.CharField(max_length=100,blank=True, null=True)
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
    
    stage = models.ForeignKey(AssemblyStage, related_name='processes', on_delete=models.CASCADE,blank=True,null=True)
    name = models.CharField(max_length=100)  # e.g., "PROCESS 1A OF 6"
    display_name = models.CharField(max_length=200,blank=True, null=True)  # Full descriptive name
    location = models.CharField(max_length=30, choices=LOCATION_CHOICES,blank=True,null=True)
    order = models.PositiveIntegerField(default=1)
    
    # Special properties
    is_looped = models.BooleanField(default=False, help_text="Should loop until manually advanced")
    loop_group = models.CharField(max_length=50, blank=True, null=True, help_text="Group processes that loop together")
    
    class Meta:
        ordering = ['stage__order', 'order']
        unique_together = ['stage', 'order']
    
    def __str__(self):
        return f"{self.stage.display_name} - {self.name}"

class BillOfMaterial(models.Model):
    """Bill of Materials for different quantities and stages"""
    BOM_TYPE_CHOICES = [
        ('SINGLE_UNIT', 'Single Unit'),
        ('BATCH_50', '50 Units'),
        ('SUB_ASSEMBLY_1', 'Sub Assembly 1'),
        ('SUB_ASSEMBLY_2', 'Sub Assembly 2'),
        ('FINAL_ASSEMBLY', 'Final Assembly'),
    ]
    
    product = models.ForeignKey(Product, related_name='boms', on_delete=models.CASCADE)
    bom_type = models.CharField(max_length=20, choices=BOM_TYPE_CHOICES)
    stage = models.ForeignKey(AssemblyStage, related_name='boms', on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='bom_files/', validators=[FileExtensionValidator(allowed_extensions=['pdf', 'xlsx', 'docx'])])
    
    def __str__(self):
        return f"{self.product.code} - {self.get_bom_type_display()}"

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
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'mp4', 'mov', 'xlsx', 'docx'])]
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
    display_number = models.PositiveIntegerField(choices=DISPLAY_CHOICES, help_text="Which display screen this station represents",blank=True,null=True)
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
    

    def get_current_media(self):
        """Get media for current state based on display number"""
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
            # If no display number, return empty
            return ProductMedia.objects.none()
        
        # Filter by current process if set
        if self.current_process:
            process_media = media_query.filter(process=self.current_process)
        else:
            process_media = ProductMedia.objects.none()
        
        # Get BOMs based on settings
        bom_media = ProductMedia.objects.none()
        
        if self.display_number == 1:  # Only show BOMs on display 1
            bom_query = ProductMedia.objects.filter(
                product=self.current_product,
                media_type='BOM',
                display_screen_1=True
            )
            
            if self.show_single_unit_bom:
                bom_media = bom_query.filter(bom__bom_type='SINGLE_UNIT')
            elif self.show_batch_bom:
                bom_media = bom_query.filter(bom__bom_type='BATCH_50')
            
            # Include stage-specific BOMs
            if self.current_stage:
                stage_bom = bom_query.filter(bom__stage=self.current_stage)
                if bom_media.exists():
                    bom_media = bom_media.union(stage_bom)
                else:
                    bom_media = stage_bom
        
        # Combine process media and BOM media
        if process_media.exists() and bom_media.exists():
            return process_media.union(bom_media)
        elif process_media.exists():
            return process_media
        elif bom_media.exists():
            return bom_media
        else:
            # Return any media for this display if nothing else matches
            return media_query
    
    def get_next_process(self):
        """Get next process, handling loops and stage transitions"""
        if not self.current_stage:
            return AssemblyProcess.objects.first()
        
        # If in loop mode and current process has loop_group, stay in loop
        if self.loop_mode and self.current_process and self.current_process.loop_group:
            loop_processes = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                loop_group=self.current_process.loop_group
            ).order_by('order')
            
            current_index = list(loop_processes).index(self.current_process)
            next_index = (current_index + 1) % loop_processes.count()
            return loop_processes[next_index]
        
        # Normal next process logic
        if self.current_process:
            next_process = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                order__gt=self.current_process.order
            ).first()
            
            if next_process:
                return next_process
            else:
                # Move to next stage
                next_stage = AssemblyStage.objects.filter(
                    order__gt=self.current_stage.order
                ).first()
                if next_stage:
                    return next_stage.processes.first()
        
        return None
    
    def get_previous_process(self):
        """Get previous process"""
        if not self.current_process:
            return None
        
        # If in loop mode, navigate within loop
        if self.loop_mode and self.current_process.loop_group:
            loop_processes = AssemblyProcess.objects.filter(
                stage=self.current_stage,
                loop_group=self.current_process.loop_group
            ).order_by('order')
            
            current_index = list(loop_processes).index(self.current_process)
            prev_index = (current_index - 1) % loop_processes.count()
            return loop_processes[prev_index]
        
        # Normal previous process logic
        return AssemblyProcess.objects.filter(
            stage=self.current_stage,
            order__lt=self.current_process.order
        ).last()

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