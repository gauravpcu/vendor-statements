"""
AWS Lambda handler for Vendor Statements Flask application
"""
import os
import sys
import json
import base64
from io import BytesIO

# Set up environment for Lambda
os.environ['LAMBDA_ENVIRONMENT'] = 'true'

# Import the Flask app
from app import app

def lambda_handler(event, context):
    """
    AWS Lambda handler for Flask application with enhanced file upload support
    """
    try:
        # Handle different event types
        if 'httpMethod' not in event:
            # Handle direct invocation or other event types
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Vendor Statements API is running on Lambda'})
            }
        
        # Extract HTTP method and path
        http_method = event['httpMethod']
        path = event.get('path', '/')
        query_string = event.get('queryStringParameters') or {}
        headers = event.get('headers', {})
        body = event.get('body', '')
        is_base64 = event.get('isBase64Encoded', False)
        
        # Handle base64 encoded body (for file uploads)
        if is_base64 and body:
            body = base64.b64decode(body)
        
        # Create WSGI environ
        environ = {
            'REQUEST_METHOD': http_method,
            'PATH_INFO': path,
            'QUERY_STRING': '&'.join([f'{k}={v}' for k, v in query_string.items()]),
            'CONTENT_TYPE': headers.get('content-type', ''),
            'CONTENT_LENGTH': str(len(body)) if body else '0',
            'SERVER_NAME': headers.get('host', 'localhost'),
            'SERVER_PORT': '443',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'https',
            'wsgi.input': BytesIO(body.encode() if isinstance(body, str) else body),
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
        }
        
        # Add headers to environ
        for key, value in headers.items():
            key = key.upper().replace('-', '_')
            if key not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
                environ[f'HTTP_{key}'] = value
        
        # Capture response
        response_data = []
        status = None
        response_headers = []
        
        def start_response(status_line, headers_list):
            nonlocal status, response_headers
            status = int(status_line.split(' ', 1)[0])
            response_headers = headers_list
        
        # Call Flask app
        with app.app_context():
            app_response = app(environ, start_response)
            response_data = b''.join(app_response)
        
        # Determine if response should be base64 encoded
        content_type = next((h[1] for h in response_headers if h[0].lower() == 'content-type'), 'text/html')
        is_binary = not content_type.startswith(('text/', 'application/json', 'application/javascript'))
        
        # Format response
        lambda_response = {
            'statusCode': status or 200,
            'headers': {h[0]: h[1] for h in response_headers},
            'body': base64.b64encode(response_data).decode() if is_binary else response_data.decode(),
            'isBase64Encoded': is_binary
        }
        
        return lambda_response
        
    except Exception as e:
        print(f"Lambda handler error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

# For compatibility with different Lambda runtimes
handler = lambda_handler
