from django.urls import path
from . import views

urlpatterns = [
    path('station/<int:station_id>/media/', views.get_station_media, name='station_media'),
    path('station/<int:station_id>/slider/', views.station_media_slider, name='station_media_slider'),
    path('station/<int:station_id>/stream/', views.station_media_stream, name='station_media_stream'),

]