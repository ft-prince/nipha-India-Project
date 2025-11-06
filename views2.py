import math
import time
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

from .models import (Station, Product, ProductMedia, AssemblyStage, 
                    AssemblyProcess, AssemblySession, BillOfMaterial,BOMTemplate, BOMItem, BOMTemplateItem)

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache


# Bom with pagination 
# Improved BOM Pagination Implementation

import math
import time
from django.core.cache import cache
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


class BOMPaginator:
    """Handle BOM pagination logic - FIXED for pre-split data from Station"""
    
    def __init__(self, bom_data, mode='split', items_per_screen=8):
        self.bom_data = bom_data or []
        self.mode = mode  # 'split' or 'single'
        self.items_per_screen = items_per_screen
        self.total_items = len(self.bom_data)
        
        print(f"DEBUG PAGINATOR: Initialized with {self.total_items} items (pre-split data)")
        
        # IMPORTANT: Since Station.get_current_bom_data() already handles display splitting,
        # we don't need to do additional splitting here. Just handle pagination within
        # the data that's already been assigned to this display.
        
        if mode == 'split':
            # For split mode, we're dealing with pre-split data
            # Just paginate the items we received for this specific display
            self.screens_count = 1  # We're only dealing with one display's data
            self.items_per_page = self.items_per_screen
        else:
            # Single mode
            self.screens_count = 1
            self.items_per_page = self.items_per_screen
            
        self.total_pages = math.ceil(self.total_items / self.items_per_page) if self.total_items > 0 else 1
        
        print(f"DEBUG PAGINATOR: Mode={mode}, items_per_page={self.items_per_page}, total_pages={self.total_pages}")
    
    def get_page_data(self, page_number=1, screen_number=1):
        """Get BOM data for specific page - FIXED for pre-split data"""
        print(f"DEBUG PAGINATOR: get_page_data called with page={page_number}, screen={screen_number}")
        print(f"DEBUG PAGINATOR: Working with {len(self.bom_data)} pre-split items")
        
        page_number = max(1, min(page_number, self.total_pages))
        
        # FIXED: Since data is already split by display, just paginate within this display's data
        page_start_idx = (page_number - 1) * self.items_per_page
        page_end_idx = page_start_idx + self.items_per_page
        
        page_items = self.bom_data[page_start_idx:page_end_idx]
        
        print(f"DEBUG PAGINATOR: Page {page_number} contains {len(page_items)} items")
        
        # Create adjusted items with proper serial numbers
        adjusted_items = []
        for i, item in enumerate(page_items):
            adjusted_item = {
                'serial_number': item['serial_number'],  # Keep original serial number from template
                'screen_position': i + 1,  # Position on current page/screen
                'item': item['item'],
                'base_quantity': item['base_quantity'],
                'calculated_quantity': item['calculated_quantity'],
                'formatted_quantity': item['formatted_quantity'],
                'notes': item.get('notes', '')
            }
            adjusted_items.append(adjusted_item)
            
        print(f"DEBUG PAGINATOR: Returning {len(adjusted_items)} adjusted items")
        return adjusted_items
    
    def get_pagination_info(self, current_page=1):
        """Get pagination information - UPDATED"""
        return {
            'current_page': current_page,
            'total_pages': self.total_pages,
            'total_items': self.total_items,  # Items for THIS display only
            'items_per_screen': self.items_per_page,
            'items_per_page': self.items_per_page,
            'screens_count': 1,  # We're handling one display's data
            'mode': self.mode,
            'has_next': current_page < self.total_pages,
            'has_previous': current_page > 1
        }
  



class BOMPaginationManager:
    """Manage pagination state using Django cache with reset capabilities"""
    
    CACHE_TIMEOUT = 3600  # 1 hour
    
    @classmethod
    def _get_cache_key(cls, product_id, bom_type):
        """Generate cache key for pagination state"""
        return f"bom_pagination_{product_id}_{bom_type}"
    
    @classmethod
    def get_current_page(cls, product_id, bom_type):
        """Get current page for a product/bom_type combination"""
        cache_key = cls._get_cache_key(product_id, bom_type)
        return cache.get(cache_key, 1)
    
    @classmethod
    def set_current_page(cls, product_id, bom_type, page):
        """Set current page for a product/bom_type combination"""
        cache_key = cls._get_cache_key(product_id, bom_type)
        cache.set(cache_key, max(1, page), cls.CACHE_TIMEOUT)
    
    # NEW: Reset pagination when process/stage changes
    @classmethod
    def reset_pagination(cls, product_id, bom_type):
        """Reset pagination to page 1 for a product/bom_type combination"""
        cache_key = cls._get_cache_key(product_id, bom_type)
        cache.set(cache_key, 1, cls.CACHE_TIMEOUT)
        print(f"DEBUG PAGINATION: Reset pagination for {product_id}_{bom_type} to page 1")
    
    # NEW: Clear all pagination state for a product
    @classmethod
    def clear_product_pagination(cls, product_id):
        """Clear all pagination state for a product"""
        # Clear all possible BOM types for this product
        bom_types = ['SINGLE_UNIT', 'BATCH_50', 'SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY', 'BOM_DISPLAY']
        for bom_type in bom_types:
            cache_key = cls._get_cache_key(product_id, bom_type)
            cache.delete(cache_key)
        print(f"DEBUG PAGINATION: Cleared all pagination state for product {product_id}")
    
    @classmethod
    def next_page(cls, product_id, bom_type, total_pages):
        """Go to next page"""
        current = cls.get_current_page(product_id, bom_type)
        next_page = min(current + 1, total_pages)
        cls.set_current_page(product_id, bom_type, next_page)
        return next_page
    
    @classmethod
    def previous_page(cls, product_id, bom_type):
        """Go to previous page"""
        current = cls.get_current_page(product_id, bom_type)
        prev_page = max(current - 1, 1)
        cls.set_current_page(product_id, bom_type, prev_page)
        return prev_page

    
# Add this debug endpoint to test process changes

