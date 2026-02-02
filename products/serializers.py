"""
Serializers para os endpoints da API de produtos.
Transformam os objetos do banco em JSON e vice-versa.
"""

from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer completo do produto.
    Usado nas views de detalhe e operações de criação/atualização.
    """

    class Meta:
        model = Product
        fields = [
            "id",
            "original_id",
            "ean",
            "original_name",
            "worten_name",
            "worten_url",
            "lowest_price",
            "seller_name",
            "is_available",
            "last_scraped",
            "scrape_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criar novos produtos.
    Exige apenas os campos essenciais da planilha original.
    """

    class Meta:
        model = Product
        fields = [
            "original_id",
            "ean",
            "original_name",
        ]

    def validate_original_id(self, value):
        """Valida se o ID já existe no banco."""
        if Product.objects.filter(original_id=value).exists():
            raise serializers.ValidationError(
                f"Já existe um produto com o ID '{value}'."
            )
        return value


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para atualizar produtos existentes.
    """

    class Meta:
        model = Product
        fields = [
            "original_id",
            "ean",
            "original_name",
            "worten_name",
            "worten_url",
            "lowest_price",
            "seller_name",
            "is_available",
            "scrape_error",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listagem.
    Só os campos principais pra não pesar a resposta.
    """

    class Meta:
        model = Product
        fields = [
            "id",
            "original_id",
            "original_name",
            "worten_name",
            "lowest_price",
            "seller_name",
            "is_available",
        ]


class ProductScrapeSerializer(serializers.Serializer):
    """
    Serializer para disparar a coleta de dados.
    """

    product_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Lista de IDs dos produtos para coletar. Se vazio, coleta todos.",
    )
