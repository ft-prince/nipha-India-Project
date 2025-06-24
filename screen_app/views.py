from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import condition
from django.conf import settings
from wsgiref.util import FileWrapper
import os
import mimetypes
import time
import json
from .models import Station, ProductMedia, Refresher


def get_product_media(request):
    product_ids = request.GET.getlist('products[]')
    media = ProductMedia.objects.filter(product__in=product_ids)
    
    media_list = [
        {
            'id': m.id,
            'url': m.file.url,
            'type': m.file.name.split('.')[-1].lower(),
            'duration': m.duration
        }
        for m in media
    ]
    
    return JsonResponse({'media': media_list})


def get_station_media(request, station_id):
    station = get_object_or_404(Station, pk=station_id)
    selected_media = station.selected_media.all()
    
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
    request.session['last_station_id'] = station_id

    # Get the first Refresher object's time_duration or default to 3 minutes
    refresh_duration = Refresher.objects.first().time_duration if Refresher.objects.exists() else 3
    
    selected_media = station.selected_media.all()
    
    return render(request, 'station_slider.html', {
        'station': station, 
        'selected_media': selected_media,
        'refresh_duration': refresh_duration
    })


def station_media_stream(request, station_id):
    """Real-time streaming endpoint for media updates"""
    def event_stream():
        last_update = None
        while True:
            try:
                station = get_object_or_404(Station, pk=station_id)
                selected_media = station.selected_media.select_related('product').all()
                
                # Convert QuerySet to list of dicts for comparison
                current_media = list(selected_media.values(
                    'id', 'file', 'duration', 'product__name', 'product__code'
                ))
                
                # Only send update if media has changed
                if current_media != last_update:
                    media_data = {
                        'media': [
                            {
                                'id': m.id,
                                'url': m.file.url,
                                'type': m.file.name.split('.')[-1].lower(),
                                'duration': m.duration,
                                'product_name': m.product.name,
                                'product_code': m.product.code
                            }
                            for m in selected_media
                        ],
                        'station_name': station.name
                    }
                    last_update = current_media
                    yield f"data: {json.dumps(media_data)}\n\n"
                
                time.sleep(5)  # Check for updates every 5 seconds
                
            except Station.DoesNotExist:
                yield f"data: {json.dumps({'error': 'Station not found'})}\n\n"
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(10)  # Wait longer on errors

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'  # Disable buffering for nginx
    return response


def stream_video(request, video_path):
    # Remove any leading slashes and 'media' from the path
    clean_path = video_path.lstrip('/').replace('media/', '', 1)
    path = os.path.join(settings.MEDIA_ROOT, clean_path)
    
    range_header = request.META.get('HTTP_RANGE', '').strip()
    size = os.path.getsize(path)
    
    if range_header:
        range_s, range_e = range_header.split('=')[-1].split('-')
        range_start = int(range_s)
        range_end = int(range_e) if range_e else size - 1
        length = range_end - range_start + 1

        response = StreamingHttpResponse(
            file_iterator(path, offset=range_start, length=length),
            status=206,
            content_type='video/mp4'
        )
        response['Content-Range'] = f'bytes {range_start}-{range_end}/{size}'
    else:
        response = StreamingHttpResponse(
            file_iterator(path),
            content_type='video/mp4'
        )
    
    response['Accept-Ranges'] = 'bytes'
    response['Content-Length'] = str(size)
    return response


def stream_pdf(request, pdf_path):
    # Remove any leading slashes and 'media' from the path
    clean_path = pdf_path.lstrip('/').replace('media/', '', 1)
    path = os.path.join(settings.MEDIA_ROOT, clean_path)
    
    chunk_size = 8192
    response = StreamingHttpResponse(
        file_iterator(path, chunk_size=chunk_size),
        content_type='application/pdf'
    )
    response['Content-Length'] = os.path.getsize(path)
    return response


def file_iterator(path, chunk_size=8192, offset=0, length=None):
    with open(path, 'rb') as f:
        if offset:
            f.seek(offset)
        remaining = length if length is not None else None
        while True:
            if remaining is not None:
                chunk_size = min(chunk_size, remaining)
            data = f.read(chunk_size)
            if not data:
                break
            if remaining is not None:
                remaining -= len(data)
            yield data
            if remaining == 0:
                break