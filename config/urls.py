"""
Configuração de URLs do projeto Worten API.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Configuração do schema Swagger/OpenAPI
schema_view = get_schema_view(
    openapi.Info(
        title="Worten Products API",
        default_version="v1",
        description="""
API para gerenciamento de produtos coletados da Worten.pt.

**Funcionalidades:**
- CRUD completo de produtos
- Importação de planilha Excel
- Web scraping da Worten.pt
- Exportação para Excel
        """,
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("products.urls")),
    # Documentação Swagger
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("swagger.json", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]
