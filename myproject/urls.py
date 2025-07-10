from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from scraping_data.views import afficher_rapport_swagger  # Import direct de la vue

schema_view = get_schema_view(
   openapi.Info(
      title="Scraping API",
      default_version='v1',
      description="API exposant des données scrapées",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

def home(request):
    return redirect('schema-swagger-ui')  # redirige vers Swagger UI

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),

    # Route rapport swagger hors de /api/
    path('rapport-swagger/', afficher_rapport_swagger, name='rapport-swagger-html'),

    path('api/', include('scraping_data.urls')),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
]