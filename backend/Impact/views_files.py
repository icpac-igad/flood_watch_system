import os
from pathlib import Path
from django.http import FileResponse, JsonResponse, Http404
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# Base directory for serving files
FILES_BASE_DIR = getattr(settings, 'FILES_BASE_DIR', '/data')

@api_view(['GET'])
def serve_file(request, file_path):
    """
    Serve files from the configured base directory.
    """
    try:
        # Construct the full file path
        full_path = Path(FILES_BASE_DIR) / file_path

        # Security check: ensure the path is within the base directory
        full_path = full_path.resolve()
        base_path = Path(FILES_BASE_DIR).resolve()

        if not str(full_path).startswith(str(base_path)):
            raise Http404("File not found")

        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            raise Http404("File not found")

        # Serve the file
        response = FileResponse(
            open(full_path, 'rb'),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'inline; filename="{full_path.name}"'

        return response

    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'detail': 'File not found or inaccessible'
        }, status=404)

@api_view(['GET'])
def list_files(request):
    """
    List available files in a directory.
    """
    directory = request.GET.get('dir', '')

    try:
        # Construct the full directory path
        full_path = Path(FILES_BASE_DIR) / directory

        # Security check: ensure the path is within the base directory
        full_path = full_path.resolve()
        base_path = Path(FILES_BASE_DIR).resolve()

        if not str(full_path).startswith(str(base_path)):
            return JsonResponse({
                'error': 'Invalid directory path'
            }, status=400)

        # Check if directory exists
        if not full_path.exists() or not full_path.is_dir():
            return JsonResponse({
                'error': 'Directory not found'
            }, status=404)

        # List files and directories
        items = []
        for item in full_path.iterdir():
            item_info = {
                'name': item.name,
                'type': 'directory' if item.is_dir() else 'file',
                'size': item.stat().st_size if item.is_file() else None,
                'path': str(item.relative_to(base_path))
            }
            items.append(item_info)

        return JsonResponse({
            'directory': directory,
            'items': items
        })

    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)