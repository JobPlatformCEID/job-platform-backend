import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.debug(f"Method: {request.method}")
        logger.debug(f"Path: {request.path}")
        logger.debug(f"Headers: {dict(request.headers)}")
        logger.debug(f"Body: {request.body}")
        response = self.get_response(request)
        logger.debug(f"Status: {response.status_code}")
        logger.debug(f"Response body: {response.content}")
        return response