def debug_process_change(request, station_id):
    """Debug what happens when process changes"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get current state
    current_state = {
        'station_id': station_id,
        'display_number': station.display_number,
        'current_process': {
            'id': station.current_process.id if station.current_process else None,
            'name': station.current_process.name if station.current_process else None,
            'display_name': station.current_process.display_name if station.current_process else None,
        },
        'current_stage': {
            'id': station.current_stage.id if station.current_stage else None,
            'name': station.current_stage.name if station.current_stage else None,
            'display_name': station.current_stage.display_name if station.current_stage else None,
        },
        'bom_settings': {
            'show_batch_bom': station.show_batch_bom,
            'show_single_unit_bom': station.show_single_unit_bom,
            'product_quantity': station.product_quantity
        }
    }
    
    # Check what BOM data this should produce
    bom_data = station.get_current_bom_data() or []
    current_bom = {
        'item_count': len(bom_data),
        'items': [
            {
                'serial_number': item['serial_number'],
                'item_description': item['item'].item_description,
            }
            for item in bom_data
        ]
    }
    
    # Get cache state
    from django.core.cache import cache
    cache_states = {}
    if station.current_product:
        bom_types = ['SINGLE_UNIT', 'BATCH_50', 'SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY', 'BOM_DISPLAY']
        for bom_type in bom_types:
            cache_key = f"bom_pagination_{station.current_product.id}_{bom_type}"
            cache_value = cache.get(cache_key, 'NOT_SET')
            cache_states[bom_type] = cache_value
    
    # Test what different processes would show
    process_scenarios = {}
    
    # Test some other processes
    test_processes = AssemblyProcess.objects.all()[:5]  # Get first 5 processes for testing
    
    for process in test_processes:
        # Temporarily change process
        original_process = station.current_process
        original_stage = station.current_stage
        
        station.current_process = process
        station.current_stage = process.stage
        
        # Get BOM data for this process
        test_bom_data = station.get_current_bom_data() or []
        
        process_scenarios[process.name] = {
            'process_id': process.id,
            'stage_name': process.stage.name if process.stage else None,
            'bom_item_count': len(test_bom_data),
            'items': [
                {
                    'serial_number': item['serial_number'],
                    'item_description': item['item'].item_description,
                }
                for item in test_bom_data[:3]  # Just first 3 for brevity
            ] if test_bom_data else []
        }
        
        # Restore original
        station.current_process = original_process
        station.current_stage = original_stage
    
    return JsonResponse({
        'current_state': current_state,
        'current_bom': current_bom,
        'cache_states': cache_states,
        'process_scenarios': process_scenarios,
        'explanation': {
            'why_same_items': 'If you see the same items when changing processes, it could be because:',
            'reasons': [
                '1. You are staying in the same BOM stage (BOM Display)',
                '2. Both processes use the same BOM template (BATCH_50)',
                '3. Display 3 always gets items 7-9 for this BOM template',
                '4. The process change does not affect which BOM template is used'
            ],
            'when_items_change': 'Items will change when:',
            'change_conditions': [
                '1. You move to a different stage that has its own BOM template',
                '2. You toggle between single unit and batch BOM',
                '3. You change to a process that does not show BOMs'
            ]
        }
    })
# Add this debug view to check your BOM template

def debug_bom_template(request, station_id):
    """Debug BOM template to see what's happening"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return JsonResponse({'error': 'No product selected'}, status=400)
    
    debug_info = {
        'station_id': station_id,
        'display_number': station.display_number,
        'current_product': station.current_product.code,
        'show_batch_bom': station.show_batch_bom,
        'show_single_unit_bom': station.show_single_unit_bom,
        'product_quantity': station.product_quantity
    }
    
    # Check what BOM template exists
    try:
        if station.show_batch_bom:
            bom_template = BOMTemplate.objects.get(
                product=station.current_product,
                bom_type='BATCH_50',
                is_active=True
            )
        elif station.show_single_unit_bom:
            bom_template = BOMTemplate.objects.get(
                product=station.current_product,
                bom_type='SINGLE_UNIT',
                is_active=True
            )
        else:
            return JsonResponse({'error': 'No BOM type selected'}, status=400)
        
        # Get template details
        template_info = {
            'id': bom_template.id,
            'name': bom_template.template_name,
            'bom_type': bom_template.bom_type,
            'should_split': bom_template.should_split_across_displays(),
            'total_items': bom_template.bom_items.filter(is_active=True).count()
        }
        
        # Get all items in the template
        all_template_items = []
        for item in bom_template.bom_items.filter(is_active=True).order_by('serial_number'):
            all_template_items.append({
                'serial_number': item.serial_number,
                'item_code': item.item.item_code,
                'item_description': item.item.item_description,
                'base_quantity': float(item.base_quantity)
            })
        
        # Test split logic for all 3 displays
        split_results = {}
        for display_num in [1, 2, 3]:
            items_for_display = bom_template.get_items_for_display(display_num, station.product_quantity)
            split_results[f'display_{display_num}'] = {
                'item_count': len(items_for_display),
                'items': [
                    {
                        'serial_number': item['serial_number'],
                        'item_description': item['item'].item_description,
                        'calculated_quantity': item['calculated_quantity']
                    }
                    for item in items_for_display
                ]
            }
        
        # Test what station.get_current_bom_data() returns
        station_bom_data = station.get_current_bom_data() or []
        station_result = {
            'item_count': len(station_bom_data),
            'items': [
                {
                    'serial_number': item['serial_number'],
                    'item_description': item['item'].item_description,
                    'calculated_quantity': item['calculated_quantity']
                }
                for item in station_bom_data
            ]
        }
        
        return JsonResponse({
            'debug_info': debug_info,
            'template_info': template_info,
            'all_template_items': all_template_items,
            'split_test_results': split_results,
            'station_bom_result': station_result,
            'summary': {
                'template_has_items': template_info['total_items'],
                'should_split': template_info['should_split'],
                'display_1_gets': split_results['display_1']['item_count'],
                'display_2_gets': split_results['display_2']['item_count'],
                'display_3_gets': split_results['display_3']['item_count'],
                'station_method_returns': station_result['item_count']
            }
        })
        
    except BOMTemplate.DoesNotExist:
        return JsonResponse({
            'error': 'BOM template not found',
            'debug_info': debug_info,
            'suggestion': 'Create a BOM template in admin panel'
        }, status=404)
           
def validate_pagination_params(request):
    """Centralized parameter validation"""
    # Validate page parameter
    try:
        page = int(request.GET.get('page', 1))
        page = max(1, page)
    except (ValueError, TypeError):
        page = 1
    
    # Validate mode parameter
    mode = request.GET.get('mode', 'split')
    if mode not in ['split', 'single']:
        mode = 'split'
    
    # Validate items_per_screen parameter
    try:
        items_per_screen_param = request.GET.get('items_per_screen', '8')
        if items_per_screen_param in ['undefined', 'null', '', None]:
            items_per_screen = 8
        else:
            items_per_screen = int(items_per_screen_param)
            if not (1 <= items_per_screen <= 20):
                items_per_screen = 8
    except (ValueError, TypeError):
        items_per_screen = 8
    
    return page, mode, items_per_screen

