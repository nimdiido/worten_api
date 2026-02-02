"""
Comando para importar produtos e coletar dados da Worten.
"""

import time
from django.utils import timezone
from django.core.management.base import BaseCommand, CommandError
from products.models import Product
from products.services import WortenScraper, SpreadsheetService


class Command(BaseCommand):
    help = "Importa produtos da planilha e coleta dados da Worten.pt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--import-only",
            action="store_true",
            help="Apenas importar produtos, sem fazer scraping",
        )
        parser.add_argument(
            "--scrape-only",
            action="store_true",
            help="Apenas fazer scraping, sem reimportar",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limitar quantidade de produtos (0 = todos)",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.5,
            help="Delay entre requisições em segundos (padrão: 0.5)",
        )
        parser.add_argument(
            "--headless",
            action="store_true",
            help="Rodar sem interface (pode ser bloqueado pelo Cloudflare)",
        )

    def handle(self, *args, **options):
        import_only = options["import_only"]
        scrape_only = options["scrape_only"]
        limit = options["limit"]
        delay = options["delay"]
        headless = options["headless"]

        spreadsheet_service = SpreadsheetService()

        # Importa produtos
        if not scrape_only:
            self.stdout.write(self.style.NOTICE("Importando produtos da planilha..."))
            try:
                df = spreadsheet_service.read_input_spreadsheet()
                imported = 0
                updated = 0

                for _, row in df.iterrows():
                    product_id = str(row.get("ID", ""))
                    if not product_id:
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
                        updated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Importados {imported} novos produtos, atualizados {updated} existentes."
                    )
                )

            except FileNotFoundError as e:
                raise CommandError(f"Arquivo não encontrado: {e}")
            except Exception as e:
                raise CommandError(f"Erro na importação: {e}")

        # Coleta dados dos produtos
        if not import_only:
            self.stdout.write(self.style.NOTICE("Coletando dados da Worten.pt..."))
            if not headless:
                self.stdout.write(
                    self.style.WARNING(
                        "NOTA: O Chrome vai abrir (necessário pra contornar o Cloudflare)"
                    )
                )

            scraper = WortenScraper(headless=headless)
            products = Product.objects.all()

            if limit > 0:
                products = products[:limit]

            total = products.count()
            found = 0
            not_found = 0
            errors = 0

            try:
                for i, product in enumerate(products, 1):
                    self.stdout.write(f"[{i}/{total}] {product.original_name[:50]}...")

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

                        if result.is_available:
                            found += 1
                            price_str = f"{result.price}€" if result.price else "N/A"
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'  -> {price_str} ({result.seller or "Worten"})'
                                )
                            )
                        elif result.error:
                            errors += 1
                            self.stdout.write(
                                self.style.WARNING(f"  -> {result.error}")
                            )
                        else:
                            not_found += 1
                            self.stdout.write(self.style.WARNING("  -> Não encontrado"))

                    except Exception as e:
                        errors += 1
                        product.scrape_error = str(e)
                        product.last_scraped = timezone.now()
                        product.save()
                        self.stdout.write(self.style.ERROR(f"  -> Exceção: {e}"))

                    # Delay entre requisições
                    if i < total:
                        time.sleep(delay)

            finally:
                # Sempre fecha o browser
                self.stdout.write(self.style.NOTICE("Fechando navegador..."))
                scraper.close()

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nColeta concluída: {found} encontrados, {not_found} não encontrados, {errors} erros"
                )
            )

        # Salva na planilha de saída
        self.stdout.write(self.style.NOTICE("Salvando na planilha de saída..."))
        try:
            output_path = spreadsheet_service.save_from_queryset(Product.objects.all())
            self.stdout.write(self.style.SUCCESS(f"Salvo em: {output_path}"))
        except Exception as e:
            raise CommandError(f"Erro ao salvar planilha: {e}")

        self.stdout.write(self.style.SUCCESS("Pronto!"))
