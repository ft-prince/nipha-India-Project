from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import time
from .models import (Station, Product, ProductMedia, AssemblyStage, 
                    AssemblyProcess, AssemblySession, BillOfMaterial)




def get_station_media(request, station_id):
    """Get media for a specific station based on current assembly state"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get media based on current assembly state and display number
    current_media = station.get_current_media()
    
    media_data = []
    for media in current_media:
        media_info = {
            'id': media.id,
            'url': media.file.url,
            'type': media.file.name.split('.')[-1].lower(),
            'duration': media.duration,
            'media_type': media.get_media_type_display(),
            'product_name': media.product.name,
            'product_code': media.product.code,
        }
        
        # Add process info if available
        if media.process:
            media_info['process'] = {
                'id': media.process.id,
                'name': media.process.name,
                'display_name': media.process.display_name,
                'stage': media.process.stage.display_name,
                'order': media.process.order,
                'is_looped': media.process.is_looped,
                'loop_group': media.process.loop_group
            }
        
        # Add BOM info if available
        if media.bom:
            media_info['bom'] = {
                'id': media.bom.id,
                'type': media.bom.get_bom_type_display(),
                'stage': media.bom.stage.display_name if media.bom.stage else None
            }
        
        media_data.append(media_info)
    
    return JsonResponse({
        'media': media_data,
        'station_info': {
            'name': station.name,
            'display_number': station.display_number,
            'current_product': {
                'id': station.current_product.id,
                'code': station.current_product.code,
                'name': station.current_product.name
            } if station.current_product else None,
            'current_stage': {
                'id': station.current_stage.id,
                'name': station.current_stage.display_name,
                'order': station.current_stage.order
            } if station.current_stage else None,
            'current_process': {
                'id': station.current_process.id,
                'name': station.current_process.name,
                'display_name': station.current_process.display_name,
                'order': station.current_process.order,
                'is_looped': station.current_process.is_looped,
                'loop_group': station.current_process.loop_group
            } if station.current_process else None,
            'quantity': station.product_quantity,
            'loop_mode': station.loop_mode,
            'clicker_enabled': station.clicker_enabled
        }
    })

def station_media_slider(request, station_id):
    """Render the media slider for a station"""
    station = get_object_or_404(Station, pk=station_id)
    request.session['last_station_id'] = station_id

    # Get current media for this display
    current_media = station.get_current_media()
    
    context = {
        'station': station,
        'selected_media': current_media,
        'current_product': station.current_product,
        'current_stage': station.current_stage,
        'current_process': station.current_process,
        'product_quantity': station.product_quantity,
        'clicker_enabled': station.clicker_enabled,
        'loop_mode': station.loop_mode,
        'next_process': station.get_next_process(),
        'previous_process': station.get_previous_process(),
        'display_number': station.display_number,
    }
    
    return render(request, 'brg_station_slider.html', context)

def station_media_stream(request, station_id):
    """Real-time streaming for BRG assembly workflow"""
    def event_stream():
        last_update = None
        while True:
            try:
                station = get_object_or_404(Station, pk=station_id)
                current_media = station.get_current_media()
                
                # Create comprehensive comparison data
                media_comparison = []
                for media in current_media:
                    comparison_item = {
                        'id': media.id,
                        'file_url': media.file.url,
                        'media_type': media.media_type,
                        'process_id': media.process.id if media.process else None,
                        'bom_id': media.bom.id if media.bom else None
                    }
                    media_comparison.append(comparison_item)
                
                # Include assembly state in comparison
                assembly_state = {
                    'current_product_id': station.current_product.id if station.current_product else None,
                    'current_stage_id': station.current_stage.id if station.current_stage else None,
                    'current_process_id': station.current_process.id if station.current_process else None,
                    'product_quantity': station.product_quantity,
                    'loop_mode': station.loop_mode,
                    'display_number': station.display_number,
                }
                
                current_state = {
                    'media': media_comparison,
                    'assembly': assembly_state
                }
                
                # Only send update if something changed
                if current_state != last_update:
                    # Prepare detailed media data for frontend
                    media_data = []
                    for media in current_media:
                        media_info = {
                            'id': media.id,
                            'url': media.file.url,
                            'type': media.file.name.split('.')[-1].lower(),
                            'duration': media.duration,
                            'media_type': media.get_media_type_display(),
                            'product_name': media.product.name,
                            'product_code': media.product.code,
                        }
                        
                        if media.process:
                            media_info['process'] = {
                                'id': media.process.id,
                                'name': media.process.name,
                                'display_name': media.process.display_name,
                                'stage': media.process.stage.display_name,
                                'order': media.process.order,
                                'is_looped': media.process.is_looped,
                                'loop_group': media.process.loop_group
                            }
                        
                        if media.bom:
                            media_info['bom'] = {
                                'id': media.bom.id,
                                'type': media.bom.get_bom_type_display(),
                                'stage': media.bom.stage.display_name if media.bom.stage else None
                            }
                        
                        media_data.append(media_info)
                    
                    # Prepare assembly info
                    assembly_info = {
                        'current_product': {
                            'id': station.current_product.id,
                            'code': station.current_product.code,
                            'name': station.current_product.name
                        } if station.current_product else None,
                        'current_stage': {
                            'id': station.current_stage.id,
                            'name': station.current_stage.display_name,
                            'order': station.current_stage.order
                        } if station.current_stage else None,
                        'current_process': {
                            'id': station.current_process.id,
                            'name': station.current_process.name,
                            'display_name': station.current_process.display_name,
                            'order': station.current_process.order,
                            'is_looped': station.current_process.is_looped,
                            'loop_group': station.current_process.loop_group
                        } if station.current_process else None,
                        'quantity': station.product_quantity,
                        'loop_mode': station.loop_mode,
                        'clicker_enabled': station.clicker_enabled,
                        'display_number': station.display_number,
                        'next_process': {
                            'id': station.get_next_process().id,
                            'name': station.get_next_process().name,
                            'display_name': station.get_next_process().display_name
                        } if station.get_next_process() else None,
                        'previous_process': {
                            'id': station.get_previous_process().id,  
                            'name': station.get_previous_process().name,
                            'display_name': station.get_previous_process().display_name
                        } if station.get_previous_process() else None,
                    }
                    
                    response_data = {
                        'media': media_data,
                        'station_name': station.name,
                        'assembly': assembly_info,
                        'timestamp': time.time()
                    }
                    
                    last_update = current_state
                    yield f"data: {json.dumps(response_data)}\n\n"
                
                time.sleep(3)  # Check every 3 seconds for BRG workflow
                
            except Station.DoesNotExist:
                yield f"data: {json.dumps({'error': 'Station not found'})}\n\n"
                break
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                time.sleep(10)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['X-Accel-Buffering'] = 'no'
    return response

@csrf_exempt
@require_http_methods(["POST"])
def clicker_action(request, station_id):
    """Enhanced clicker action handling for BRG workflow"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.clicker_enabled:
        return JsonResponse({'error': 'Clicker not enabled for this station'}, status=400)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'forward', 'backward', 'toggle_loop'
        
        if action == 'forward':
            next_process = station.get_next_process()
            if next_process:
                # Special handling for exiting loop mode
                if (station.loop_mode and 
                    station.current_process and 
                    station.current_process.loop_group == 'final_assembly_1abc' and
                    next_process.name == 'PROCESS 2 OF 6'):
                    station.loop_mode = False
                
                station.current_process = next_process
                
                # Update stage if process belongs to different stage
                if next_process.stage != station.current_stage:
                    station.current_stage = next_process.stage
                
                station.save()
                
                return JsonResponse({
                    'success': True,
                    'current_process': {
                        'id': station.current_process.id,
                        'name': station.current_process.name,
                        'display_name': station.current_process.display_name,
                        'stage': station.current_stage.display_name,
                        'is_looped': station.current_process.is_looped
                    },
                    'loop_mode': station.loop_mode,
                    'next_process': {
                        'id': station.get_next_process().id,
                        'name': station.get_next_process().name
                    } if station.get_next_process() else None
                })
            else:
                return JsonResponse({'error': 'No next process available'}, status=400)
                
        elif action == 'backward':
            previous_process = station.get_previous_process()
            if previous_process:
                station.current_process = previous_process
                
                # Update stage if process belongs to different stage
                if previous_process.stage != station.current_stage:
                    station.current_stage = previous_process.stage
                
                station.save()
                
                return JsonResponse({
                    'success': True,
                    'current_process': {
                        'id': station.current_process.id,
                        'name': station.current_process.name,
                        'display_name': station.current_process.display_name,
                        'stage': station.current_stage.display_name,
                        'is_looped': station.current_process.is_looped
                    }
                })
            else:
                return JsonResponse({'error': 'No previous process available'}, status=400)
                
        elif action == 'toggle_loop':
            # Toggle loop mode for processes 1A, 1B, 1C
            if (station.current_process and 
                station.current_process.loop_group == 'final_assembly_1abc'):
                station.loop_mode = not station.loop_mode
                station.save()
                
                return JsonResponse({
                    'success': True,
                    'loop_mode': station.loop_mode,
                    'message': f"Loop mode {'enabled' if station.loop_mode else 'disabled'}"
                })
            else:
                return JsonResponse({'error': 'Loop mode only available for processes 1A, 1B, 1C'}, status=400)
        
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity value'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_assembly_options(request, station_id):
    """Get available options for BRG assembly configuration"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get available products for this station
    products = [
        {
            'id': p.id,
            'code': p.code,
            'name': p.name
        }
        for p in station.products.all()
    ]
    
    # Get all assembly stages
    stages = [
        {
            'id': s.id,
            'name': s.name,
            'display_name': s.display_name,
            'order': s.order,
            'processes': [
                {
                    'id': p.id,
                    'name': p.name,
                    'display_name': p.display_name,
                    'order': p.order,
                    'location': p.get_location_display(),
                    'is_looped': p.is_looped,
                    'loop_group': p.loop_group
                }
                for p in s.processes.all()
            ]
        }
        for s in AssemblyStage.objects.all().prefetch_related('processes')
    ]
    
    # Get current configuration
    current_config = {
        'product_id': station.current_product.id if station.current_product else None,
        'stage_id': station.current_stage.id if station.current_stage else None,
        'process_id': station.current_process.id if station.current_process else None,
        'quantity': station.product_quantity,
        'clicker_enabled': station.clicker_enabled,
        'loop_mode': station.loop_mode,
        'display_number': station.display_number,
        'bom_settings': {
            'show_single_unit': station.show_single_unit_bom,
            'show_batch': station.show_batch_bom
        }
    }
    
    return JsonResponse({
        'products': products,
        'stages': stages,
        'current_config': current_config,
        'workflow_info': {
            'total_stages': len(stages),
            'loop_processes': ['PROCESS 1A OF 6', 'PROCESS 1B OF 6', 'PROCESS 1C OF 6'],
            'display_assignments': {
                1: 'BOMs and Reference Materials',
                2: 'Process Documents and Instructions', 
                3: 'Instructional Videos'
            }
        }
    })

def get_workflow_status(request):
    """Get overall workflow status across all displays"""
    stations = Station.objects.all().select_related(
        'current_product', 'current_stage', 'current_process'
    )
    
    workflow_status = {
        'stations': [],
        'active_sessions': AssemblySession.objects.filter(completed=False).count(),
        'current_time': time.time()
    }
    
    for station in stations:
        station_info = {
            'id': station.id,
            'name': station.name,
            'display_number': station.display_number,
            'current_product': {
                'code': station.current_product.code,
                'name': station.current_product.name
            } if station.current_product else None,
            'current_stage': station.current_stage.display_name if station.current_stage else None,
            'current_process': {
                'name': station.current_process.name,
                'display_name': station.current_process.display_name,
                'is_looped': station.current_process.is_looped
            } if station.current_process else None,
            'quantity': station.product_quantity,
            'loop_mode': station.loop_mode,
            'clicker_enabled': station.clicker_enabled,
            'media_count': station.get_current_media().count()
        }
        workflow_status['stations'].append(station_info)
    
    return JsonResponse(workflow_status)

@csrf_exempt
@require_http_methods(["POST"])
def sync_all_displays(request):
    """Synchronize all displays to the same process step"""
    try:
        data = json.loads(request.body)
        target_stage_id = data.get('stage_id')
        target_process_id = data.get('process_id')
        
        if not target_stage_id or not target_process_id:
            return JsonResponse({'error': 'Stage ID and Process ID required'}, status=400)
        
        target_stage = get_object_or_404(AssemblyStage, id=target_stage_id)
        target_process = get_object_or_404(AssemblyProcess, id=target_process_id)
        
        # Update all stations
        stations = Station.objects.all()
        updated_stations = []
        
        for station in stations:
            station.current_stage = target_stage
            station.current_process = target_process
            
            # Handle loop mode for processes 1A, 1B, 1C
            if target_process.loop_group == 'final_assembly_1abc':
                station.loop_mode = True
            else:
                station.loop_mode = False
                
            station.save()
            updated_stations.append({
                'id': station.id,
                'name': station.name,
                'display_number': station.display_number
            })
        
        return JsonResponse({
            'success': True,
            'message': f'All displays synchronized to {target_process.display_name}',
            'updated_stations': updated_stations,
            'target_process': {
                'id': target_process.id,
                'name': target_process.name,
                'display_name': target_process.display_name,
                'stage': target_stage.display_name
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_bom_files(request, station_id):
    """Get BOM files for a specific station"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return JsonResponse({'error': 'No product selected'}, status=400)
    
    boms = BillOfMaterial.objects.filter(product=station.current_product)
    
    # Filter BOMs based on station settings
    if station.show_single_unit_bom:
        boms = boms.filter(bom_type='SINGLE_UNIT')
    elif station.show_batch_bom:
        boms = boms.filter(bom_type='BATCH_50')
    
    # Include stage-specific BOMs if in that stage
    if station.current_stage:
        stage_boms = BillOfMaterial.objects.filter(
            product=station.current_product,
            stage=station.current_stage
        )
        boms = boms.union(stage_boms)
    
    bom_data = [
        {
            'id': bom.id,
            'type': bom.get_bom_type_display(),
            'file_url': bom.file.url,
            'stage': bom.stage.display_name if bom.stage else None
        }
        for bom in boms
    ]
    
    return JsonResponse({
        'boms': bom_data,
        'station_info': {
            'display_number': station.display_number,
            'show_single_unit': station.show_single_unit_bom,
            'show_batch': station.show_batch_bom
        }
    })

