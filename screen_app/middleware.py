
import logging

logger = logging.getLogger(__name__)

class FixedSSEMiddleware:
    """
    Fixed middleware for SSE support that works with Django development server
    Avoids hop-by-hop headers that cause WSGI errors
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Handle SSE streaming endpoints
        if '/stream/' in request.path:
            logger.debug(f"Processing SSE request: {request.path}")
            
            # Only add safe headers for SSE
            if not response.get('Content-Type'):
                response['Content-Type'] = 'text/event-stream; charset=utf-8'
            
            # Safe caching headers (not hop-by-hop)
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # CORS headers (safe for WSGI)
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Cache-Control, Content-Type'
            response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            
            # Remove any hop-by-hop headers that might cause issues
            hop_by_hop_headers = [
                'Connection', 
                'Keep-Alive', 
                'Proxy-Authenticate',
                'Proxy-Authorization',
                'TE',
                'Trailers',
                'Transfer-Encoding',
                'Upgrade'
            ]
            
            for header in hop_by_hop_headers:
                if header in response:
                    del response[header]
                    logger.debug(f"Removed hop-by-hop header: {header}")
        
        # Handle CORS for other API endpoints
        elif any(endpoint in request.path for endpoint in ['/clicker/', '/bom-pagination-control/', '/auto-loop-progress/', '/ping/']):
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
            response['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
            
            # Handle preflight OPTIONS requests
            if request.method == 'OPTIONS':
                response['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response
    
    def process_exception(self, request, exception):
        """Handle exceptions in streaming endpoints"""
        if '/stream/' in request.path:
            logger.error(f"SSE stream exception for {request.path}: {str(exception)}")
            
            # For SSE endpoints, return a proper error event
            from django.http import StreamingHttpResponse
            import json
            import time
            
            def error_stream():
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(exception), 'timestamp': time.time()})}\n\n"
            
            response = StreamingHttpResponse(error_stream(), content_type='text/event-stream')
            response['Cache-Control'] = 'no-cache'
            response['Access-Control-Allow-Origin'] = '*'
            return response
        
        return None


# Alternative simpler middleware if the above doesn't work
class SimpleSSEMiddleware:
    """
    Simplified SSE middleware - minimal headers only
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Only handle SSE endpoints with minimal headers
        if '/stream/' in request.path and hasattr(response, 'streaming_content'):
            # Remove any problematic headers
            if 'Connection' in response:
                del response['Connection']
            if 'Keep-Alive' in response:
                del response['Keep-Alive']
            
            # Set only essential headers
            response['Cache-Control'] = 'no-cache'
            response['Access-Control-Allow-Origin'] = '*'
        
        return response
