from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Station, ProductMedia

def get_station_media(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = ProductMedia.objects.filter(
        station=station,
        is_selected=True,
        is_active=True
    )
    
    media_data = [
        {
            'id': m.id,
            'url': m.file.url,
            'type': m.file.name.split('.')[-1].lower(),
            'duration': m.duration,
            'product_name': m.product.name,
            'product_code': m.product.code
        }
        for m in selected_media
    ]
    return JsonResponse({'media': media_data})

def station_media_slider(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = ProductMedia.objects.filter(
        station=station,
        is_selected=True,
        is_active=True
    )
    return render(request, 'station_slider.html', {'station': station, 'selected_media': selected_media})