# File streaming views (from your original code)
def stream_video(request, video_path):
    """Stream video files with range support"""
    clean_path = video_path.lstrip('/').replace('media/', '', 1)
    path = os.path.join(settings.MEDIA_ROOT, clean_path)
    
    if not os.path.exists(path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    range_header = request.META.get('HTTP_RANGE', '').strip()
    size = os.path.getsize(path)
    
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
    """Stream PDF files"""
    clean_path = pdf_path.lstrip('/').replace('media/', '', 1)
    path = os.path.join(settings.MEDIA_ROOT, clean_path)
    
    if not os.path.exists(path):
        return JsonResponse({'error': 'File not found'}, status=404)
    
    def file_iterator(path, chunk_size=8192):
        with open(path, 'rb') as f:
            while True:
                data = f.read(chunk_size)
                if not data:
                    break
                yield data
    
    response = StreamingHttpResponse(
        file_iterator(path),
        content_type='application/pdf'
    )
    response['Content-Length'] = os.path.getsize(path)
    return response
        
@csrf_exempt
@require_http_methods(["POST"])
def update_assembly_config(request, station_id):
    """Update BRG assembly configuration"""
    station = get_object_or_404(Station, pk=station_id)
    
    try:
        data = json.loads(request.body)
        
        # Update product
        if 'product_id' in data:
            if data['product_id']:
                product = get_object_or_404(Product, id=data['product_id'])
                if product in station.products.all():
                    station.current_product = product
                    # Reset to first stage and process when product changes
                    first_stage = AssemblyStage.objects.first()
                    station.current_stage = first_stage
                    station.current_process = first_stage.processes.first() if first_stage else None
                else:
                    return JsonResponse({'error': 'Product not available for this station'}, status=400)
        
        # Update stage
        if 'stage_id' in data:
            if data['stage_id']:
                stage = get_object_or_404(AssemblyStage, id=data['stage_id'])
                station.current_stage = stage
                # Reset to first process of new stage
                station.current_process = stage.processes.first()
        
        # Update process
        if 'process_id' in data:
            if data['process_id']:
                process = get_object_or_404(AssemblyProcess, id=data['process_id'])
                station.current_process = process
                station.current_stage = process.stage
                
                # Auto-enable loop mode for processes 1A, 1B, 1C
                if process.loop_group == 'final_assembly_1abc':
                    station.loop_mode = True
                else:
                    station.loop_mode = False
        
        # Update quantity
        if 'quantity' in data:
            quantity = int(data['quantity'])
            if quantity > 0:
                station.product_quantity = quantity
                # Update BOM display based on quantity
                if quantity == 1:
                    station.show_single_unit_bom = True
                    station.show_batch_bom = False
                else:
                    station.show_single_unit_bom = False
                    station.show_batch_bom = True
        
        # Update BOM display settings
        if 'show_single_unit_bom' in data:
            station.show_single_unit_bom = data['show_single_unit_bom']
        if 'show_batch_bom' in data:
            station.show_batch_bom = data['show_batch_bom']
            
        station.save()
        
        return JsonResponse({
            'success': True,
            'current_state': {
                'product': {
                    'id': station.current_product.id,
                    'code': station.current_product.code,
                    'name': station.current_product.name
                } if station.current_product else None,
                'stage': {
                    'id': station.current_stage.id,
                    'name': station.current_stage.display_name,
                    'order': station.current_stage.order
                } if station.current_stage else None,
                'process': {
                    'id': station.current_process.id,
                    'name': station.current_process.name,
                    'display_name': station.current_process.display_name,
                    'order': station.current_process.order
                } if station.current_process else None,
                'quantity': station.product_quantity,
                'loop_mode': station.loop_mode,
                'bom_settings': {
                    'show_single_unit': station.show_single_unit_bom,
                    'show_batch': station.show_batch_bom
                }
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    
# Add this to your views.py for debugging

# Add this to your views.py for debugging

def debug_station(request, station_id):
    """Debug view to test station setup"""
    try:
        station = Station.objects.get(pk=station_id)
        
        debug_info = {
            'station_id': station.id,
            'station_name': station.name,
            'display_number': station.display_number,
            'current_product': {
                'id': station.current_product.id if station.current_product else None,
                'code': station.current_product.code if station.current_product else None,
                'name': station.current_product.name if station.current_product else None,
            },
            'current_stage': {
                'id': station.current_stage.id if station.current_stage else None,
                'name': station.current_stage.display_name if station.current_stage else None,
            },
            'current_process': {
                'id': station.current_process.id if station.current_process else None,
                'name': station.current_process.name if station.current_process else None,
                'display_name': station.current_process.display_name if station.current_process else None,
            },
            'media_count': 0,
            'media_files': [],
            'error': None
        }
        
        # Test get_current_media
        try:
            media = station.get_current_media()
            debug_info['media_count'] = media.count()
            debug_info['media_files'] = [
                {
                    'id': m.id,
                    'file': str(m.file),
                    'type': m.media_type,
                    'display_1': m.display_screen_1,
                    'display_2': m.display_screen_2,
                    'display_3': m.display_screen_3,
                }
                for m in media
            ]
        except Exception as e:
            debug_info['error'] = str(e)
        
        return JsonResponse(debug_info)
        
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    

def station_media_stream_debug(request, station_id):
    """Simplified streaming for debugging"""
    def event_stream():
        try:
            # Test 1: Basic connection
            yield f"data: {json.dumps({'test': 'connection_ok', 'timestamp': time.time()})}\n\n"
            
            # Test 2: Get station
            station = Station.objects.get(pk=station_id)
            yield f"data: {json.dumps({'test': 'station_found', 'station_name': station.name})}\n\n"
            
            # Test 3: Get media
            current_media = station.get_current_media()
            yield f"data: {json.dumps({'test': 'media_found', 'media_count': current_media.count()})}\n\n"
            
            # Test 4: Try to serialize one media item
            if current_media.exists():
                media = current_media.first()
                media_data = {
                    'id': media.id,
                    'url': media.file.url,
                    'type': media.file.name.split('.')[-1].lower(),
                    'duration': media.duration,
                    'media_type': media.get_media_type_display(),
                }
                yield f"data: {json.dumps({'test': 'media_serialized', 'media': media_data})}\n\n"
            
            # Test 5: Full data structure
            counter = 0
            while counter < 3:  # Only run 3 times for testing
                try:
                    station = Station.objects.get(pk=station_id)
                    current_media = station.get_current_media()
                    
                    media_data = []
                    for media in current_media:
                        media_info = {
                            'id': media.id,
                            'url': media.file.url,
                            'type': media.file.name.split('.')[-1].lower(),
                            'duration': media.duration,
                            'media_type': media.get_media_type_display(),
                        }
                        
                        # Safely add process info
                        if media.process:
                            try:
                                media_info['process'] = {
                                    'id': media.process.id,
                                    'name': media.process.name,
                                    'display_name': media.process.display_name,
                                }
                            except Exception as pe:
                                media_info['process_error'] = str(pe)
                        
                        # Safely add BOM info
                        if media.bom:
                            try:
                                media_info['bom'] = {
                                    'id': media.bom.id,
                                    'type': media.bom.get_bom_type_display(),
                                }
                            except Exception as be:
                                media_info['bom_error'] = str(be)
                        
                        media_data.append(media_info)
                    
                    # Assembly info
                    assembly_info = {}
                    try:
                        if station.current_product:
                            assembly_info['current_product'] = {
                                'id': station.current_product.id,
                                'code': station.current_product.code,
                                'name': station.current_product.name
                            }
                    except Exception as pe:
                        assembly_info['product_error'] = str(pe)
                    
                    try:
                        if station.current_stage:
                            assembly_info['current_stage'] = {
                                'id': station.current_stage.id,
                                'name': station.current_stage.display_name,
                                'order': station.current_stage.order
                            }
                    except Exception as se:
                        assembly_info['stage_error'] = str(se)
                    
                    try:
                        if station.current_process:
                            assembly_info['current_process'] = {
                                'id': station.current_process.id,
                                'name': station.current_process.name,
                                'display_name': station.current_process.display_name,
                                'order': station.current_process.order,
                                'is_looped': station.current_process.is_looped,
                                'loop_group': station.current_process.loop_group
                            }
                    except Exception as pe:
                        assembly_info['process_error'] = str(pe)
                    
                    response_data = {
                        'media': media_data,
                        'station_name': station.name,
                        'assembly': assembly_info,
                        'timestamp': time.time(),
                        'counter': counter
                    }
                    
                    yield f"data: {json.dumps(response_data)}\n\n"
                    counter += 1
                    time.sleep(2)
                    
                except Exception as inner_e:
                    yield f"data: {json.dumps({'error': f'Inner loop error: {str(inner_e)}'})}\n\n"
                    break
                    
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Stream error: {str(e)}'})}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response





# views.py

from django.shortcuts import render

def supervisor_dashboard(request):
    return render(request, 'supervisor-dashboard.html')

def workflow_guide(request):
    return render(request, 'workflow-guide.html')
def workflow_guide2(request):
    return render(request, 'hindi.html')
