from django.db import models


class Product(models.Model):
    """
    Modelo que representa um produto com dados coletados da Worten.
    """

    # Campos da planilha original
    original_id = models.CharField(
        max_length=50, unique=True, help_text="ID do produto na planilha"
    )
    ean = models.CharField(max_length=50, blank=True, help_text="Código de barras EAN")
    original_name = models.CharField(
        max_length=500, help_text="Nome original do produto"
    )

    # Dados coletados da Worten
    worten_name = models.CharField(
        max_length=500, blank=True, null=True, help_text="Nome do produto na Worten"
    )
    worten_url = models.URLField(
        max_length=1000, blank=True, null=True, help_text="Link do produto na Worten"
    )
    lowest_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Menor preço encontrado",
    )
    seller_name = models.CharField(
        max_length=200, blank=True, null=True, help_text="Vendedor com menor preço"
    )

    # Campos de status
    is_available = models.BooleanField(
        default=False, help_text="Disponibilidade na Worten"
    )
    last_scraped = models.DateTimeField(
        blank=True, null=True, help_text="Data da última coleta"
    )
    scrape_error = models.TextField(
        blank=True, null=True, help_text="Mensagem de erro, se houver"
    )

    # Datas de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["original_id"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return f"{self.original_id} - {self.original_name[:50]}"
