from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import time
from .models import (Station, Product, ProductMedia, AssemblyStage, 
                    AssemblyProcess, AssemblySession, BillOfMaterial,BOMTemplate, BOMItem, BOMTemplateItem)




# for bom 

def get_station_bom_data(request, station_id):
    """Get database BOM data for a specific station with split logic - FIXED"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return JsonResponse({'error': 'No product selected'}, status=400)
    
    # Get BOM data based on station settings and display number
    bom_data = station.get_current_bom_data()
    
    if not bom_data:
        return JsonResponse({'error': 'No BOM data available'}, status=404)
    
    # Get BOM info for display context
    bom_info = station.get_current_bom_info()
    
    # Format BOM data for frontend
    formatted_bom = []
    for item_data in bom_data:
        item_info = {
            'serial_number': item_data['serial_number'],
            'item_code': item_data['item'].item_code,
            'item_description': item_data['item'].item_description,
            'part_number': item_data['item'].part_number,
            'unit_of_measure': item_data['item'].unit_of_measure,
            'base_quantity': item_data['base_quantity'],
            'calculated_quantity': item_data['calculated_quantity'],
            'formatted_quantity': item_data['formatted_quantity'],
            'notes': item_data['notes'],
            'item_photo_url': item_data['item'].item_photo.url if item_data['item'].item_photo else None,
            'supplier': item_data['item'].supplier,
            'cost_per_unit': float(item_data['item'].cost_per_unit) if item_data['item'].cost_per_unit else None,
        }
        formatted_bom.append(item_info)
    
    # Determine BOM type and quantity
    if station.show_single_unit_bom:
        bom_type = 'SINGLE_UNIT'
        quantity = 1
    elif station.show_batch_bom:
        bom_type = 'BATCH_50'
        quantity = station.product_quantity
    else:
        bom_type = station.current_stage.name if station.current_stage else None
        quantity = station.product_quantity
    
    # FIXED: Get BOM template information without model objects
    bom_template_info = None
    try:
        bom_template = BOMTemplate.objects.get(
            product=station.current_product,
            bom_type=bom_type,
            is_active=True
        )
        bom_template_info = {
            'id': bom_template.id,
            'name': bom_template.template_name,
            'bom_type': bom_template.get_bom_type_display(),
            'stage': bom_template.stage.display_name if bom_template.stage else None,
            'description': bom_template.description,
            'is_split': bom_info['is_split'] if bom_info else False,
            'display_info': bom_info['display_info'] if bom_info else None,
            'split_info': bom_info.get('split_info') if bom_info else None,
        }
    except BOMTemplate.DoesNotExist:
        pass
    
    # FIXED: Serialize bom_info properly
    serialized_bom_info = {}
    if bom_info:
        for key, value in bom_info.items():
            if hasattr(value, 'id'):  # It's a model object
                if hasattr(value, 'template_name'):  # BOMTemplate
                    serialized_bom_info[key] = {
                        'id': value.id,
                        'name': value.template_name,
                        'bom_type': value.bom_type,
                    }
                elif hasattr(value, 'display_name'):  # AssemblyStage
                    serialized_bom_info[key] = {
                        'id': value.id,
                        'name': value.name,
                        'display_name': value.display_name,
                    }
                else:
                    serialized_bom_info[key] = str(value)
            else:
                serialized_bom_info[key] = value
    
    return JsonResponse({
        'bom_data': formatted_bom,
        'bom_template': bom_template_info,
        'station_info': {
            'name': station.name,
            'display_number': station.display_number,
            'product_code': station.current_product.code,
            'product_name': station.current_product.name,
            'quantity': quantity,
            'bom_type': bom_type,
            'is_split_bom': bom_info['is_split'] if bom_info else False,
            'display_info': bom_info['display_info'] if bom_info else None,
            'bom_info': serialized_bom_info,  # FIXED: Use serialized version
        },
        'summary': {
            'total_items': len(formatted_bom),
            'total_cost': sum(
                item['calculated_quantity'] * (item['cost_per_unit'] or 0) 
                for item in formatted_bom
            ),
            'display_context': f"Display {station.display_number}" + (
                f" - {bom_info['display_info']}" if bom_info and bom_info.get('display_info') else ""
            )
        }
    })
    
def render_bom_display(request, station_id):
    """Render BOM display page for a station with split logic"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get BOM data for this specific display
    bom_data = station.get_current_bom_data() if station.current_product else []
    bom_info = station.get_current_bom_info()
    
    # Determine BOM type and quantity
    if station.show_single_unit_bom:
        bom_type = 'Single Unit'
        if bom_info and bom_info['is_split']:
            bom_type += f" (Display {station.display_number})"
        quantity = 1
    elif station.show_batch_bom:
        bom_type = f'{station.product_quantity} Units Batch'
        if bom_info and bom_info['is_split']:
            bom_type += f" (Display {station.display_number})"
        quantity = station.product_quantity
    else:
        bom_type = station.current_stage.display_name if station.current_stage else 'Unknown'
        quantity = station.product_quantity
    
    # Add split information to context
    split_context = {}
    if bom_info and bom_info.get('is_split'):
        split_context = {
            'is_split': True,
            'display_info': bom_info.get('display_info', ''),
            'split_info': bom_info.get('split_info', {}),
            'current_display': station.display_number
        }
    
    context = {
        'station': station,
        'bom_data': bom_data,
        'bom_type': bom_type,
        'quantity': quantity,
        'product': station.current_product,
        'stage': station.current_stage,
        'process': station.current_process,
        'split_context': split_context,
    }
    
    return render(request, 'bom_display.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def update_bom_settings(request, station_id):
    """Update BOM display settings for a station"""
    station = get_object_or_404(Station, pk=station_id)
    
    try:
        data = json.loads(request.body)
        
        # Update BOM display settings
        if 'show_single_unit_bom' in data:
            station.show_single_unit_bom = data['show_single_unit_bom']
        if 'show_batch_bom' in data:
            station.show_batch_bom = data['show_batch_bom']
        if 'product_quantity' in data:
            quantity = int(data['product_quantity'])
            if quantity > 0:
                station.product_quantity = quantity
        
        station.save()
        
        # Get updated BOM data
        bom_data = station.get_current_bom_data()
        
        return JsonResponse({
            'success': True,
            'message': 'BOM settings updated successfully',
            'current_settings': {
                'show_single_unit_bom': station.show_single_unit_bom,
                'show_batch_bom': station.show_batch_bom,
                'product_quantity': station.product_quantity,
            },
            'bom_item_count': len(bom_data) if bom_data else 0,
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid quantity value'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_bom_templates(request):
    """Get all available BOM templates"""
    templates = BOMTemplate.objects.filter(is_active=True).select_related('product', 'stage')
    
    templates_data = []
    for template in templates:
        template_info = {
            'id': template.id,
            'name': template.template_name,
            'product_code': template.product.code,
            'product_name': template.product.name,
            'bom_type': template.bom_type,
            'bom_type_display': template.get_bom_type_display(),
            'stage': template.stage.name if template.stage else None,
            'stage_display': template.stage.display_name if template.stage else None,
            'description': template.description,
            'item_count': template.bom_items.filter(is_active=True).count(),
            'displays': {
                'screen_1': template.display_screen_1,
                'screen_2': template.display_screen_2,
                'screen_3': template.display_screen_3,
            },
            'created_date': template.created_date.isoformat(),
        }
        templates_data.append(template_info)
    
    return JsonResponse({
        'templates': templates_data,
        'total_count': len(templates_data),
    })

def preview_bom_template(request, template_id):
    """Preview BOM template for different quantities"""
    template = get_object_or_404(BOMTemplate, pk=template_id)
    quantity = int(request.GET.get('quantity', 1))
    
    # Generate BOM data for the specified quantity
    bom_data = template.generate_bom_for_quantity(quantity)
    
    # Format for JSON response
    formatted_bom = []
    total_cost = 0
    
    for item_data in bom_data:
        item_cost = (item_data['calculated_quantity'] * 
                    (item_data['item'].cost_per_unit or 0))
        total_cost += item_cost
        
        item_info = {
            'serial_number': item_data['serial_number'],
            'item_code': item_data['item'].item_code,
            'item_description': item_data['item'].item_description,
            'part_number': item_data['item'].part_number,
            'unit_of_measure': item_data['item'].unit_of_measure,
            'base_quantity': item_data['base_quantity'],
            'calculated_quantity': item_data['calculated_quantity'],
            'formatted_quantity': item_data['formatted_quantity'],
            'notes': item_data['notes'],
            'cost_per_unit': float(item_data['item'].cost_per_unit) if item_data['item'].cost_per_unit else None,
            'line_cost': float(item_cost),
            'supplier': item_data['item'].supplier,
            'item_photo_url': item_data['item'].item_photo.url if item_data['item'].item_photo else None,
        }
        formatted_bom.append(item_info)
    
    return JsonResponse({
        'template': {
            'id': template.id,
            'name': template.template_name,
            'bom_type': template.get_bom_type_display(),
            'product': {
                'code': template.product.code,
                'name': template.product.name,
            },
            'stage': template.stage.display_name if template.stage else None,
            'description': template.description,
        },
        'quantity': quantity,
        'bom_data': formatted_bom,
        'summary': {
            'total_items': len(formatted_bom),
            'total_cost': float(total_cost),
            'unique_suppliers': len(set(
                item['supplier'] for item in formatted_bom 
                if item['supplier']
            )),
        }
    })

def get_bom_items(request):
    """Get all BOM items with search and filtering"""
    items = BOMItem.objects.filter(is_active=True)
    
    # Search functionality
    search = request.GET.get('search', '').strip()
    if search:
        items = items.filter(
            item_description__icontains=search
        ) | items.filter(
            item_code__icontains=search
        ) | items.filter(
            part_number__icontains=search
        )
    
    # Filter by unit
    unit_filter = request.GET.get('unit')
    if unit_filter:
        items = items.filter(unit_of_measure=unit_filter)
    
    # Filter by supplier
    supplier_filter = request.GET.get('supplier')
    if supplier_filter:
        items = items.filter(supplier__icontains=supplier_filter)
    
    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    start = (page - 1) * per_page
    end = start + per_page
    
    total_count = items.count()
    items_page = items[start:end]
    
    items_data = []
    for item in items_page:
        item_info = {
            'id': item.id,
            'item_code': item.item_code,
            'item_description': item.item_description,
            'part_number': item.part_number,
            'unit_of_measure': item.unit_of_measure,
            'supplier': item.supplier,
            'cost_per_unit': float(item.cost_per_unit) if item.cost_per_unit else None,
            'weight_per_unit': float(item.weight_per_unit) if item.weight_per_unit else None,
            'item_photo_url': item.item_photo.url if item.item_photo else None,
            'created_date': item.created_date.isoformat(),
            'is_active': item.is_active,
        }
        items_data.append(item_info)
    
    return JsonResponse({
        'items': items_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page,
            'has_next': end < total_count,
            'has_prev': page > 1,
        },
        'filters': {
            'search': search,
            'unit': unit_filter,
            'supplier': supplier_filter,
        }
    })




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
    """Enhanced clicker action handling for BRG workflow - SYNCS ALL STATIONS"""
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
                exit_loop_mode = False
                if (station.loop_mode and 
                    station.current_process and 
                    station.current_process.loop_group == 'final_assembly_1abc' and
                    next_process.name == 'PROCESS 2 OF 6'):
                    exit_loop_mode = True
                
                # UPDATE ALL STATIONS - not just the current one
                all_stations = Station.objects.all()
                updated_stations = []
                
                for st in all_stations:
                    # Skip stations that don't have the same product (optional check)
                    if st.current_product != station.current_product:
                        continue
                        
                    st.current_process = next_process
                    
                    # Update stage if process belongs to different stage
                    if next_process.stage != st.current_stage:
                        st.current_stage = next_process.stage
                    
                    # Apply loop mode changes to all stations
                    if exit_loop_mode:
                        st.loop_mode = False
                    
                    st.save()
                    updated_stations.append({
                        'id': st.id,
                        'name': st.name,
                        'display_number': st.display_number
                    })
                
                return JsonResponse({
                    'success': True,
                    'message': f'All stations moved to {next_process.display_name}',
                    'current_process': {
                        'id': next_process.id,
                        'name': next_process.name,
                        'display_name': next_process.display_name,
                        'stage': next_process.stage.display_name,
                        'is_looped': next_process.is_looped
                    },
                    'loop_mode': not exit_loop_mode and station.loop_mode,
                    'updated_stations': updated_stations,
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
                # UPDATE ALL STATIONS
                all_stations = Station.objects.all()
                updated_stations = []
                
                for st in all_stations:
                    # Skip stations that don't have the same product (optional check)
                    if st.current_product != station.current_product:
                        continue
                        
                    st.current_process = previous_process
                    
                    # Update stage if process belongs to different stage
                    if previous_process.stage != st.current_stage:
                        st.current_stage = previous_process.stage
                    
                    st.save()
                    updated_stations.append({
                        'id': st.id,
                        'name': st.name,
                        'display_number': st.display_number
                    })
                
                return JsonResponse({
                    'success': True,
                    'message': f'All stations moved to {previous_process.display_name}',
                    'current_process': {
                        'id': previous_process.id,
                        'name': previous_process.name,
                        'display_name': previous_process.display_name,
                        'stage': previous_process.stage.display_name,
                        'is_looped': previous_process.is_looped
                    },
                    'updated_stations': updated_stations
                })
            else:
                return JsonResponse({'error': 'No previous process available'}, status=400)
                
        elif action == 'toggle_loop':
            # Toggle loop mode for processes 1A, 1B, 1C on ALL stations
            if (station.current_process and 
                station.current_process.loop_group == 'final_assembly_1abc'):
                
                new_loop_mode = not station.loop_mode
                
                # UPDATE ALL STATIONS
                all_stations = Station.objects.all()
                updated_stations = []
                
                for st in all_stations:
                    # Only update stations with the same product and in loop processes
                    if (st.current_product == station.current_product and
                        st.current_process and 
                        st.current_process.loop_group == 'final_assembly_1abc'):
                        st.loop_mode = new_loop_mode
                        st.save()
                        updated_stations.append({
                            'id': st.id,
                            'name': st.name,
                            'display_number': st.display_number
                        })
                
                return JsonResponse({
                    'success': True,
                    'loop_mode': new_loop_mode,
                    'message': f"Loop mode {'enabled' if new_loop_mode else 'disabled'} on all stations",
                    'updated_stations': updated_stations
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
    """Enhanced assembly configuration with proper BOM stage handling"""
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
                
                # Auto-configure BOM settings based on stage
                if stage.name == 'BOM_DISPLAY':
                    # Set default BOM display based on quantity
                    if station.product_quantity == 1:
                        station.show_single_unit_bom = True
                        station.show_batch_bom = False
                    else:
                        station.show_single_unit_bom = False
                        station.show_batch_bom = True
        
        # Update process
        if 'process_id' in data:
            if data['process_id']:
                process = get_object_or_404(AssemblyProcess, id=data['process_id'])
                station.current_process = process
                station.current_stage = process.stage
                
                # Handle BOM-specific processes
                if process.stage.name == 'BOM_DISPLAY':
                    if process.name == 'SINGLE_UNIT_BOM_DISPLAY':
                        station.show_single_unit_bom = True
                        station.show_batch_bom = False
                        station.product_quantity = 1
                    elif process.name == 'BATCH_50_BOM_DISPLAY':
                        station.show_single_unit_bom = False
                        station.show_batch_bom = True
                        if station.product_quantity < 2:
                            station.product_quantity = 50
                    elif process.name == 'STAGE_BOM_DISPLAY':
                        station.show_single_unit_bom = False
                        station.show_batch_bom = False
                
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
                # Auto-adjust BOM display based on quantity
                if station.current_stage and station.current_stage.name == 'BOM_DISPLAY':
                    if quantity == 1:
                        station.show_single_unit_bom = True
                        station.show_batch_bom = False
                    else:
                        station.show_single_unit_bom = False
                        station.show_batch_bom = True
        
        # Update BOM display settings
        if 'show_single_unit_bom' in data:
            station.show_single_unit_bom = data['show_single_unit_bom']
            if data['show_single_unit_bom']:
                station.show_batch_bom = False
                station.product_quantity = 1
                
        if 'show_batch_bom' in data:
            station.show_batch_bom = data['show_batch_bom']
            if data['show_batch_bom']:
                station.show_single_unit_bom = False
                if station.product_quantity < 2:
                    station.product_quantity = 50
            
        station.save()
        
        # Get updated BOM data for response
        bom_data = station.get_current_bom_data()
        bom_info = station.get_current_bom_info()
        
        return JsonResponse({
            'success': True,
            'message': 'Configuration updated successfully',
            'current_state': {
                'product': {
                    'id': station.current_product.id,
                    'code': station.current_product.code,
                    'name': station.current_product.name
                } if station.current_product else None,
                'stage': {
                    'id': station.current_stage.id,
                    'name': station.current_stage.display_name,
                    'order': station.current_stage.order,
                    'is_bom_stage': station.current_stage.name == 'BOM_DISPLAY'
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
                },
                'bom_data_available': bool(bom_data),
                'bom_item_count': len(bom_data) if bom_data else 0,
                'bom_is_split': bom_info.get('is_split', False) if bom_info else False,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        return JsonResponse({'error': f'Invalid value: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


    
def station_media_stream_enhanced(request, station_id):
    """Enhanced streaming with BOM data support"""
    def event_stream():
        last_update = None
        while True:
            try:
                station = get_object_or_404(Station, pk=station_id)
                current_media = station.get_current_media()
                bom_data = station.get_current_bom_data()
                
                # Create comprehensive comparison data including BOM
                media_comparison = []
                for media in current_media:
                    comparison_item = {
                        'id': media.id,
                        'file_url': media.file.url if media.file else None,
                        'media_type': media.media_type,
                        'process_id': media.process.id if media.process else None,
                        'bom_id': media.bom.id if media.bom else None
                    }
                    media_comparison.append(comparison_item)
                
                # Include BOM data in comparison
                bom_comparison = []
                if bom_data:
                    for item_data in bom_data:
                        bom_comparison.append({
                            'item_code': item_data['item'].item_code,
                            'calculated_quantity': item_data['calculated_quantity'],
                            'serial_number': item_data['serial_number']
                        })
                
                # Include assembly state in comparison
                assembly_state = {
                    'current_product_id': station.current_product.id if station.current_product else None,
                    'current_stage_id': station.current_stage.id if station.current_stage else None,
                    'current_process_id': station.current_process.id if station.current_process else None,
                    'product_quantity': station.product_quantity,
                    'loop_mode': station.loop_mode,
                    'display_number': station.display_number,
                    'show_single_unit_bom': station.show_single_unit_bom,
                    'show_batch_bom': station.show_batch_bom,
                }
                
                current_state = {
                    'media': media_comparison,
                    'bom': bom_comparison,
                    'assembly': assembly_state
                }
                
                # Only send update if something changed
                if current_state != last_update:
                    # Prepare detailed media data for frontend
                    media_data = []
                    for media in current_media:
                        media_info = {
                            'id': media.id,
                            'url': media.file.url if media.file else None,
                            'type': media.file.name.split('.')[-1].lower() if media.file else 'bom',
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
                    
                    # Prepare BOM data for frontend
                    formatted_bom = []
                    if bom_data:
                        for item_data in bom_data:
                            formatted_bom.append({
                                'serial_number': item_data['serial_number'],
                                'item_code': item_data['item'].item_code,
                                'item_description': item_data['item'].item_description,
                                'part_number': item_data['item'].part_number,
                                'formatted_quantity': item_data['formatted_quantity'],
                                'notes': item_data['notes'],
                                'item_photo_url': item_data['item'].item_photo.url if item_data['item'].item_photo else None,
                                'supplier': item_data['item'].supplier,
                            })
                    
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
                        'bom_settings': {
                            'show_single_unit': station.show_single_unit_bom,
                            'show_batch': station.show_batch_bom,
                        },
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
                        'bom_data': formatted_bom,
                        'station_name': station.name,
                        'assembly': assembly_info,
                        'timestamp': time.time()
                    }
                    
                    last_update = current_state
                    yield f"data: {json.dumps(response_data)}\n\n"
                
                time.sleep(3)  # Check every 3 seconds
                
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



def get_station_media_with_bom(request, station_id):
    """Enhanced station media API that handles split BOM properly for all displays - FIXED"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get regular media (excluding PDF BOMs when we have database BOM)
    current_media = station.get_current_media()
    
    media_data = []
    
    # Check if we have database BOM data for this specific display
    bom_data = station.get_current_bom_data() if station.current_product else []
    bom_info = station.get_current_bom_info()
    has_database_bom = bool(bom_data)
    
    print(f"Station {station_id} Display {station.display_number}:")
    print(f"  - Has BOM data: {has_database_bom}")
    print(f"  - BOM items count: {len(bom_data) if bom_data else 0}")
    print(f"  - Current stage: {station.current_stage.name if station.current_stage else None}")
    
    # ALWAYS add database BOM as first item if we have data and are in BOM stage
    if (has_database_bom and station.current_stage and 
        station.current_stage.name == 'BOM_DISPLAY'):
        
        # Determine BOM display type
        bom_display_type = "Database BOM"
        if station.show_single_unit_bom:
            bom_display_type = "Single Unit BOM"
        elif station.show_batch_bom:
            bom_display_type = f"{station.product_quantity} Units BOM"
        elif station.current_stage:
            bom_display_type = f"{station.current_stage.display_name} BOM"
        
        # Add split information if applicable
        display_suffix = ""
        items_for_display = len(bom_data)
        
        if bom_info and bom_info.get('is_split'):
            split_info = bom_info.get('split_info', {})
            current_display_info = split_info.get(f'display_{station.display_number}', {})
            items_for_display = current_display_info.get('item_count', 0)
            
            if items_for_display > 0:
                display_suffix = f" (Part {station.display_number}/3 - {items_for_display} items)"
            else:
                display_suffix = f" (Display {station.display_number}/3 - No items)"
        
        bom_media_info = {
            'id': f'database_bom_{station.id}',
            'url': f'/station/{station.id}/bom-render/',
            'type': 'bom',
            'duration': 30,
            'media_type': f'Database BOM',
            'product_name': station.current_product.name,
            'product_code': station.current_product.code,
            'is_bom_data': True,
            'bom_items': items_for_display,  # Items for THIS display
            'bom_type': bom_display_type + display_suffix,
            'is_split': bom_info.get('is_split', False) if bom_info else False,
            'display_info': bom_info.get('display_info', '') if bom_info else '',
        }
        
        media_data.append(bom_media_info)
        print(f"  - Added BOM media: {bom_media_info['bom_type']}")
        
        # Filter out PDF BOMs from regular media when we have database BOM
        filtered_media = current_media.exclude(media_type='Bill of Material')
        
        # Add remaining non-BOM media
        for media in filtered_media:
            media_info = {
                'id': media.id,
                'url': media.file.url if media.file else None,
                'type': media.file.name.split('.')[-1].lower() if media.file else 'unknown',
                'duration': media.duration,
                'media_type': media.get_media_type_display(),
                'product_name': media.product.name,
                'product_code': media.product.code,
                'is_bom_data': False,
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
            
            media_data.append(media_info)
    
    else:
        print(f"  - Not adding BOM: stage={station.current_stage.name if station.current_stage else None}, has_bom={has_database_bom}")
        
        # Regular media handling for non-BOM stages
        for media in current_media:
            media_info = {
                'id': media.id,
                'url': media.file.url if media.file else None,
                'type': media.file.name.split('.')[-1].lower() if media.file else 'unknown',
                'duration': media.duration,
                'media_type': media.get_media_type_display(),
                'product_name': media.product.name,
                'product_code': media.product.code,
                'is_bom_data': False,
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
            
            media_data.append(media_info)
    
    # FIXED: Properly serialize BOM info without model objects
    serialized_bom_info = None
    if bom_info:
        # Convert any model objects to serializable data
        serialized_bom_info = {}
        for key, value in bom_info.items():
            if key == 'template' and value:
                # Convert BOMTemplate to serializable dict
                serialized_bom_info['template'] = {
                    'id': value.id,
                    'name': value.template_name,
                    'bom_type': value.bom_type,
                    'description': value.description,
                    'product_id': value.product.id,
                    'product_code': value.product.code,
                    'stage_id': value.stage.id if value.stage else None,
                    'stage_name': value.stage.name if value.stage else None,
                }
            elif key == 'stage' and value:
                # Convert AssemblyStage to serializable dict
                serialized_bom_info['stage'] = {
                    'id': value.id,
                    'name': value.name,
                    'display_name': value.display_name,
                    'order': value.order,
                }
            else:
                # Copy primitive values as-is
                serialized_bom_info[key] = value
    
    response_data = {
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
            'clicker_enabled': station.clicker_enabled,
            'bom_settings': {
                'show_single_unit': station.show_single_unit_bom,
                'show_batch': station.show_batch_bom,
            },
            'bom_split_info': serialized_bom_info,  # FIXED: Use serialized version
            'has_database_bom': has_database_bom,
            'is_bom_stage': (station.current_stage and 
                           station.current_stage.name == 'BOM_DISPLAY')
        }
    }
    
    print(f"  - Returning {len(media_data)} media items")
    return JsonResponse(response_data)
  
def render_bom_for_slider(request, station_id):
    """Render BOM as HTML fragment for slider integration with enhanced split logic"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return HttpResponse('''
            <div class="bom-container-slider">
                <div class="no-bom-data-slider">
                    <div class="no-bom-icon-slider">📋</div>
                    <h3>No Product Selected</h3>
                    <p>Please select a product to view BOM data</p>
                </div>
            </div>
        ''')
    
    bom_data = station.get_current_bom_data()
    
    if not bom_data:
        return HttpResponse('''
            <div class="bom-container-slider">
                <div class="no-bom-data-slider">
                    <div class="no-bom-icon-slider">📋</div>
                    <h3>No BOM Data Available</h3>
                    <p>No bill of materials configured for current settings</p>
                    <p>Check BOM templates in admin panel</p>
                </div>
            </div>
        ''')
    
    bom_info = station.get_current_bom_info()
    
    # Determine BOM type and quantity with split information
    if station.show_single_unit_bom:
        bom_type = 'Single Unit'
        quantity = 1
    elif station.show_batch_bom:
        bom_type = f'{station.product_quantity} Units'
        quantity = station.product_quantity
    else:
        bom_type = station.current_stage.display_name if station.current_stage else 'Stage BOM'
        quantity = station.product_quantity
    
    # Add split information for display
    split_context = {'is_split': False}
    if bom_info and bom_info.get('is_split'):
        split_info = bom_info.get('split_info', {})
        current_display_info = split_info.get(f'display_{station.display_number}', {})
        
        split_context = {
            'is_split': True,
            'display_info': bom_info.get('display_info', ''),
            'current_display': station.display_number,
            'item_count': current_display_info.get('item_count', 0),
            'start_serial': current_display_info.get('start_serial', 0),
            'end_serial': current_display_info.get('end_serial', 0),
        }
        
        if current_display_info.get('item_count', 0) > 0:
            bom_type += f" (Items {current_display_info['start_serial']}-{current_display_info['end_serial']})"
        else:
            bom_type += " (No items for this display)"
    
    context = {
        'station': station,
        'bom_data': bom_data,
        'bom_type': bom_type,
        'quantity': quantity,
        'product': station.current_product,
        'stage': station.current_stage,
        'bom_info': bom_info,
        'is_split': split_context['is_split'],
        'split_context': split_context,
        'has_bom_data': bool(bom_data),
    }
    
    return render(request, 'bom_slider_fragment.html', context)

 
# BOM Management Dashboard
def bom_management_dashboard(request):
    """BOM management dashboard"""
    context = {
        'total_items': BOMItem.objects.filter(is_active=True).count(),
        'total_templates': BOMTemplate.objects.filter(is_active=True).count(),
        'total_products': Product.objects.count(),
        'recent_items': BOMItem.objects.filter(is_active=True).order_by('-created_date')[:10],
        'recent_templates': BOMTemplate.objects.filter(is_active=True).order_by('-created_date')[:5],
        'templates_by_type': {},
    }
    
    # Group templates by type
    templates = BOMTemplate.objects.filter(is_active=True).select_related('product', 'stage')
    for template in templates:
        if template.bom_type not in context['templates_by_type']:
            context['templates_by_type'][template.bom_type] = []
        context['templates_by_type'][template.bom_type].append(template)
    
    return render(request, 'bom_management_dashboard.html', context)

def bom_item_management(request):
    """BOM item management page"""
    search = request.GET.get('search', '').strip()
    unit_filter = request.GET.get('unit', '')
    supplier_filter = request.GET.get('supplier', '')
    
    items = BOMItem.objects.filter(is_active=True)
    
    if search:
        items = items.filter(
            item_description__icontains=search
        ) | items.filter(
            item_code__icontains=search
        ) | items.filter(
            part_number__icontains=search
        )
    
    if unit_filter:
        items = items.filter(unit_of_measure=unit_filter)
    
    if supplier_filter:
        items = items.filter(supplier__icontains=supplier_filter)
    
    items = items.order_by('item_description')
    
    # Get filter options
    units = BOMItem.objects.filter(is_active=True).values_list('unit_of_measure', flat=True).distinct()
    suppliers = BOMItem.objects.filter(is_active=True, supplier__isnull=False).exclude(supplier='').values_list('supplier', flat=True).distinct()
    
    context = {
        'items': items,
        'search': search,
        'unit_filter': unit_filter,
        'supplier_filter': supplier_filter,
        'units': sorted(units),
        'suppliers': sorted(suppliers),
        'total_items': items.count(),
    }
    
    return render(request, 'bom_item_management.html', context)


def bom_template_management(request):
    """BOM template management page"""
    templates = BOMTemplate.objects.filter(is_active=True).select_related('product', 'stage').prefetch_related('bom_items__item')
    
    context = {
        'templates': templates,
        'products': Product.objects.all(),
        'stages': AssemblyStage.objects.all(),
    }
    
    return render(request, 'bom_template_management.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def bulk_update_bom_items(request):
    """Bulk update BOM items via AJAX"""
    try:
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        updated_count = 0
        for update in updates:
            item_id = update.get('id')
            if not item_id:
                continue
                
            try:
                item = BOMItem.objects.get(id=item_id)
                
                # Update fields if provided
                if 'cost_per_unit' in update:
                    item.cost_per_unit = update['cost_per_unit']
                if 'supplier' in update:
                    item.supplier = update['supplier']
                if 'is_active' in update:
                    item.is_active = update['is_active']
                    
                item.save()
                updated_count += 1
                
            except BOMItem.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'Updated {updated_count} items successfully',
            'updated_count': updated_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def export_all_bom_items_csv(request):
    """Export all BOM items to CSV"""
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_bom_items.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Item Code', 'Description', 'Part Number', 'Unit', 
        'Supplier', 'Cost per Unit', 'Weight per Unit', 'Active', 'Created Date'
    ])
    
    items = BOMItem.objects.all().order_by('item_code')
    for item in items:
        writer.writerow([
            item.item_code,
            item.item_description,
            item.part_number,
            item.unit_of_measure,
            item.supplier or '',
            item.cost_per_unit or '',
            item.weight_per_unit or '',
            'Yes' if item.is_active else 'No',
            item.created_date.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response

def station_media_slider_enhanced(request, station_id):
    """Enhanced media slider with BOM integration"""
    station = get_object_or_404(Station, pk=station_id)
    request.session['last_station_id'] = station_id

    # Get current media for this display
    current_media = station.get_current_media()
    
    # Get BOM data if available
    bom_data = station.get_current_bom_data()
    has_bom_data = bool(bom_data )
    
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
        'has_bom_data': has_bom_data,
        'bom_item_count': len(bom_data) if bom_data else 0,
    }
    
    return render(request, 'brg_station_slider_enhanced.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def quick_add_bom_item(request):
    """Quick add BOM item via AJAX"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['item_code', 'item_description', 'part_number']
        if not all(field in data for field in required_fields):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Check if item already exists
        if BOMItem.objects.filter(item_code=data['item_code']).exists():
            return JsonResponse({'error': 'Item code already exists'}, status=400)
        
        item = BOMItem.objects.create(
            item_code=data['item_code'],
            item_description=data['item_description'],
            part_number=data['part_number'],
            unit_of_measure=data.get('unit_of_measure', 'NO.'),
            supplier=data.get('supplier', ''),
            cost_per_unit=data.get('cost_per_unit'),
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Item created successfully',
            'item': {
                'id': item.id,
                'item_code': item.item_code,
                'item_description': item.item_description,
                'part_number': item.part_number,
                'unit_of_measure': item.unit_of_measure,
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def export_bom_csv(request, template_id):
    """Export BOM template to CSV"""
    import csv
    from django.http import HttpResponse
    
    template = get_object_or_404(BOMTemplate, pk=template_id)
    quantity = int(request.GET.get('quantity', 1))
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{template.template_name}_qty_{quantity}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow([
        'S.NO', 'Item Code', 'Item Description', 'Part Number', 
        'Quantity', 'Unit', 'Supplier', 'Cost per Unit', 'Line Cost', 'Notes'
    ])
    
    # Write BOM data
    bom_data = template.generate_bom_for_quantity(quantity)
    total_cost = 0
    
    for item_data in bom_data:
        line_cost = (item_data['calculated_quantity'] * 
                    (item_data['item'].cost_per_unit or 0))
        total_cost += line_cost
        
        writer.writerow([
            item_data['serial_number'],
            item_data['item'].item_code,
            item_data['item'].item_description,
            item_data['item'].part_number,
            item_data['calculated_quantity'],
            item_data['item'].unit_of_measure,
            item_data['item'].supplier or '',
            item_data['item'].cost_per_unit or '',
            f"{line_cost:.2f}" if line_cost > 0 else '',
            item_data['notes'] or '',
        ])
    
    # Write summary
    writer.writerow([])
    writer.writerow(['Summary'])
    writer.writerow(['Total Items:', len(bom_data)])
    writer.writerow(['Total Cost:', f"{total_cost:.2f}"])
    writer.writerow(['Quantity:', quantity])
    writer.writerow(['Template:', template.template_name])
    writer.writerow(['Product:', f"{template.product.code} - {template.product.name}"])
    writer.writerow(['Generated:', time.strftime('%Y-%m-%d %H:%M:%S')])
    
    return response




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




def debug_bom_stage(request, station_id):
    """Debug endpoint to check BOM stage configuration"""
    try:
        station = Station.objects.get(pk=station_id)
        
        # Check BOM stage and processes
        bom_stage = None
        bom_processes = []
        try:
            bom_stage = AssemblyStage.objects.get(name='BOM_DISPLAY')
            bom_processes = list(bom_stage.processes.all().values(
                'id', 'name', 'display_name', 'order'
            ))
        except AssemblyStage.DoesNotExist:
            pass
        
        # Check current BOM data
        bom_data = station.get_current_bom_data() if station.current_product else []
        bom_info = station.get_current_bom_info()
        
        # Check BOM templates
        bom_templates = []
        if station.current_product:
            from .models import BOMTemplate
            templates = BOMTemplate.objects.filter(
                product=station.current_product,
                is_active=True
            ).values('id', 'template_name', 'bom_type', 'stage__name')
            bom_templates = list(templates)
        
        debug_info = {
            'station': {
                'id': station.id,
                'name': station.name,
                'display_number': station.display_number,
                'current_product': {
                    'id': station.current_product.id if station.current_product else None,
                    'code': station.current_product.code if station.current_product else None,
                    'name': station.current_product.name if station.current_product else None,
                },
                'current_stage': {
                    'id': station.current_stage.id if station.current_stage else None,
                    'name': station.current_stage.name if station.current_stage else None,
                    'display_name': station.current_stage.display_name if station.current_stage else None,
                    'is_bom_stage': (station.current_stage and 
                                   station.current_stage.name == 'BOM_DISPLAY')
                },
                'current_process': {
                    'id': station.current_process.id if station.current_process else None,
                    'name': station.current_process.name if station.current_process else None,
                    'display_name': station.current_process.display_name if station.current_process else None,
                },
                'bom_settings': {
                    'show_single_unit': station.show_single_unit_bom,
                    'show_batch': station.show_batch_bom,
                    'product_quantity': station.product_quantity,
                }
            },
            'bom_stage': {
                'exists': bom_stage is not None,
                'stage_data': {
                    'id': bom_stage.id if bom_stage else None,
                    'name': bom_stage.name if bom_stage else None,
                    'display_name': bom_stage.display_name if bom_stage else None,
                } if bom_stage else None,
                'processes': bom_processes,
                'process_count': len(bom_processes)
            },
            'bom_data': {
                'available': bool(bom_data),
                'item_count': len(bom_data) if bom_data else 0,
                'is_split': bom_info.get('is_split', False) if bom_info else False,
                'display_info': bom_info.get('display_info', '') if bom_info else '',
                'bom_info': bom_info,
            },
            'bom_templates': {
                'available': len(bom_templates) > 0,
                'count': len(bom_templates),
                'templates': bom_templates,
            },
            'recommendations': []
        }
        
        # Add recommendations
        if not bom_stage:
            debug_info['recommendations'].append(
                "Create BOM_DISPLAY stage with processes for single unit, batch, and stage BOMs"
            )
        
        if not bom_data and station.current_product:
            debug_info['recommendations'].append(
                f"Create BOM templates for product {station.current_product.code}"
            )
        
        if station.current_stage and station.current_stage.name == 'BOM_DISPLAY' and not bom_data:
            debug_info['recommendations'].append(
                "Configure BOM templates or check station BOM settings"
            )
        
        return JsonResponse(debug_info, json_dumps_params={'indent': 2})
        
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)






