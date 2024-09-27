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

class Station(models.Model):
    name = models.CharField(max_length=100)
    screen_name = models.CharField(max_length=400, blank=True)
    products = models.ManyToManyField(Product, related_name='stations', blank=True)
    selected_media = models.ManyToManyField('ProductMedia', related_name='selected_stations', blank=True)
    manager = models.ForeignKey(User, on_delete=models.CASCADE, blank=True)

    def __str__(self):
        return self.name

class ProductMedia(models.Model):
    product = models.ForeignKey(Product, related_name='media', on_delete=models.CASCADE)
    file = models.FileField(
        upload_to='product_media/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'mp4', 'mov', 'zip'])]
    )
    duration = models.PositiveIntegerField(default=15, blank=True, help_text="Duration in seconds (for videos)")
    station = models.ForeignKey(Station, on_delete=models.CASCADE, blank=True, null=True)
    is_selected = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.code} - {self.file.name}"

    def save(self, *args, **kwargs):
        if self.file.name.endswith('.zip'):
            with zipfile.ZipFile(self.file) as zip_file:
                for filename in zip_file.namelist():
                    name, extension = os.path.splitext(filename)
                    if extension.lower() in ['.pdf', '.mp4', '.mov']:
                        file_content = zip_file.read(filename)
                        content_file = ContentFile(file_content)
                        new_media = ProductMedia(
                            product=self.product,
                            station=self.station,
                            is_selected=self.is_selected,
                            is_active=self.is_active
                        )
                        new_media.file.save(filename, content_file, save=False)
                        new_media.save()
            self.file.delete(save=False)
            return
        super().save(*args, **kwargs)

class Linewise(models.Model): 
    name = models.CharField(max_length=100) 
    stations = models.ManyToManyField(Station, related_name='linewise_set') 
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True) 

    def __str__(self): 
        return self.name 

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.product:
            self.update_stations_and_media()

    def update_stations_and_media(self):
        if self.product:
            # Update all stations to include the selected product
            self.stations.add(*self.product.stations.all())

            for station in self.stations.all():
                # Get all media for this product and station that are active
                product_media = ProductMedia.objects.filter(
                    product=self.product,
                    station=station,
                    is_active=True
                )
                
                # Update the selected_media for this station
                station.selected_media.set(product_media)
                
                # Update is_selected status in ProductMedia
                ProductMedia.objects.filter(station=station).update(is_selected=False)
                product_media.update(is_selected=True)