def serialize_bom_item(item_data):
    """Serialize BOM item for JSON response"""
    return {
        'serial_number': item_data['serial_number'],
        'screen_position': item_data.get('screen_position', item_data['serial_number']),  # Use serial_number if screen_position not available
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

def get_station_bom_data_paginated(request, station_id):
    """Get paginated BOM data for a specific station - UPDATED WITH NEW PAGINATION LOGIC"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return JsonResponse({'error': 'No product selected'}, status=400)
    
    # Validate parameters
    page, mode, items_per_screen = validate_pagination_params(request)
    
    print(f"DEBUG PAGINATED VIEW: Station {station.name}, Display {station.display_number}, Page {page}")
    print(f"DEBUG PAGINATED VIEW: Current stage: {station.current_stage.name if station.current_stage else 'None'}")
    
    # Get BOM data with pagination support (pass page parameter)
    bom_data = station.get_current_bom_data(page=page) or []
    
    if not bom_data:
        return JsonResponse({'error': 'No BOM data available'}, status=404)
    
    # Determine BOM type for pagination state
    bom_type = 'UNKNOWN'
    quantity = station.product_quantity or 1
    bom_template = None
    
    if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
        # Stage-specific BOM
        bom_type = station.current_stage.name
        quantity = station.product_quantity
        try:
            bom_template = station.current_product.bom_templates.get(
                bom_type=bom_type,
                is_active=True
            )
        except:
            pass
    elif station.current_stage and station.current_stage.name == 'BOM_DISPLAY':
        # BOM Display stage
        if station.show_single_unit_bom:
            bom_type = 'SINGLE_UNIT'
            quantity = 1
        elif station.show_batch_bom:
            bom_type = 'BATCH_50'
            quantity = station.product_quantity
        
        try:
            bom_template = station.current_product.bom_templates.get(
                bom_type=bom_type,
                is_active=True
            )
        except:
            pass
    
    # Get current page from cache or use request page
    current_page = page
    if 'page' in request.GET:
        BOMPaginationManager.set_current_page(station.current_product.id, bom_type, current_page)
    else:
        current_page = BOMPaginationManager.get_current_page(station.current_product.id, bom_type)
        if current_page != page:
            # If cached page is different, update the data
            bom_data = station.get_current_bom_data(page=current_page) or []
    
    # Get proper pagination info from template
    if bom_template:
        if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            # Stage-specific BOMs don't paginate (all on Display 1)
            if station.display_number == 1:
                total_items = len(bom_template.generate_bom_for_quantity(quantity))
                pagination_info = {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': total_items,
                    'items_per_screen': total_items,
                    'items_per_page': total_items,
                    'screens_count': 1,
                    'mode': mode,
                    'has_next': False,
                    'has_previous': False
                }
            else:
                # Displays 2 and 3 get no items in assembly stages
                pagination_info = {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': 0,
                    'items_per_screen': 0,
                    'items_per_page': 0,
                    'screens_count': 1,
                    'mode': mode,
                    'has_next': False,
                    'has_previous': False
                }
        else:
            # BOM Display stage with pagination (8 items per display, 3 displays per page)
            template_pagination_info = bom_template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
            pagination_info = {
                'current_page': current_page,
                'total_pages': template_pagination_info['total_pages'],
                'total_items': template_pagination_info['total_items'],
                'items_per_screen': 8,  # Fixed 8 items per screen
                'items_per_page': template_pagination_info['items_per_page'],  # 24 items per page (8×3)
                'screens_count': 3,  # Always 3 displays
                'mode': mode,
                'has_next': current_page < template_pagination_info['total_pages'],
                'has_previous': current_page > 1
            }
    else:
        # Fallback pagination info when no template found
        pagination_info = {
            'current_page': current_page,
            'total_pages': 1,
            'total_items': len(bom_data),
            'items_per_screen': len(bom_data),
            'items_per_page': len(bom_data),
            'screens_count': 1,
            'mode': mode,
            'has_next': False,
            'has_previous': False
        }
    
    # Add screen position to items for serialization compatibility
    for i, item in enumerate(bom_data):
        if 'screen_position' not in item:
            item['screen_position'] = i + 1
    
    # Serialize BOM data
    formatted_bom = [serialize_bom_item(item) for item in bom_data]
    
    print(f"DEBUG PAGINATED VIEW: Returning {len(formatted_bom)} items for Display {station.display_number}, Page {current_page}")
    print(f"DEBUG PAGINATED VIEW: Pagination info: Total pages={pagination_info['total_pages']}, Total items={pagination_info['total_items']}")
    
    return JsonResponse({
        'bom_data': formatted_bom,
        'pagination': pagination_info,
        'station_info': {
            'name': station.name,
            'display_number': station.display_number,
            'product_code': station.current_product.code,
            'product_name': station.current_product.name,
            'quantity': quantity,
            'bom_type': bom_type,
            'mode': mode,
            'current_stage': station.current_stage.name if station.current_stage else None
        },
        'summary': {
            'items_on_screen': len(formatted_bom),
            'total_items': pagination_info['total_items'],
            'display_context': f"Display {station.display_number} - Page {current_page}/{pagination_info['total_pages']}"
        }
    })

def get_station_media_with_bom_pagination(request, station_id):
    """Get media for a specific station - FIXED STAGE-SPECIFIC BOM PAGINATION"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Get regular media FIRST
    current_media = station.get_current_media()
    
    # Validate pagination parameters
    try:
        mode = request.GET.get('mode', 'split')
        if mode not in ['split', 'single']:
            mode = 'split'
    except:
        mode = 'split'
    
    try:
        current_page = int(request.GET.get('page', '1'))
        if current_page < 1:
            current_page = 1
    except (ValueError, TypeError):
        current_page = 1
    
    try:
        items_per_screen_param = request.GET.get('items_per_screen', '8')
        if items_per_screen_param in ['undefined', 'null', '', None]:
            items_per_screen = 8
        else:
            items_per_screen = int(items_per_screen_param)
            if items_per_screen < 1 or items_per_screen > 20:
                items_per_screen = 8
    except (ValueError, TypeError):
        items_per_screen = 8
    
    media_data = []
    
    # FIRST: Add regular media (videos, PDFs, documents)
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
        
        media_data.append(media_info)
    
    # SECOND: Try to get BOM data with pagination
    display_bom_data = station.get_current_bom_data(page=current_page) or []
    
    print(f"DEBUG VIEW: Display {station.display_number} - Station returned {len(display_bom_data)} BOM items for page {current_page}")
    print(f"DEBUG VIEW: Current stage: {station.current_stage.name if station.current_stage else 'None'}")
    
    if display_bom_data and len(display_bom_data) > 0:
        # Determine BOM type and get the template for duration info
        bom_template = None
        is_stage_specific = False
        
        if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            # Stage-specific BOM (only on Display 1, no splitting, no pagination)
            bom_type_key = station.current_stage.name
            bom_display_name = f'{station.current_stage.display_name} BOM'
            is_stage_specific = True
            try:
                bom_template = station.current_product.bom_templates.get(
                    bom_type=bom_type_key, 
                    stage=station.current_stage,
                    is_active=True
                )
            except:
                try:
                    bom_template = station.current_product.bom_templates.get(
                        bom_type=bom_type_key,
                        is_active=True
                    )
                except:
                    pass
        elif station.current_stage and station.current_stage.name == 'BOM_DISPLAY':
            # BOM Display stage (split across displays with pagination)
            if station.show_single_unit_bom:
                bom_type_key = 'SINGLE_UNIT'
                bom_display_name = 'Single Unit BOM'
                quantity = 1
            elif station.show_batch_bom:
                bom_type_key = 'BATCH_50'
                bom_display_name = f'{station.product_quantity} Units BOM'
                quantity = station.product_quantity
                # Add split indicator for BOM_DISPLAY stage
                if station.display_number in [2, 3]:
                    bom_display_name += ' (Split)'
            
            try:
                bom_template = station.current_product.bom_templates.get(
                    bom_type=bom_type_key,
                    is_active=True
                )
            except:
                pass
        else:
            bom_type_key = 'UNKNOWN'
            bom_display_name = 'BOM'
        
        # Determine duration from BOM template or use default
        bom_duration = 400  # Default fallback
        is_duration_active = False  # Default fallback
        
        if bom_template:
            bom_duration = bom_template.duration
            is_duration_active = bom_template.is_duration_active
            print(f"DEBUG VIEW: Display {station.display_number} - Using BOM template duration: {bom_duration}s, is_duration_active: {is_duration_active}")
        else:
            print(f"DEBUG VIEW: Display {station.display_number} - No BOM template found, using default duration: {bom_duration}s")
        
        # Get pagination info from template
        if bom_template and is_stage_specific:
            # Stage-specific BOMs: All items on Display 1, no pagination
            if station.display_number == 1:
                total_items = len(bom_template.generate_bom_for_quantity(station.product_quantity or 1))
                pagination_info = {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': total_items,
                    'items_per_screen': total_items,  # All items on one screen
                    'items_per_page': total_items,
                    'screens_count': 1,  # Only Display 1
                    'mode': mode,
                    'has_next': False,
                    'has_previous': False
                }
            else:
                # This shouldn't happen for stage-specific BOMs, but handle gracefully
                pagination_info = {
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': 0,
                    'items_per_screen': 0,
                    'items_per_page': 0,
                    'screens_count': 1,
                    'mode': mode,
                    'has_next': False,
                    'has_previous': False
                }
        elif bom_template:
            # BOM Display stage: 8 items per display, 3 displays per page
            template_pagination_info = bom_template.get_pagination_info_for_split(
                quantity=station.product_quantity or 1, 
                items_per_screen=8
            )
            pagination_info = {
                'current_page': current_page,
                'total_pages': template_pagination_info['total_pages'],
                'total_items': template_pagination_info['total_items'],
                'items_per_screen': 8,  # Fixed 8 items per screen
                'items_per_page': template_pagination_info['items_per_page'],  # 24 items per page
                'screens_count': 3,  # Always 3 displays
                'mode': mode,
                'has_next': current_page < template_pagination_info['total_pages'],
                'has_previous': current_page > 1
            }
        else:
            # Fallback
            pagination_info = {
                'current_page': current_page,
                'total_pages': 1,
                'total_items': len(display_bom_data),
                'items_per_screen': len(display_bom_data),
                'items_per_page': len(display_bom_data),
                'screens_count': 1,
                'mode': mode,
                'has_next': False,
                'has_previous': False
            }
        
        # Format the data we received from the station
        serialized_bom_data = []
        for i, item_data in enumerate(display_bom_data):
            serialized_item = {
                'serial_number': item_data['serial_number'],
                'screen_position': i + 1,
                'item': {
                    'item_code': item_data['item'].item_code,
                    'item_description': item_data['item'].item_description,
                    'part_number': item_data['item'].part_number,
                    'unit_of_measure': item_data['item'].unit_of_measure,
                    'supplier': item_data['item'].supplier,
                    'cost_per_unit': float(item_data['item'].cost_per_unit) if item_data['item'].cost_per_unit else None,
                    'item_photo_url': item_data['item'].item_photo.url if item_data['item'].item_photo else None,
                },
                'base_quantity': item_data['base_quantity'],
                'calculated_quantity': item_data['calculated_quantity'],
                'formatted_quantity': item_data['formatted_quantity'],
                'notes': item_data['notes']
            }
            serialized_bom_data.append(serialized_item)
        
        # Add BOM as media item with dynamic duration
        bom_media = {
            'id': f'bom_paginated_{station.id}',
            'url': f'/station/{station.id}/bom-render-paginated/',
            'type': 'bom',
            'duration': bom_duration,
            'is_duration_active': is_duration_active,
            'media_type': 'Paginated BOM',
            'is_bom_data': True,
            'bom_items': len(display_bom_data),
            'bom_type': bom_display_name,
            'is_split': not is_stage_specific,  # Stage-specific BOMs are NOT split
            'display_info': f"Display {station.display_number} - Page {current_page} - {len(display_bom_data)} items",
            'bom_data': serialized_bom_data,
            'pagination': pagination_info,
            'bom_hash': f"{station.current_product.id}_{bom_type_key}_{current_page}_{mode}_{items_per_screen}_{station.display_number}"
        }
        
        # Add BOM at beginning (priority)
        media_data.insert(0, bom_media)
        
        print(f"DEBUG VIEW: Display {station.display_number} - Added BOM media: {bom_display_name} with duration {bom_duration}s, page {current_page}/{pagination_info['total_pages']}")
        print(f"DEBUG VIEW: Is stage-specific: {is_stage_specific}, Is split: {not is_stage_specific}")
    else:
        print(f"DEBUG VIEW: Display {station.display_number} - No BOM data to add for page {current_page}")
    
    print(f"DEBUG VIEW: Display {station.display_number} - Final media count: {len(media_data)}")
    
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
        },
        'pagination_info': {
            'mode': mode,
            'items_per_screen': pagination_info['items_per_screen'] if 'pagination_info' in locals() else items_per_screen,
            'has_bom_data': len([m for m in media_data if m.get('is_bom_data')]) > 0,
            'current_page': current_page
        },
        'debug_info': {
            'display_number': station.display_number,
            'current_stage': station.current_stage.name if station.current_stage else None,
            'bom_items_from_station': len(display_bom_data) if 'display_bom_data' in locals() else 0,
            'regular_media_count': len([m for m in media_data if not m.get('is_bom_data')]),
            'total_media_items': len(media_data),
            'logic': 'Stage-specific BOMs on Display 1 only, BOM Display BOMs split across displays',
            'is_stage_specific': 'is_stage_specific' in locals() and is_stage_specific
        }
    })
   


