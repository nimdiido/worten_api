"""
Serviço de planilhas - leitura/escrita de dados de produtos.
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)


class SpreadsheetService:
    """Gerencia leitura e escrita de planilhas Excel/CSV."""

    OUTPUT_COLUMNS = [
        "ID",
        "EAN",
        "Nome Original",
        "Nome Worten",
        "Link Worten",
        "Menor Preco",
        "Vendedor",
        "Disponivel",
        "Ultima Atualizacao",
        "Erro",
    ]

    def __init__(
        self, input_path: Optional[Path] = None, output_path: Optional[Path] = None
    ):
        self.input_path = input_path or settings.INPUT_SPREADSHEET
        self.output_path = output_path or settings.OUTPUT_SPREADSHEET
        self._ensure_output_directory()

    def _ensure_output_directory(self):
        output_dir = self.output_path.parent
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

    def read_input_spreadsheet(self) -> pd.DataFrame:
        """Lê a planilha de entrada."""
        if not self.input_path.exists():
            raise FileNotFoundError(
                f"Arquivo de entrada não encontrado: {self.input_path}"
            )

        file_extension = self.input_path.suffix.lower()

        if file_extension == ".xlsx":
            return pd.read_excel(self.input_path, engine="openpyxl")
        elif file_extension == ".xls":
            return pd.read_excel(self.input_path, engine="xlrd")
        elif file_extension == ".csv":
            return pd.read_csv(self.input_path)
        else:
            raise ValueError(f"Formato de arquivo não suportado: {file_extension}")

    def read_output_spreadsheet(self) -> pd.DataFrame:
        """Lê a planilha de saída (ou retorna vazio se não existir)."""
        if not self.output_path.exists():
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

        file_extension = self.output_path.suffix.lower()

        try:
            if file_extension == ".xlsx":
                return pd.read_excel(self.output_path, engine="openpyxl")
            elif file_extension == ".csv":
                return pd.read_csv(self.output_path)
            else:
                return pd.DataFrame(columns=self.OUTPUT_COLUMNS)
        except Exception as e:
            logger.error(f"Erro ao ler arquivo de saída: {e}")
            return pd.DataFrame(columns=self.OUTPUT_COLUMNS)

    def save_products(self, products: List[dict]) -> str:
        """Salva lista de produtos na planilha."""
        df = pd.DataFrame(products, columns=self.OUTPUT_COLUMNS)
        return self._write_spreadsheet(df)

    def save_from_queryset(self, queryset) -> str:
        """Salva produtos do queryset na planilha."""
        products = []
        for product in queryset:
            products.append(
                {
                    "ID": product.original_id,
                    "EAN": product.ean,
                    "Nome Original": product.original_name,
                    "Nome Worten": product.worten_name or "",
                    "Link Worten": product.worten_url or "",
                    "Menor Preco": (
                        float(product.lowest_price) if product.lowest_price else ""
                    ),
                    "Vendedor": product.seller_name or "",
                    "Disponivel": "Sim" if product.is_available else "Nao",
                    "Ultima Atualizacao": (
                        product.last_scraped.strftime("%Y-%m-%d %H:%M:%S")
                        if product.last_scraped
                        else ""
                    ),
                    "Erro": product.scrape_error or "",
                }
            )

        df = pd.DataFrame(products, columns=self.OUTPUT_COLUMNS)
        return self._write_spreadsheet(df)

    def _write_spreadsheet(self, df: pd.DataFrame) -> str:
        """Escreve o DataFrame no arquivo."""
        file_extension = self.output_path.suffix.lower()

        try:
            if file_extension == ".xlsx":
                df.to_excel(self.output_path, index=False, engine="openpyxl")
            elif file_extension == ".csv":
                df.to_csv(self.output_path, index=False, encoding="utf-8-sig")
            else:
                # Se não reconhecer, salva como xlsx
                self.output_path = self.output_path.with_suffix(".xlsx")
                df.to_excel(self.output_path, index=False, engine="openpyxl")

            logger.info(f"Planilha salva: {self.output_path}")
            return str(self.output_path)

        except Exception as e:
            logger.error(f"Erro ao escrever planilha: {e}")
            raise

    def add_product(self, product_data: dict) -> str:
        """Adiciona um produto na planilha."""
        df = self.read_output_spreadsheet()

        row = {
            "ID": product_data.get("original_id", ""),
            "EAN": product_data.get("ean", ""),
            "Nome Original": product_data.get("original_name", ""),
            "Nome Worten": product_data.get("worten_name", ""),
            "Link Worten": product_data.get("worten_url", ""),
            "Menor Preco": product_data.get("lowest_price", ""),
            "Vendedor": product_data.get("seller_name", ""),
            "Disponivel": "Sim" if product_data.get("is_available") else "Nao",
            "Ultima Atualizacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Erro": product_data.get("scrape_error", ""),
        }

        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        return self._write_spreadsheet(df)

    def update_product(self, product_id: str, product_data: dict) -> str:
        """Atualiza um produto na planilha."""
        df = self.read_output_spreadsheet()

        mask = df["ID"] == product_id
        if not mask.any():
            return self.add_product(product_data)

        for col, key in [
            ("EAN", "ean"),
            ("Nome Original", "original_name"),
            ("Nome Worten", "worten_name"),
            ("Link Worten", "worten_url"),
            ("Menor Preco", "lowest_price"),
            ("Vendedor", "seller_name"),
            ("Erro", "scrape_error"),
        ]:
            if key in product_data:
                df.loc[mask, col] = product_data[key]

        if "is_available" in product_data:
            df.loc[mask, "Disponivel"] = (
                "Sim" if product_data["is_available"] else "Nao"
            )

        df.loc[mask, "Ultima Atualizacao"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return self._write_spreadsheet(df)

    def delete_product(self, product_id: str) -> str:
        """Remove um produto da planilha."""
        df = self.read_output_spreadsheet()
        df = df[df["ID"] != product_id]
        return self._write_spreadsheet(df)

    def get_output_path(self) -> Path:
        """Retorna o caminho da planilha de saída."""
        return self.output_path

    def output_exists(self) -> bool:
        """Verifica se o arquivo de saída existe."""
        return self.output_path.exists()
