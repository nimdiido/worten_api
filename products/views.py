"""
Views da API de produtos.
Inclui operações CRUD, download de arquivo e endpoints de scraping.
"""

import logging
from django.utils import timezone
from django.http import FileResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from .models import Product
from .serializers import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductListSerializer,
)
from .services import WortenScraper, SpreadsheetService

logger = logging.getLogger(__name__)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de produtos.

    Disponibiliza listagem, detalhes, criação, atualização e exclusão.
    Toda modificação é sincronizada automaticamente com a planilha.
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_serializer_class(self):
        """Retorna o serializer adequado pra cada tipo de ação."""
        if self.action == "create":
            return ProductCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ProductUpdateSerializer
        elif self.action == "list":
            return ProductListSerializer
        return ProductSerializer

    def _sync_spreadsheet(self):
        """Sincroniza o banco com o arquivo da planilha."""
        try:
            service = SpreadsheetService()
            service.save_from_queryset(Product.objects.all())
        except Exception as e:
            logger.error(f"Erro ao sincronizar planilha: {e}")

    @swagger_auto_schema(
        operation_description="Lista todos os produtos com paginação",
        responses={200: ProductListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        """Lista todos os produtos."""
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Busca um produto específico pelo ID",
        responses={200: ProductSerializer()},
    )
    def retrieve(self, request, *args, **kwargs):
        """Retorna os detalhes de um produto."""
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Cria um novo produto",
        request_body=ProductCreateSerializer,
        responses={201: ProductSerializer()},
    )
    def create(self, request, *args, **kwargs):
        """Cria um produto e sincroniza com a planilha."""
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            self._sync_spreadsheet()
        return response

    @swagger_auto_schema(
        operation_description="Atualiza um produto completamente",
        request_body=ProductUpdateSerializer,
        responses={200: ProductSerializer()},
    )
    def update(self, request, *args, **kwargs):
        """Atualiza um produto e sincroniza com a planilha."""
        response = super().update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            self._sync_spreadsheet()
        return response

    @swagger_auto_schema(
        operation_description="Atualiza parcialmente um produto",
        request_body=ProductUpdateSerializer,
        responses={200: ProductSerializer()},
    )
    def partial_update(self, request, *args, **kwargs):
        """Atualiza parcialmente um produto e sincroniza com a planilha."""
        response = super().partial_update(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            self._sync_spreadsheet()
        return response

    @swagger_auto_schema(
        operation_description="Remove um produto",
        responses={204: "Produto removido com sucesso"},
    )
    def destroy(self, request, *args, **kwargs):
        """Remove um produto e sincroniza com a planilha."""
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            self._sync_spreadsheet()
        return response

    @swagger_auto_schema(
        method="get",
        operation_description="Faz download da planilha de produtos (formato XLSX)",
        responses={
            200: openapi.Response(
                description="Download do arquivo Excel",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            404: "Arquivo não encontrado",
        },
    )
    @action(detail=False, methods=["get"])
    def download(self, request):
        """
        Faz o download da planilha de produtos atual.
        Retorna o arquivo XLSX com todos os dados.
        """
        try:
            service = SpreadsheetService()

            # Garante que a planilha está atualizada
            if Product.objects.exists():
                service.save_from_queryset(Product.objects.all())

            file_path = service.get_output_path()

            if not file_path.exists():
                return Response(
                    {"error": "Arquivo não encontrado. Importe os produtos primeiro."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            response = FileResponse(
                open(file_path, "rb"),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = (
                'attachment; filename="produtos_worten.xlsx"'
            )
            return response

        except Exception as e:
            logger.error(f"Erro no download da planilha: {e}")
            return Response(
                {"error": f"Erro ao gerar arquivo: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @swagger_auto_schema(
        method="post",
        operation_description="Importa produtos da planilha de entrada (data/input/worten.xlsx). Não requer dados no body.",
        request_body=no_body,
        responses={
            200: openapi.Response(
                description="Importação concluída",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "imported": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "skipped": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Erro na importação",
        },
    )
    @action(detail=False, methods=["post"])
    def import_products(self, request):
        """
        Importa produtos da planilha de entrada.
        Lê a planilha original e cria os produtos no banco.
        """
        try:
            service = SpreadsheetService()
            df = service.read_input_spreadsheet()

            imported = 0
            skipped = 0

            for _, row in df.iterrows():
                product_id = str(row.get("ID", ""))
                if not product_id:
                    skipped += 1
                    continue

                product, created = Product.objects.update_or_create(
                    original_id=product_id,
                    defaults={
                        "ean": str(row.get("EAN", "")),
                        "original_name": str(row.get("Name", "")),
                    },
                )

                if created:
                    imported += 1
                else:
                    skipped += 1

            # Salva na planilha de saída
            service.save_from_queryset(Product.objects.all())

            return Response(
                {
                    "message": "Importação concluída com sucesso",
                    "imported": imported,
                    "skipped": skipped,
                }
            )

        except FileNotFoundError as e:
            return Response(
                {"error": f"Arquivo de entrada não encontrado: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Erro na importação: {e}")
            return Response(
                {"error": f"Falha na importação: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @swagger_auto_schema(
        method="post",
        operation_description="Coleta dados de produtos da Worten.pt. Sem body = coleta todos. Com body = coleta IDs específicos.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                "product_ids": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description="Lista de IDs dos produtos (opcional). Se vazio, coleta todos.",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Coleta concluída",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "scraped": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "found": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "not_found": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "errors": openapi.Schema(type=openapi.TYPE_INTEGER),
                    },
                ),
            ),
            400: "Erro na coleta",
        },
    )
    @action(detail=False, methods=["post"])
    def scrape(self, request):
        """
        Coleta dados de produtos na Worten.pt.
        Busca os produtos na Worten e atualiza as informações no banco.
        Opcionalmente recebe uma lista de IDs para coletar produtos específicos.
        """
        # Pega product_ids do body, se existir
        product_ids = request.data.get("product_ids", []) if request.data else []

        if product_ids:
            products = Product.objects.filter(original_id__in=product_ids)
        else:
            products = Product.objects.all()

        if not products.exists():
            return Response(
                {"error": "Nenhum produto para coletar"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scraper = WortenScraper()
        scraped = 0
        found = 0
        not_found = 0
        errors = 0

        for product in products:
            try:
                result = scraper.search_product(
                    query=product.original_name, ean=product.ean
                )

                product.worten_name = result.name
                product.worten_url = result.url
                product.lowest_price = result.price
                product.seller_name = result.seller
                product.is_available = result.is_available
                product.scrape_error = result.error
                product.last_scraped = timezone.now()
                product.save()

                scraped += 1

                if result.is_available:
                    found += 1
                elif result.error:
                    errors += 1
                else:
                    not_found += 1

            except Exception as e:
                logger.error(f"Erro ao coletar produto {product.original_id}: {e}")
                product.scrape_error = str(e)
                product.last_scraped = timezone.now()
                product.save()
                errors += 1

        # Sincroniza com a planilha
        self._sync_spreadsheet()

        return Response(
            {
                "message": "Coleta concluída",
                "scraped": scraped,
                "found": found,
                "not_found": not_found,
                "errors": errors,
            }
        )

    @swagger_auto_schema(
        method="post",
        operation_description="Coleta dados de um único produto pelo ID. Não requer dados no body.",
        request_body=no_body,
        responses={200: ProductSerializer()},
    )
    @action(detail=True, methods=["post"])
    def scrape_single(self, request, pk=None):
        """
        Coleta dados de um único produto na Worten.
        Atualiza os dados do produto e retorna o resultado.
        """
        product = self.get_object()

        try:
            scraper = WortenScraper()
            result = scraper.search_product(
                query=product.original_name, ean=product.ean
            )

            product.worten_name = result.name
            product.worten_url = result.url
            product.lowest_price = result.price
            product.seller_name = result.seller
            product.is_available = result.is_available
            product.scrape_error = result.error
            product.last_scraped = timezone.now()
            product.save()

            # Sincroniza com a planilha
            self._sync_spreadsheet()

            return Response(ProductSerializer(product).data)

        except Exception as e:
            logger.error(f"Erro ao coletar produto {product.original_id}: {e}")
            return Response(
                {"error": f"Falha na coleta: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