@csrf_exempt
@require_http_methods(["POST"])
def bom_pagination_control(request, station_id):
    """Handle BOM pagination controls - UPDATED WITH NEW LOGIC"""
    station = get_object_or_404(Station, pk=station_id)
    
    if not station.current_product:
        return JsonResponse({'error': 'No product selected'}, status=400)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        
        print(f"DEBUG PAGINATION CONTROL: Station {station.name}, Display {station.display_number}, Action: {action}")
        
        # Validate parameters
        mode = data.get('mode', 'split')
        if mode not in ['split', 'single']:
            mode = 'split'
        
        # Determine BOM type and get template
        bom_type = 'UNKNOWN'
        quantity = station.product_quantity or 1
        bom_template = None
        
        if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            # Stage-specific BOM (no pagination)
            return JsonResponse({'error': 'Stage-specific BOMs do not support pagination'}, status=400)
        elif station.current_stage and station.current_stage.name == 'BOM_DISPLAY':
            # BOM Display stage (with pagination)
            if station.show_single_unit_bom:
                bom_type = 'SINGLE_UNIT'
                quantity = 1
            elif station.show_batch_bom:
                bom_type = 'BATCH_50'
                quantity = station.product_quantity
            
            try:
                bom_template = station.current_product.bom_templates.get(
                    bom_type=bom_type,
                    is_active=True
                )
            except:
                return JsonResponse({'error': f'No BOM template found for {bom_type}'}, status=404)
        else:
            return JsonResponse({'error': 'BOM pagination only available in BOM Display stage'}, status=400)
        
        if not bom_template:
            return JsonResponse({'error': 'No BOM template available'}, status=404)
        
        # Get pagination info from template
        template_pagination_info = bom_template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
        total_pages = template_pagination_info['total_pages']
        
        # Get current page from cache
        current_page = BOMPaginationManager.get_current_page(station.current_product.id, bom_type)
        
        # Handle pagination actions
        if action == 'next_page':
            new_page = min(current_page + 1, total_pages)
        elif action == 'previous_page':
            new_page = max(current_page - 1, 1)
        elif action == 'set_page':
            try:
                target_page = int(data.get('page', 1))
                new_page = max(1, min(target_page, total_pages))
            except (ValueError, TypeError):
                new_page = 1
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        # Update pagination state
        BOMPaginationManager.set_current_page(station.current_product.id, bom_type, new_page)
        
        # Create updated pagination info
        pagination_info = {
            'current_page': new_page,
            'total_pages': total_pages,
            'total_items': template_pagination_info['total_items'],
            'items_per_screen': 8,
            'items_per_page': template_pagination_info['items_per_page'],
            'screens_count': 3,
            'mode': mode,
            'has_next': new_page < total_pages,
            'has_previous': new_page > 1
        }
        
        print(f"DEBUG PAGINATION CONTROL: Updated to page {new_page}/{total_pages}")
        
        return JsonResponse({
            'success': True,
            'action': action,
            'current_page': new_page,
            'pagination': pagination_info,
            'message': f'Moved to page {new_page} of {total_pages}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"DEBUG PAGINATION CONTROL ERROR: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def render_bom_fragment_paginated(request, station_id):
    """Render BOM fragment with pagination support - UPDATED WITH NEW LOGIC"""
    station = get_object_or_404(Station, pk=station_id)
    
    # Validate parameters
    try:
        mode = request.GET.get('mode', 'split')
        if mode not in ['split', 'single']:
            mode = 'split'
    except:
        mode = 'split'
    
    try:
        items_per_screen_param = request.GET.get('items_per_screen', '8')
        if items_per_screen_param in ['undefined', 'null', '', None]:
            items_per_screen = 8
        else:
            items_per_screen = int(items_per_screen_param)
            if items_per_screen < 1 or items_per_screen > 20:
                items_per_screen = 8
    except (ValueError, TypeError):
        items_per_screen = 8
    
    print(f"DEBUG RENDER FRAGMENT: Station {station.name}, Display {station.display_number}")
    print(f"DEBUG RENDER FRAGMENT: Current stage: {station.current_stage.name if station.current_stage else 'None'}")
    
    # Determine BOM type and get current page
    bom_type_key = 'UNKNOWN'
    quantity = station.product_quantity or 1
    bom_template = None
    
    if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
        # Stage-specific BOM (no pagination)
        bom_type_key = station.current_stage.name
        bom_type_display = station.current_stage.display_name
        current_page = 1  # Always page 1 for stage-specific BOMs
        try:
            bom_template = station.current_product.bom_templates.get(
                bom_type=bom_type_key,
                is_active=True
            )
        except:
            pass
    elif station.current_stage and station.current_stage.name == 'BOM_DISPLAY':
        # BOM Display stage (with pagination)
        if station.show_single_unit_bom:
            bom_type_key = 'SINGLE_UNIT'
            bom_type_display = 'Single Unit BOM'
            quantity = 1
        elif station.show_batch_bom:
            bom_type_key = 'BATCH_50'
            bom_type_display = f'{station.product_quantity} Units BOM'
            quantity = station.product_quantity
        else:
            bom_type_display = 'No BOM Selected'
        
        # Get current page from cache for BOM Display stage
        current_page = BOMPaginationManager.get_current_page(station.current_product.id, bom_type_key)
        
        try:
            bom_template = station.current_product.bom_templates.get(
                bom_type=bom_type_key,
                is_active=True
            ) if bom_type_key != 'UNKNOWN' else None
        except:
            pass
    else:
        bom_type_display = 'No BOM Available'
        current_page = 1
    
    # For stage-specific BOMs, check if this display should have any data
    if (station.current_stage and 
        station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY'] and 
        station.display_number != 1):
        # Displays 2 and 3 get NO BOM in assembly stages - return empty context
        print(f"DEBUG RENDER FRAGMENT: Assembly stage - Display {station.display_number} should be empty")
        
        context = {
            'station': station,
            'bom_data': [],
            'bom_type': 'No BOM for this display',
            'quantity': 0,
            'pagination': {
                'current_page': 1,
                'total_pages': 1,
                'total_items': 0,
                'items_per_screen': 0,
                'items_per_page': 0,
                'screens_count': 1,
                'mode': mode,
                'has_next': False,
                'has_previous': False
            },
            'mode': mode,
            'is_split': False,
            'bom_info': {},
            'debug_info': {
                'display_number': station.display_number,
                'stage': station.current_stage.name,
                'message': 'Assembly stage - only Display 1 gets BOM data'
            }
        }
        return render(request, 'bom_slider_fragment_paginated.html', context)
    
    # Get BOM data with pagination
    bom_data = station.get_current_bom_data(page=current_page) if station.current_product else []
    bom_info = station.get_current_bom_info(page=current_page)
    
    # Get pagination info from template
    if bom_template:
        if station.current_stage and station.current_stage.name in ['SUB_ASSEMBLY_1', 'SUB_ASSEMBLY_2', 'FINAL_ASSEMBLY']:
            # Stage-specific BOMs don't paginate (only Display 1 should reach here)
            total_items = len(bom_template.generate_bom_for_quantity(quantity))
            pagination_info = {
                'current_page': 1,
                'total_pages': 1,
                'total_items': total_items,
                'items_per_screen': total_items,
                'items_per_page': total_items,
                'screens_count': 1,
                'mode': mode,
                'has_next': False,
                'has_previous': False
            }
        else:
            # BOM Display stage with pagination
            template_pagination_info = bom_template.get_pagination_info_for_split(quantity=quantity, items_per_screen=8)
            pagination_info = {
                'current_page': current_page,
                'total_pages': template_pagination_info['total_pages'],
                'total_items': template_pagination_info['total_items'],
                'items_per_screen': 8,
                'items_per_page': template_pagination_info['items_per_page'],
                'screens_count': 3,
                'mode': mode,
                'has_next': current_page < template_pagination_info['total_pages'],
                'has_previous': current_page > 1
            }
    else:
        # Fallback pagination info
        pagination_info = {
            'current_page': current_page,
            'total_pages': 1,
            'total_items': len(bom_data),
            'items_per_screen': len(bom_data),
            'items_per_page': len(bom_data),
            'screens_count': 1,
            'mode': mode,
            'has_next': False,
            'has_previous': False
        }
    
    # Add screen position to items for template compatibility
    for i, item in enumerate(bom_data):
        if 'screen_position' not in item:
            item['screen_position'] = i + 1
    
    print(f"DEBUG RENDER FRAGMENT: Display {station.display_number}, Page {current_page}/{pagination_info['total_pages']}, Items: {len(bom_data)}")
    
    context = {
        'station': station,
        'bom_data': bom_data,
        'bom_type': bom_type_display,
        'quantity': quantity,
        'pagination': pagination_info,
        'mode': mode,
        'is_split': mode == 'split' and station.current_stage and station.current_stage.name == 'BOM_DISPLAY',
        'bom_info': bom_info or {},
        'debug_info': {
            'received_params': {
                'mode': request.GET.get('mode'),
                'items_per_screen': request.GET.get('items_per_screen')
            },
            'processed_params': {
                'mode': mode,
                'items_per_screen': items_per_screen
            },
            'current_page': current_page,
            'total_pages': pagination_info['total_pages'],
            'screen_items': len(bom_data),
            'bom_type_key': bom_type_key,
            'stage': station.current_stage.name if station.current_stage else 'None'
        }
    }
    
    return render(request, 'bom_slider_fragment_paginated.html', context) 

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




#  For station 
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

# UPDATED: Add pagination reset to your clicker_action function

@csrf_exempt
@require_http_methods(["POST"])
def clicker_action(request, station_id):
    station = get_object_or_404(Station, pk=station_id)

    if not station.clicker_enabled:
        return JsonResponse({'error': 'Clicker not enabled for this station'}, status=400)

    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'forward', 'backward', 'toggle_loop'

        if action == 'forward':
            next_process = station.get_next_process()
            exit_loop_mode = False
            enter_loop_mode = False
            current_proc = station.current_process

            if (station.loop_mode and 
                current_proc and 
                current_proc.loop_group == 'final_assembly_1abc'):

                # Exit loop and jump directly to Process 2
                process_2 = AssemblyProcess.objects.filter(name='PROCESS 2 OF 6').first()
                if process_2:
                    next_process = process_2
                    exit_loop_mode = True
                    print(f"CLICKER: Exiting loop mode via manual forward → Jumping to {next_process.name}")

            elif (station.loop_mode and 
                  current_proc and 
                  current_proc.loop_group == 'final_assembly_1abc' and
                  next_process.loop_group != 'final_assembly_1abc'):

                # Exit loop due to process transition
                exit_loop_mode = True
                print(f"MANUAL FORWARD: Exiting loop - from {current_proc.name} to {next_process.name}")

            # ✅ Auto-enable loop when arriving at 1A from non-loop process
            elif (
                not station.loop_mode and 
                next_process and 
                next_process.name == 'PROCESS 1A OF 6'
            ):
                enter_loop_mode = True
                print(f"AUTO-ENTER LOOP MODE: Entering loop at {next_process.name}")

            if next_process:
                all_stations = Station.objects.all()
                updated_stations = []

                for st in all_stations:
                    if st.current_product == station.current_product:
                        old_process_name = st.current_process.name if st.current_process else None
                        st.current_process = next_process

                        if next_process.stage != st.current_stage:
                            st.current_stage = next_process.stage

                        if exit_loop_mode:
                            st.loop_mode = False
                        if enter_loop_mode:
                            st.loop_mode = True

                        st.save()
                        updated_stations.append({
                            'id': st.id,
                            'name': st.name,
                            'display_number': st.display_number,
                            'old_process': old_process_name,
                            'new_process': next_process.name,
                            'loop_mode_changed': exit_loop_mode or enter_loop_mode
                        })

                # NEW: Reset BOM pagination when process changes
                if station.current_product:
                    print(f"PAGINATION RESET: Process changed from {current_proc.name if current_proc else 'None'} to {next_process.name}")
                    BOMPaginationManager.clear_product_pagination(station.current_product.id)

                response_data = {
                    'success': True,
                    'message': f'All stations moved to {next_process.display_name}',
                    'current_process': {
                        'id': next_process.id,
                        'name': next_process.name,
                        'display_name': next_process.display_name,
                        'stage': next_process.stage.display_name,
                        'is_looped': next_process.is_looped,
                        'loop_group': next_process.loop_group
                    },
                    'loop_mode': True if enter_loop_mode else (station.loop_mode if not exit_loop_mode else False),
                    'updated_stations': updated_stations,
                    'exit_loop': exit_loop_mode,
                    'manual_action': True,
                    'pagination_reset': True,  # NEW: Flag indicating pagination was reset
                    'next_process': {
                        'id': station.get_next_process().id,
                        'name': station.get_next_process().name,
                        'display_name': station.get_next_process().display_name
                    } if station.get_next_process() else None
                }

                if exit_loop_mode:
                    response_data['exit_message'] = f'Exited loop mode - moved from {current_proc.name} to {next_process.name}'

                return JsonResponse(response_data)
            else:
                return JsonResponse({'error': 'No next process available'}, status=400)


        elif action == 'backward':
            exit_loop_mode = False
            enter_loop_mode = False

            current_proc = station.current_process
            previous_process = station.get_previous_process()

            # 🔧 Manual override: If current is 1A, jump back to Sub Assembly 2
            if (
                station.loop_mode and 
                current_proc and 
                current_proc.name == 'PROCESS 1A OF 6'
            ):
                previous_process = AssemblyProcess.objects.filter(
                    name='PROCESS 1 OF 1'
                ).first()

                if previous_process:
                    exit_loop_mode = True
                    print(f"OVERRIDE BACKWARD: From 1A → {previous_process.name}")
                else:
                    return JsonResponse({'error': 'Could not locate Sub Assembly 2 process'}, status=404)

            elif (
                station.loop_mode and 
                current_proc and 
                current_proc.loop_group == 'final_assembly_1abc' and 
                (previous_process.loop_group != 'final_assembly_1abc' or previous_process.loop_group is None)
            ):
                exit_loop_mode = True
                print(f"BACKWARD: Exiting loop mode – {current_proc.name} → {previous_process.name}")

            elif (
                not station.loop_mode and 
                previous_process and 
                previous_process.name == 'PROCESS 1A OF 6'
            ):
                enter_loop_mode = True
                print(f"BACKWARD: Auto-entering loop mode at {previous_process.name}")

            if previous_process is None:
                return JsonResponse({'error': 'No previous process available'}, status=400)

            # 🔁 Update all stations with same product
            all_stations = Station.objects.all()
            updated_stations = []

            for st in all_stations:
                if st.current_product == station.current_product:
                    old_process_name = st.current_process.name if st.current_process else None
                    st.current_process = previous_process

                    if previous_process.stage != st.current_stage:
                        st.current_stage = previous_process.stage

                    if exit_loop_mode:
                        st.loop_mode = False
                    if enter_loop_mode:
                        st.loop_mode = True

                    st.save()
                    updated_stations.append({
                        'id': st.id,
                        'name': st.name,
                        'display_number': st.display_number,
                        'old_process': old_process_name,
                        'new_process': previous_process.name,
                        'loop_mode_changed': exit_loop_mode or enter_loop_mode
                    })

            # NEW: Reset BOM pagination when process changes
            if station.current_product:
                print(f"PAGINATION RESET: Process changed from {current_proc.name if current_proc else 'None'} to {previous_process.name}")
                BOMPaginationManager.clear_product_pagination(station.current_product.id)

            return JsonResponse({
                'success': True,
                'message': f'All stations moved to {previous_process.display_name}',
                'current_process': {
                    'id': previous_process.id,
                    'name': previous_process.name,
                    'display_name': previous_process.display_name,
                    'stage': previous_process.stage.display_name,
                    'is_looped': previous_process.is_looped,
                    'loop_group': previous_process.loop_group
                },
                'loop_mode': True if enter_loop_mode else (station.loop_mode if not exit_loop_mode else False),
                'updated_stations': updated_stations,
                'manual_action': True,
                'pagination_reset': True,  # NEW: Flag indicating pagination was reset
                'previous_process': {
                    'id': previous_process.id,
                    'name': previous_process.name,
                    'display_name': previous_process.display_name
                }
            })

        elif action == 'toggle_loop':
            # No pagination reset needed for loop toggle
            if (station.current_process and 
                station.current_process.loop_group == 'final_assembly_1abc'):

                new_loop_mode = not station.loop_mode
                all_stations = Station.objects.all()
                updated_stations = []

                for st in all_stations:
                    if (st.current_product == station.current_product and
                        st.current_process and 
                        st.current_process.loop_group == 'final_assembly_1abc'):
                        st.loop_mode = new_loop_mode
                        st.save()
                        updated_stations.append({
                            'id': st.id,
                            'name': st.name,
                            'display_number': st.display_number,
                            'loop_mode': new_loop_mode
                        })

                return JsonResponse({
                    'success': True,
                    'loop_mode': new_loop_mode,
                    'message': f"Loop mode {'enabled' if new_loop_mode else 'disabled'} on all stations",
                    'updated_stations': updated_stations,
                    'manual_action': True
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
        print(f"Clicker action error: {str(e)}")
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

# File streaming views
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
    """Enhanced assembly configuration with AUTO LOOP MODE DETECTION"""
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
                
                # ENHANCED: Auto-enable loop mode when entering Process 1A
                if (process.loop_group == 'final_assembly_1abc' and 
                    process.name == 'PROCESS 1A OF 6'):
                    station.loop_mode = True
                    print(f"Auto-enabling loop mode for Process 1A on station {station.id}")
                elif process.loop_group != 'final_assembly_1abc':
                    # Disable loop mode when leaving the loop group
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
            'auto_loop_enabled': (station.current_process and 
                                 station.current_process.loop_group == 'final_assembly_1abc' and
                                 station.current_process.name == 'PROCESS 1A OF 6'),  # NEW: Auto loop flag
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
                    'order': station.current_process.order,
                    'loop_group': station.current_process.loop_group,
                    'is_auto_loop': (station.current_process.loop_group == 'final_assembly_1abc' and
                                   station.current_process.name == 'PROCESS 1A OF 6')  # NEW: Auto loop indicator
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


# NEW: Auto loop 
@csrf_exempt
@require_http_methods(["POST"])
def auto_loop_progress(request, station_id):
    """Handle automatic progression in loop mode - ENHANCED VERSION"""
    station = get_object_or_404(Station, pk=station_id)
    
    try:
        data = json.loads(request.body)
        client_timestamp = data.get('timestamp')
        expected_process = data.get('expectedProcess')
        
        # FIXED: Validate that enough time has passed since last auto progression
        current_time = time.time() * 1000  # Convert to milliseconds
        if hasattr(station, 'last_auto_progress_time'):
            time_since_last = current_time - station.last_auto_progress_time
            if time_since_last < 5000:  # Prevent progressions within 5 seconds
                return JsonResponse({
                    'error': f'Auto progression too frequent. Last: {time_since_last}ms ago',
                    'time_since_last': time_since_last,
                    'minimum_interval': 5000
                }, status=429)
        
        # FIXED: Validate that we're still in the expected process
        if expected_process and station.current_process:
            if station.current_process.name != expected_process:
                return JsonResponse({
                    'error': f'Process changed. Expected: {expected_process}, Current: {station.current_process.name}',
                    'expected': expected_process,
                    'current': station.current_process.name if station.current_process else None
                }, status=409)
        
        # Existing validation logic
        if not (station.loop_mode and 
                station.current_process and 
                station.current_process.loop_group == 'final_assembly_1abc'):
            return JsonResponse({
                'error': 'Auto progression not allowed',
                'details': {
                    'loop_mode': station.loop_mode,
                    'current_process': station.current_process.name if station.current_process else None,
                    'loop_group': station.current_process.loop_group if station.current_process else None
                }
            }, status=400)
        
        # Determine next process in loop
        current_name = station.current_process.name
        next_process = None
        loop_sequence = ['PROCESS 1A OF 6', 'PROCESS 1B OF 6', 'PROCESS 1C OF 6']
        
        try:
            current_index = loop_sequence.index(current_name)
            next_index = (current_index + 1) % len(loop_sequence)
            next_process_name = loop_sequence[next_index]
            
            next_process = AssemblyProcess.objects.filter(
                name=next_process_name,
                loop_group='final_assembly_1abc'
            ).first()
            
        except ValueError:
            return JsonResponse({
                'error': f'Current process {current_name} not in loop sequence',
                'loop_sequence': loop_sequence
            }, status=400)
        
        if not next_process:
            return JsonResponse({
                'error': f'Next process {next_process_name} not found in database',
                'searched_for': next_process_name
            }, status=404)
        
        # Log the auto progression
        print(f"AUTO LOOP PROGRESSION: {current_name} → {next_process.name} (Client: {client_timestamp})")
        
        # FIXED: Update timestamp tracking
        station.last_auto_progress_time = current_time
        
        # Update ALL stations with the same product
        all_stations = Station.objects.all()
        updated_stations = []
        skipped_stations = []
        
        for st in all_stations:
            if (st.current_product == station.current_product and
                st.loop_mode and
                st.current_process and 
                st.current_process.loop_group == 'final_assembly_1abc'):
                
                old_process = st.current_process.name
                st.current_process = next_process
                
                if next_process.stage != st.current_stage:
                    st.current_stage = next_process.stage
                
                # FIXED: Update timestamp on all affected stations
                st.last_auto_progress_time = current_time
                st.save()
                
                updated_stations.append({
                    'id': st.id,
                    'name': st.name,
                    'display_number': st.display_number,
                    'old_process': old_process,
                    'new_process': next_process.name
                })
                
            else:
                skip_reason = []
                if st.current_product != station.current_product:
                    skip_reason.append('different_product')
                if not st.loop_mode:
                    skip_reason.append('not_in_loop_mode')
                if not st.current_process:
                    skip_reason.append('no_current_process')
                elif st.current_process.loop_group != 'final_assembly_1abc':
                    skip_reason.append('not_in_loop_group')
                
                skipped_stations.append({
                    'id': st.id,
                    'name': st.name,
                    'display_number': st.display_number,
                    'skip_reasons': skip_reason
                })
        
        # Enhanced response data
        response_data = {
            'success': True,
            'message': f'Auto-progressed from {current_name} to {next_process.display_name}',
            'progression': {
                'from': {
                    'name': current_name,
                    'display_name': station.current_process.display_name if station.current_process else current_name
                },
                'to': {
                    'name': next_process.name,
                    'display_name': next_process.display_name
                }
            },
            'current_process': {
                'id': next_process.id,
                'name': next_process.name,
                'display_name': next_process.display_name,
                'loop_group': next_process.loop_group,
                'stage': {
                    'id': next_process.stage.id,
                    'name': next_process.stage.name,
                    'display_name': next_process.stage.display_name
                }
            },
            'updated_stations': updated_stations,
            'skipped_stations': skipped_stations,
            'loop_continues': True,
            'loop_sequence': loop_sequence,
            'current_position': loop_sequence.index(next_process.name),
            'timestamp': current_time,
            'server_time': time.time() * 1000,
            'client_timestamp': client_timestamp,
            'progression_id': f"{station_id}_{current_time}"  # Unique ID for this progression
        }
        
        # Add next progression info
        try:
            current_index = loop_sequence.index(next_process.name)
            next_index = (current_index + 1) % len(loop_sequence)
            response_data['next_progression'] = {
                'will_go_to': loop_sequence[next_index],
                'is_cycle_complete': next_index == 0
            }
        except ValueError:
            pass
        
        print(f"AUTO LOOP SUCCESS: Updated {len(updated_stations)} stations, skipped {len(skipped_stations)}")
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        error_message = f'Auto loop progression error: {str(e)}'
        print(f"AUTO LOOP ERROR: {error_message}")
        
        return JsonResponse({
            'error': error_message,
            'success': False,
            'current_process': {
                'name': station.current_process.name if station.current_process else None,
                'loop_group': station.current_process.loop_group if station.current_process else None
            },
            'station_info': {
                'id': station.id,
                'name': station.name,
                'loop_mode': station.loop_mode
            },
            'timestamp': time.time() * 1000
        }, status=500)    
      
        
@csrf_exempt
@require_http_methods(["GET", "POST"])
def auto_loop_config(request, station_id):
    """Configure auto loop settings for a station"""
    station = get_object_or_404(Station, pk=station_id)
    
    if request.method == 'GET':
        # Return current auto loop configuration
        return JsonResponse({
            'station': {
                'id': station.id,
                'name': station.name,
                'display_number': station.display_number
            },
            'current_state': {
                'loop_mode': station.loop_mode,
                'current_process': {
                    'name': station.current_process.name if station.current_process else None,
                    'display_name': station.current_process.display_name if station.current_process else None,
                    'loop_group': station.current_process.loop_group if station.current_process else None,
                } if station.current_process else None,
                'is_in_loop_group': (station.current_process and 
                                   station.current_process.loop_group == 'final_assembly_1abc'),
            },
            'loop_configuration': {
                'loop_processes': ['PROCESS 1A OF 6', 'PROCESS 1B OF 6', 'PROCESS 1C OF 6'],
                'default_durations': {
                    'PROCESS 1A OF 6': 30000,  # 30 seconds
                    'PROCESS 1B OF 6': 45000,  # 45 seconds
                    'PROCESS 1C OF 6': 60000   # 60 seconds
                },
                'loop_group': 'final_assembly_1abc'
            }
        })
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'enable_auto_loop':
                # Enable auto loop mode for this station
                if (station.current_process and 
                    station.current_process.loop_group == 'final_assembly_1abc'):
                    
                    station.loop_mode = True
                    station.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Auto loop mode enabled',
                        'current_process': station.current_process.name,
                        'loop_mode': station.loop_mode
                    })
                else:
                    return JsonResponse({
                        'error': 'Can only enable auto loop in processes 1A, 1B, or 1C',
                        'current_process': station.current_process.name if station.current_process else None
                    }, status=400)
            
            elif action == 'disable_auto_loop':
                # Disable auto loop mode
                station.loop_mode = False
                station.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Auto loop mode disabled',
                    'loop_mode': station.loop_mode
                })
            
            elif action == 'force_progress':
                # Force immediate progression (for testing)
                if (station.loop_mode and 
                    station.current_process and 
                    station.current_process.loop_group == 'final_assembly_1abc'):
                    
                    # Call the auto progression logic
                    progress_request = type('MockRequest', (), {
                        'method': 'POST',
                        'body': json.dumps({}).encode()
                    })()
                    
                    # This would call the auto_loop_progress view
                    return auto_loop_progress(progress_request, station_id)
                else:
                    return JsonResponse({
                        'error': 'Station not in auto loop mode or not in loop group'
                    }, status=400)
            
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


