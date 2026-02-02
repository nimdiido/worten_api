"""
Serviço de scraping da Worten.pt.
Responsável por buscar e extrair dados de produtos do site da Worten.

Obs: O site da Worten usa proteção Cloudflare que pode bloquear requisições
automatizadas. O scraper tenta contornar isso, mas não garante 100% de sucesso.
Em produção, o ideal seria usar uma API oficial ou serviços de proxy rotativo.
"""

import re
import json
import logging
import time
import subprocess
import atexit
from dataclasses import dataclass
from typing import Optional, Dict, Any
from decimal import Decimal
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Suprime warnings do undetected_chromedriver __del__
import warnings
warnings.filterwarnings("ignore", message=".*Exception ignored.*Chrome.__del__.*", category=UserWarning)

# Tenta importar componentes do Selenium
SELENIUM_AVAILABLE = False
UNDETECTED_AVAILABLE = False
WEBDRIVER_MANAGER_AVAILABLE = False

try:
    import undetected_chromedriver as uc

    UNDETECTED_AVAILABLE = True
except ImportError:
    pass

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import WebDriverException

    SELENIUM_AVAILABLE = True
except ImportError:
    pass

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    pass


def get_chrome_version() -> Optional[int]:
    """Detecta a versão do Chrome instalada."""
    try:
        # Windows
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"
        )
        version, _ = winreg.QueryValueEx(key, "version")
        return int(version.split(".")[0])
    except Exception:
        pass

    try:
        # Tenta via linha de comando
        result = subprocess.run(
            ["google-chrome", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            match = re.search(r"(\d+)\.", result.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass

    return None


@dataclass
class ScrapedProduct:
    """Classe que representa os dados coletados de um produto."""

    name: Optional[str] = None
    url: Optional[str] = None
    price: Optional[Decimal] = None
    seller: Optional[str] = None
    is_available: bool = False
    error: Optional[str] = None


class WortenScraper:
    """
    Serviço de scraping do site Worten.pt.
    Busca produtos e extrai informações de preço.

    Suporta diferentes métodos de scraping:
    1. undetected-chromedriver (melhor pra bypassar Cloudflare)
    2. Selenium padrão
    3. Requisições HTTP simples (fallback)
    """

    BASE_URL = "https://www.worten.pt"
    SEARCH_URL = f"{BASE_URL}/search"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self, headless: bool = False, use_selenium: bool = True):
        """
        Inicializa o scraper.

        Args:
            headless: Rodar o browser sem interface (padrão False - Cloudflare bloqueia)
            use_selenium: Usar Selenium pro scraping (padrão True)
        """
        self.headless = headless
        self.use_selenium = use_selenium
        self._driver = None
        self._driver_failed = False
        self._cloudflare_passed = False
        self._session = requests.Session()
        self._session.headers.update(self.HEADERS)
        self._chrome_version = get_chrome_version()

    def _get_driver(self):
        """Obtém ou cria uma instância do WebDriver."""
        if self._driver is not None:
            return self._driver

        if self._driver_failed:
            return None

        # Tenta o undetected-chromedriver primeiro (melhor pro Cloudflare)
        if UNDETECTED_AVAILABLE:
            try:
                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--window-size=1920,1080")

                # Passa a versão do Chrome se detectada
                version_main = self._chrome_version if self._chrome_version else None
                self._driver = uc.Chrome(options=options, version_main=version_main)
                logger.info(
                    f"Usando undetected-chromedriver (Chrome v{self._chrome_version})"
                )

                # Inicializa sessão visitando a homepage pra passar o Cloudflare
                if not self._cloudflare_passed:
                    self._pass_cloudflare()

                return self._driver
            except Exception as e:
                logger.warning(f"Falha ao inicializar undetected-chromedriver: {e}")

        # Fallback pro Selenium padrão com webdriver-manager
        if SELENIUM_AVAILABLE:
            try:
                options = Options()
                if self.headless:
                    options.add_argument("--headless=new")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument(f'--user-agent={self.HEADERS["User-Agent"]}')
                options.add_experimental_option(
                    "excludeSwitches", ["enable-automation"]
                )

                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
                logger.info("Usando Selenium padrão")

                # Inicializa a sessão
                if not self._cloudflare_passed:
                    self._pass_cloudflare()

                return self._driver
            except Exception as e:
                logger.warning(f"Falha ao inicializar Selenium: {e}")

        self._driver_failed = True
        return None

    def _pass_cloudflare(self):
        """Visita a homepage pra passar o desafio do Cloudflare."""
        if not self._driver:
            return

        try:
            logger.info("Passando pelo Cloudflare...")
            self._driver.get(self.BASE_URL)

            # Aguarda o Cloudflare liberar (até 30 segundos)
            for i in range(30):
                title = self._driver.title.lower() if self._driver.title else ""
                if "momento" not in title and "challenge" not in title:
                    self._cloudflare_passed = True
                    logger.info("Cloudflare liberado!")
                    time.sleep(1)
                    return
                time.sleep(1)

            logger.warning("Timeout no Cloudflare - pode não funcionar")
        except Exception as e:
            logger.warning(f"Erro ao passar Cloudflare: {e}")

    def close(self):
        """Fecha o WebDriver de forma limpa."""
        if self._driver:
            try:
                driver = self._driver
                self._driver = None
                self._cloudflare_passed = False
                
                # Desabilita o __del__ do undetected_chromedriver pra evitar o warning
                if hasattr(driver, '__del__'):
                    driver.__del__ = lambda: None
                
                # Tenta parar o serviço primeiro
                if hasattr(driver, 'service') and driver.service:
                    try:
                        driver.service.stop()
                    except Exception:
                        pass
                
                # Fecha o browser
                try:
                    driver.quit()
                except Exception:
                    pass
            except Exception:
                pass

    def search_product(self, query: str, ean: Optional[str] = None) -> ScrapedProduct:
        """
        Busca um produto na Worten.pt.

        Args:
            query: Nome do produto ou termo de busca
            ean: Código de barras EAN (opcional, mas mais preciso)

        Returns:
            ScrapedProduct com os dados extraídos ou informação de erro
        """
        # Monta os termos de busca - prioriza o NOME do produto (EAN geralmente não retorna resultados)
        search_terms = []

        if query:
            # Extrai palavras-chave do nome do produto
            words = query.split()
            # Pega as 3-4 primeiras palavras significativas (ignora palavras comuns)
            skip_words = {
                "de",
                "da",
                "do",
                "das",
                "dos",
                "e",
                "ou",
                "com",
                "para",
                "em",
                "um",
                "uma",
            }
            significant = [
                w for w in words if w.lower() not in skip_words and len(w) > 2
            ]
            if significant:
                search_terms.append(" ".join(significant[:4]))
            if len(words) <= 5:
                search_terms.append(query)

        if not search_terms:
            return ScrapedProduct(
                is_available=False, error="Nenhum termo de busca informado"
            )

        # Usa Selenium (necessário pra passar o Cloudflare)
        if self.use_selenium and not self._driver_failed:
            for term in search_terms:
                result = self._search_with_selenium(term)
                if result.is_available or result.url:
                    return result
                # Pequeno delay entre buscas
                time.sleep(0.5)

        return ScrapedProduct(
            is_available=False, error="Produto não encontrado na Worten"
        )

    def _search_with_selenium(self, search_term: str) -> ScrapedProduct:
        """Busca usando Selenium WebDriver."""
        try:
            driver = self._get_driver()
            if not driver:
                return ScrapedProduct(error="WebDriver não disponível")

            search_url = f"{self.SEARCH_URL}?query={quote_plus(search_term)}"
            driver.get(search_url)

            # Aguarda a página carregar
            if not self._wait_for_page_load(driver):
                return ScrapedProduct(error="Timeout no Cloudflare")

            # Aceita cookies se aparecer
            self._accept_cookies(driver)

            # Espera os cards de produto carregarem (até 15 segundos)
            product_loaded = False
            for _ in range(15):
                time.sleep(1)
                try:
                    # Scroll para forçar lazy loading
                    driver.execute_script("window.scrollTo(0, 300)")
                    # Verifica se tem product cards
                    cards = driver.find_elements(By.CSS_SELECTOR, ".product-card, article.product-card")
                    if cards:
                        product_loaded = True
                        logger.info(f"Encontrados {len(cards)} product cards")
                        break
                except Exception:
                    pass
            
            if not product_loaded:
                logger.warning("Nenhum product card encontrado após espera")

            # Verifica se redirecionou pra página do produto
            if "/p/" in driver.current_url:
                return self._extract_product_page(driver, driver.current_url)

            # Verifica se não encontrou resultados
            page_source = driver.page_source.lower()
            if "sem resultados" in page_source or "nenhum resultado" in page_source:
                return ScrapedProduct(
                    is_available=False, error="Nenhum resultado encontrado"
                )

            # Tenta extração via JSON primeiro (mais confiável)
            result = self._extract_from_page_data(driver.page_source)
            if result and (result.is_available or result.url):
                return result

            # Extração via DOM como fallback
            return self._extract_from_search_dom(driver)

        except WebDriverException as e:
            logger.error(f"Erro do WebDriver para {search_term}: {e}")
            self._driver_failed = True
            self._driver = None
            return ScrapedProduct(error=f"Erro WebDriver: {str(e)[:100]}")
        except Exception as e:
            logger.error(f"Erro Selenium para {search_term}: {e}")
            return ScrapedProduct(error=f"Erro Selenium: {str(e)[:100]}")

    def _search_with_requests(self, search_term: str) -> ScrapedProduct:
        """Busca usando requisições HTTP (pode ser bloqueado pelo Cloudflare)."""
        try:
            search_url = f"{self.SEARCH_URL}?query={quote_plus(search_term)}"
            response = self._session.get(search_url, timeout=15)

            if response.status_code == 403:
                return ScrapedProduct(error="Bloqueado pelo Cloudflare (403)")

            if response.status_code != 200:
                return ScrapedProduct(error=f"HTTP {response.status_code}")

            # Verifica se caiu na página do Cloudflare
            if (
                "challenge" in response.text.lower()
                or "momento" in response.text.lower()[:500]
            ):
                return ScrapedProduct(error="Desafio Cloudflare detectado")

            # Tenta extração JSON primeiro
            result = self._extract_from_page_data(response.text)
            if result and (result.is_available or result.url):
                return result

            # Extração HTML
            return self._extract_from_search_html(response.text)

        except requests.Timeout:
            return ScrapedProduct(error="Timeout na requisição")
        except requests.RequestException as e:
            return ScrapedProduct(error=f"Erro na requisição: {str(e)[:100]}")

    def _wait_for_page_load(self, driver, timeout: int = 10) -> bool:
        """Aguarda a página carregar (Cloudflare já deve ter passado)."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                title = driver.title.lower() if driver.title else ""
                # Verifica se ainda tá no desafio do Cloudflare
                if "momento" in title or "challenge" in title:
                    time.sleep(1)
                    continue
                # Página carregou
                return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def _accept_cookies(self, driver):
        """Aceita o popup de cookies se aparecer."""
        if not SELENIUM_AVAILABLE:
            return
        try:
            for selector in ["#onetrust-accept-btn-handler", 'button[id*="accept"]']:
                try:
                    btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    btn.click()
                    time.sleep(0.5)
                    return
                except Exception:
                    continue
        except Exception:
            pass

    def _extract_from_page_data(self, html: str) -> Optional[ScrapedProduct]:
        """Extrai dados do JSON embutido pelo Next.js na página."""
        try:
            match = re.search(
                r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
            )
            if not match:
                return None

            data = json.loads(match.group(1))
            props = data.get("props", {}).get("pageProps", {})

            # Resultados de busca
            for key in ["searchData", "initialData", "data"]:
                search_data = props.get(key, {})
                if not search_data:
                    continue

                products = (
                    search_data.get("products", [])
                    or search_data.get("items", [])
                    or search_data.get("results", [])
                )

                if products:
                    return self._parse_product_json(products[0])

            # Página de produto único
            product_data = props.get("product", {}) or props.get("productData", {})
            if product_data:
                return self._parse_product_json(product_data)

            return None
        except Exception:
            return None

    def _parse_product_json(self, product: Dict[str, Any]) -> ScrapedProduct:
        """Faz o parse do produto a partir do JSON."""
        try:
            name = product.get("name") or product.get("title")

            url = None
            slug = product.get("slug") or product.get("url")
            if slug:
                url = slug if slug.startswith("http") else f"{self.BASE_URL}{slug}"

            price = self._get_price_from_json(product)
            seller = self._get_seller_from_json(product)
            is_available = bool(price) and (
                product.get("available", True) or product.get("inStock", True)
            )

            return ScrapedProduct(
                name=name,
                url=url,
                price=price,
                seller=seller,
                is_available=is_available,
            )
        except Exception:
            return ScrapedProduct(error="Erro ao parsear produto do JSON")

    def _get_price_from_json(self, product: Dict) -> Optional[Decimal]:
        """Extrai o preço do JSON."""
        for field, subfield in [
            ("price", "value"),
            ("price", "current"),
            ("prices", "current"),
        ]:
            data = product.get(field, {})
            if isinstance(data, dict) and subfield in data:
                try:
                    return Decimal(str(data[subfield]))
                except Exception:
                    pass

        for field in ["currentPrice", "salePrice", "price"]:
            value = product.get(field)
            if value and not isinstance(value, dict):
                try:
                    return Decimal(str(value))
                except Exception:
                    pass
        return None

    def _get_seller_from_json(self, product: Dict) -> str:
        """Extrai o vendedor do JSON."""
        seller = product.get("seller", {})
        if isinstance(seller, dict):
            return seller.get("name", "Worten")
        return "Worten"

    def _extract_product_page(self, driver, url: str) -> ScrapedProduct:
        """Extrai dados da página de produto via DOM."""
        result = self._extract_from_page_data(driver.page_source)
        if result and result.name:
            result.url = url
            return result

        name = None
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "h1")
            name = elem.text.strip()
        except Exception:
            pass

        price = self._extract_price_dom(driver)
        seller = self._extract_seller_dom(driver)

        return ScrapedProduct(
            name=name,
            url=url,
            price=price,
            seller=seller,
            is_available=price is not None,
        )

    def _extract_from_search_dom(self, driver) -> ScrapedProduct:
        """Extrai dados dos resultados de busca via DOM."""
        try:
            # Importa By localmente se não estiver disponível globalmente
            from selenium.webdriver.common.by import By as SeleniumBy
            from selenium.webdriver.support.ui import WebDriverWait as SeleniumWait
            from selenium.webdriver.support import expected_conditions as SeleniumEC
        except ImportError:
            return ScrapedProduct(error="Selenium não disponível")

        try:
            product = None
            # Seletores atualizados para estrutura atual da Worten
            for selector in [
                "article.product-card",
                ".product-card",
                '[data-testid="product-card"]',
                'article[itemtype*="Product"]',
            ]:
                try:
                    product = SeleniumWait(driver, 5).until(
                        SeleniumEC.presence_of_element_located((SeleniumBy.CSS_SELECTOR, selector))
                    )
                    if product:
                        logger.info(f"Produto encontrado com seletor: {selector}")
                        break
                except Exception:
                    continue

            if not product:
                return ScrapedProduct(
                    is_available=False, error="Nenhum produto encontrado no DOM"
                )

            # Extrai URL - tenta link dentro do card
            url = None
            try:
                link = product.find_element(SeleniumBy.CSS_SELECTOR, 'a[href*="/produtos/"]')
                url = link.get_attribute("href")
            except Exception:
                try:
                    link = product.find_element(SeleniumBy.TAG_NAME, "a")
                    href = link.get_attribute("href")
                    if href and "/produtos/" in href:
                        url = href
                except Exception:
                    pass

            # Extrai nome - seletores atualizados
            name = None
            for sel in [".product-card__name-and-features", "h3", "h2", '[class*="name"]']:
                try:
                    elem = product.find_element(SeleniumBy.CSS_SELECTOR, sel)
                    name = elem.text.strip()
                    if name:
                        break
                except Exception:
                    continue

            price = self._extract_price_card(product)
            seller = self._extract_seller_card(product)

            return ScrapedProduct(
                name=name,
                url=url,
                price=price,
                seller=seller,
                is_available=price is not None,
            )
        except Exception as e:
            logger.error(f"Erro na extração DOM: {e}")
            return ScrapedProduct(error=f"Erro na extração DOM: {str(e)[:100]}")

    def _extract_from_search_html(self, html: str) -> ScrapedProduct:
        """Extrai dados dos resultados de busca via BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, "html.parser")

            product = None
            for selector in [
                '[data-testid="product-card"]',
                ".product-card",
                "article",
            ]:
                product = soup.select_one(selector)
                if product:
                    break

            if not product:
                return ScrapedProduct(
                    is_available=False, error="Nenhum produto no HTML"
                )

            url: Optional[str] = None
            link = product.select_one('a[href*="/p/"]') or product.select_one("a")
            if link and link.get("href"):
                href = str(link["href"])
                url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

            name = None
            for selector in ["h3", "h2", '[class*="name"]']:
                elem = product.select_one(selector)
                if elem:
                    name = elem.get_text(strip=True)
                    if name:
                        break

            price = self._extract_price_html(product)
            seller = self._extract_seller_html(product)

            return ScrapedProduct(
                name=name,
                url=url,
                price=price,
                seller=seller,
                is_available=price is not None,
            )
        except Exception as e:
            return ScrapedProduct(error=f"Erro na extração HTML: {str(e)[:100]}")

    def _extract_price_dom(self, driver) -> Optional[Decimal]:
        """Extrai preço do DOM."""
        if not SELENIUM_AVAILABLE:
            return None
        for selector in ['[class*="price"]', 'span[class*="Price"]']:
            try:
                elem = driver.find_element(By.CSS_SELECTOR, selector)
                return self._parse_price(elem.text)
            except Exception:
                continue
        return None

    def _extract_price_card(self, card) -> Optional[Decimal]:
        """Extrai preço do card de produto."""
        try:
            from selenium.webdriver.common.by import By as SeleniumBy
        except ImportError:
            return None
        # Seletores atualizados para estrutura Worten
        for selector in [".product-card__price", '[class*="price"]', '[class*="Price"]']:
            try:
                elem = card.find_element(SeleniumBy.CSS_SELECTOR, selector)
                price_text = elem.text.replace('\n', '').replace(' ', '')
                return self._parse_price(price_text)
            except Exception:
                continue
        return None

    def _extract_price_html(self, soup_elem) -> Optional[Decimal]:
        """Extrai preço do elemento BeautifulSoup."""
        for selector in ['[class*="price"]', "span"]:
            elem = soup_elem.select_one(selector)
            if elem:
                price = self._parse_price(elem.get_text())
                if price:
                    return price
        return None

    def _extract_seller_dom(self, driver) -> str:
        """Extrai vendedor do DOM."""
        if not SELENIUM_AVAILABLE:
            return "Worten"
        try:
            elem = driver.find_element(By.CSS_SELECTOR, '[class*="seller"]')
            return elem.text.strip() or "Worten"
        except Exception:
            return "Worten"

    def _extract_seller_card(self, card) -> str:
        """Extrai vendedor do card de produto."""
        try:
            from selenium.webdriver.common.by import By as SeleniumBy
        except ImportError:
            return "Worten"
        try:
            elem = card.find_element(SeleniumBy.CSS_SELECTOR, '.product-card__seller, [class*="seller"]')
            seller_text = elem.text.strip()
            # Remove prefixos comuns
            if seller_text.startswith("Vendido por "):
                seller_text = seller_text.replace("Vendido por ", "")
            return seller_text or "Worten"
        except Exception:
            return "Worten"
            return "Worten"

    def _extract_seller_html(self, soup_elem) -> str:
        """Extrai vendedor do elemento HTML."""
        elem = soup_elem.select_one('[class*="seller"]')
        if elem:
            return elem.get_text(strip=True) or "Worten"
        return "Worten"

    def _parse_price(self, text: str) -> Optional[Decimal]:
        """Faz o parse do preço a partir do texto."""
        if not text:
            return None

        cleaned = re.sub(r"[€EUR\s]", "", text)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")

        match = re.search(r"(\d+\.?\d*)", cleaned)
        if match:
            try:
                value = Decimal(match.group(1))
                if value > 0:
                    return value
            except Exception:
                pass
        return None
