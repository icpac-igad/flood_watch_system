import json
import logging
import time

logger = logging.getLogger(__name__)
timing_logger = logging.getLogger('Impact.api_timing')

class RelativeURLMiddleware:
    """
    Middleware to convert absolute URLs in API responses to relative URLs.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only process JSON responses for API endpoints
        if (request.path.startswith('/api/') and
            hasattr(response, 'get') and
            response.get('Content-Type', '').startswith('application/json')):
            try:
                # Get the response content as text
                content = response.content.decode('utf-8')
                logger.debug(f"Processing API response for {request.path}: {content[:200]}...")

                data = json.loads(content)

                # Convert absolute URLs to relative URLs
                modified_data = self.convert_urls(data)

                # Update response with modified content
                response.content = json.dumps(modified_data).encode('utf-8')
                response['Content-Length'] = str(len(response.content))
                logger.debug(f"Modified response: {json.dumps(modified_data)[:200]}...")

            except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as e:
                # If we can't parse JSON or decode, just return original response
                logger.error(f"Error processing response: {e}")
                pass

        return response

    def convert_urls(self, data):
        """
        Recursively convert absolute URLs to relative URLs in the data structure.
        """
        if isinstance(data, dict):
            return {key: self.convert_urls(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.convert_urls(item) for item in data]
        elif isinstance(data, str) and ('localhost' in data or data.startswith('http://')):
            # Convert "http://localhost/api/..." to "/api/..."
            if data.startswith('http://localhost'):
                return data.replace('http://localhost', '')
            elif data.startswith('http://'):
                # For other absolute URLs, make them relative
                parts = data.split('/')
                if len(parts) > 3:
                    return '/' + '/'.join(parts[3:])
            return data
        else:
            return data


class APITimingMiddleware:
    """Middleware to measure and log API response times"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only measure API endpoints
        if request.path.startswith('/api/'):
            start_time = time.time()
            response = self.get_response(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Add response time header
            response['X-Response-Time'] = f'{duration_ms}ms'

            # Log with emoji based on speed
            if duration_ms < 100:
                emoji = '⚡'
            elif duration_ms < 500:
                emoji = '✅'
            elif duration_ms < 2000:
                emoji = '⚠️'
            else:
                emoji = '🐌'

            timing_logger.info(
                f'{emoji} {request.method} {request.path} - {response.status_code} - {duration_ms}ms'
            )

            return response
        else:
            return self.get_response(request)