def auto_loop_status_all(request):
    """Get auto loop status for all stations"""
    stations = Station.objects.all().select_related('current_process', 'current_stage', 'current_product')
    
    stations_status = []
    for station in stations:
        is_in_loop_group = (station.current_process and 
                           station.current_process.loop_group == 'final_assembly_1abc')
        
        station_info = {
            'id': station.id,
            'name': station.name,
            'display_number': station.display_number,
            'loop_mode': station.loop_mode,
            'current_process': {
                'name': station.current_process.name if station.current_process else None,
                'display_name': station.current_process.display_name if station.current_process else None,
                'loop_group': station.current_process.loop_group if station.current_process else None,
            } if station.current_process else None,
            'is_in_loop_group': is_in_loop_group,
            'auto_loop_eligible': is_in_loop_group and station.loop_mode,
            'current_product': {
                'code': station.current_product.code,
                'name': station.current_product.name
            } if station.current_product else None
        }
        stations_status.append(station_info)
    
    # Summary statistics
    total_stations = len(stations_status)
    auto_loop_active = len([s for s in stations_status if s['auto_loop_eligible']])
    in_loop_group = len([s for s in stations_status if s['is_in_loop_group']])
    
    return JsonResponse({
        'stations': stations_status,
        'summary': {
            'total_stations': total_stations,
            'auto_loop_active': auto_loop_active,
            'in_loop_group': in_loop_group,
            'loop_processes': ['PROCESS 1A OF 6', 'PROCESS 1B OF 6', 'PROCESS 1C OF 6']
        },
        'timestamp': time.time()
    })


