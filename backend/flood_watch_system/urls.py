from django.contrib import admin
from django.urls import path, include, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import TemplateView

def redirect_to_frontend(request):
    # Adjust the frontend URL according to your setup (typically localhost:3000 for React)
    return redirect('http://127.0.0.1:8094')

urlpatterns = [
    # Frontend redirect for root path
    path('', redirect_to_frontend, name='redirect-to-frontend'),
    
    # Admin and API routes
    path('admin/', admin.site.urls),
    path('api/', include('Impact.urls')),
    path('api/auth/', include('rest_framework.urls')),
    
    # API documentation routes
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Catch all other routes and serve the frontend
    re_path(r'^(?!admin/)(?!api/)(?!assets/).*$', 
            TemplateView.as_view(template_name='index.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