def get_next_process(self):
    """Get the next process in sequence - ENHANCED for loop exit logic"""
    if not self.current_process:
        return None
    
    # Get all processes for the current product, ordered by stage and process order
    all_processes = AssemblyProcess.objects.filter(
        stage__in=self.current_product.stages.all()
    ).select_related('stage').order_by('stage__order', 'order')
    
    current_found = False
    for process in all_processes:
        if current_found:
            return process
        if process.id == self.current_process.id:
            current_found = True
    
    # If we're at the last process, return None (no next process)
    return None


#  debug the issue
def debug_process_sequence(request, station_id):
    """Debug view to check process sequence"""
    try:
        station = Station.objects.get(pk=station_id)
        
        if not station.current_product:
            return JsonResponse({'error': 'No product selected'})
        
        # Get all processes for current product
        all_processes = AssemblyProcess.objects.filter(
            stage__in=station.current_product.stages.all()
        ).select_related('stage').order_by('stage__order', 'order')
        
        process_sequence = []
        for i, process in enumerate(all_processes):
            process_info = {
                'index': i,
                'id': process.id,
                'name': process.name,
                'display_name': process.display_name,
                'stage': process.stage.display_name,
                'loop_group': process.loop_group,
                'is_current': process.id == station.current_process.id if station.current_process else False
            }
            process_sequence.append(process_info)
        
        # Find current process index
        current_index = -1
        if station.current_process:
            for i, process in enumerate(all_processes):
                if process.id == station.current_process.id:
                    current_index = i
                    break
        
        # Determine next process
        next_process_info = None
        if current_index >= 0 and current_index < len(all_processes) - 1:
            next_process = all_processes[current_index + 1]
            next_process_info = {
                'id': next_process.id,
                'name': next_process.name,
                'display_name': next_process.display_name,
                'stage': next_process.stage.display_name,
                'loop_group': next_process.loop_group
            }
        
        return JsonResponse({
            'station': {
                'id': station.id,
                'name': station.name,
                'loop_mode': station.loop_mode
            },
            'current_process': {
                'id': station.current_process.id if station.current_process else None,
                'name': station.current_process.name if station.current_process else None,
                'loop_group': station.current_process.loop_group if station.current_process else None,
                'index': current_index
            },
            'next_process': next_process_info,
            'all_processes': process_sequence,
            'total_processes': len(process_sequence)
        })
        
    except Station.DoesNotExist:
        return JsonResponse({'error': 'Station not found'}, status=404)
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
            'duration': 40,
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
from django.contrib.auth.decorators import login_required

from django.shortcuts import render

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def supervisor_dashboard(request):
    return render(request, 'supervisor-dashboard.html')

@login_required
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









# admin.py
# models.py - Enhanced with Database BOM System

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
        """Get BOM items specific to a display number with pagination - FIXED WITH MIN/MAX 8 ITEMS LOGIC"""
        print(f"DEBUG TEMPLATE: get_items_for_display called for display {display_number}, quantity {quantity}, page {page}")
        print(f"DEBUG TEMPLATE: BOM type: {self.bom_type}, should_split: {self.should_split_across_displays()}")
        
        if not self.should_split_across_displays():
            # Stage-specific BOMs show complete on Display 1 only
            if display_number == 1:
                result = self.generate_bom_for_quantity(quantity)
                print(f"DEBUG TEMPLATE: Non-split BOM on display 1: {len(result)} items")
                return result
            else:
                print(f"DEBUG TEMPLATE: Non-split BOM on display {display_number}: 0 items")
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
        """Get pagination information for split BOMs - NEW METHOD"""
        if not self.should_split_across_displays():
            return {
                'total_pages': 1,
                'items_per_page': self.bom_items.filter(is_active=True).count(),
                'items_per_screen': items_per_screen,
                'total_items': self.bom_items.filter(is_active=True).count()
            }
        
        total_items = len(self.generate_bom_for_quantity(quantity))
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
    
# FIXED: Station.get_current_bom_data method - No split for assembly stages

    def get_current_bom_data(self, page=1):
        """Get current BOM data with pagination support - UPDATED"""
        if not self.current_product or not self.display_number:
            return None

        print(f"DEBUG BOM: Station {self.name}, Display {self.display_number}, Page {page}")
        print(f"DEBUG BOM: Current stage: {self.current_stage.name if self.current_stage else 'None'}")
        print(f"DEBUG BOM: Current process: {self.current_process.name if self.current_process else 'None'}")
        
        quantity = self.product_quantity
        
        # PRIORITY 1: Stage-specific BOM (only on Display 1, complete, non-split, no pagination)
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
                    print(f"DEBUG BOM: Found stage-specific BOM: {stage_bom_type} for Display 1 (complete)")
                    # Stage-specific BOMs show complete on Display 1, no splitting, no pagination
                    result = stage_template.generate_bom_for_quantity(quantity)
                    print(f"DEBUG BOM: Stage BOM returned {len(result)} items for Display 1")
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
    
    
    
    
    
    
# with everything in working condition 

# `
# 



# `
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# ` 

# '
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# 
# ' 
# `
#  