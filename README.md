# Worten Products API

Sistema de gerenciamento de produtos com scraping de dados do site Worten.pt.

## Funcionalidades

- **CRUD de Produtos**: Criar, ler, atualizar e deletar produtos via API REST
- **Importação de Planilha**: Importar produtos a partir de arquivo Excel (.xlsx)
- **Web Scraping**: Buscar dados atualizados de produtos no site Worten.pt
- **Exportação**: Download do arquivo Excel com todos os dados
- **Documentação Swagger**: API documentada e testável via interface web

---

## Roteiro de Demonstração

### Passo 1: Iniciar o Servidor

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar ambiente virtual
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Executar migrações do banco de dados
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

---

### Passo 2: Importar Produtos da Planilha

**Via Swagger:**

1. Acesse `/api/products/import_products/`
2. Clique em "Try it out" > "Execute"

**Via Terminal:**

```bash
curl -X POST http://127.0.0.1:8000/api/products/import_products/
```

**Resultado esperado:**

```json
{
  "message": "Import completed successfully",
  "imported": 86,
  "skipped": 0
}
```

---

### Passo 3: Listar Produtos (READ)

**Via Swagger:**

1. Acesse `GET /api/products/`
2. Clique em "Try it out" > "Execute"

**Via Terminal:**

```bash
curl http://127.0.0.1:8000/api/products/
```

**Resultado esperado:** Lista paginada com 86 produtos

---

### Passo 4: Criar Produto (CREATE)

**Via Swagger:**

1. Acesse `POST /api/products/`
2. Clique em "Try it out"
3. Cole o JSON abaixo e clique "Execute"

```json
{
  "original_id": "DEMO001",
  "ean": "1234567890123",
  "original_name": "Produto de Demonstração"
}
```

**Via Terminal:**

```bash
curl -X POST http://127.0.0.1:8000/api/products/ ^
  -H "Content-Type: application/json" ^
  -d "{\"original_id\": \"DEMO001\", \"ean\": \"1234567890123\", \"original_name\": \"Produto de Demonstração\"}"
```

**Resultado esperado:** Produto criado com ID gerado

---

### Passo 5: Buscar Produto Específico (READ)

**Via Terminal:**

```bash
curl http://127.0.0.1:8000/api/products/1/
```

**Resultado esperado:** Detalhes completos do produto ID 1

---

### Passo 6: Atualizar Produto (UPDATE)

**Via Swagger:**

1. Acesse `PATCH /api/products/{id}/`
2. Informe o ID do produto criado (ex: 87)
3. Cole o JSON:

```json
{
  "original_name": "Produto Atualizado via API"
}
```

**Via Terminal:**

```bash
curl -X PATCH http://127.0.0.1:8000/api/products/87/ ^
  -H "Content-Type: application/json" ^
  -d "{\"original_name\": \"Produto Atualizado via API\"}"
```

---

### Passo 7: Deletar Produto (DELETE)

**Via Swagger:**

1. Acesse `DELETE /api/products/{id}/`
2. Informe o ID do produto de teste
3. Execute

**Via Terminal:**

```bash
curl -X DELETE http://127.0.0.1:8000/api/products/87/
```

**Resultado esperado:** Status 204 (No Content)

---

### Passo 8: Web Scraping (Worten.pt)

**IMPORTANTE:** O Chrome vai abrir durante o scraping (necessário para contornar proteção Cloudflare).

**Via Linha de Comando (Recomendado):**

```bash
# Scraping de 5 produtos (demonstração rápida)
python manage.py import_and_scrape --scrape-only --limit 5

# Scraping completo (todos os 86 produtos)
python manage.py import_and_scrape --scrape-only
```

**Resultado esperado:**

```
Scraping products from Worten.pt...
NOTA: Chrome vai abrir (necessário para contornar Cloudflare)
[1/5] Cesta Decorativa Alexandra House Living...
  -> 54.99€ (Vendido por PETRO SHOP)
[2/5] Cesta Decorativa Alexandra House Living...
  -> 54.99€ (Vendido por PETRO SHOP)
...
Scraping complete: 5 found, 0 not found, 0 errors
```

---

### Passo 9: Download da Planilha

**Via Browser:**
Acesse: http://127.0.0.1:8000/api/products/download/

**Via Terminal:**

```bash
curl -OJ http://127.0.0.1:8000/api/products/download/
```

**Resultado esperado:** Arquivo `produtos_worten.xlsx` baixado com todos os dados

---

### Passo 10: Verificar Sincronização

1. Abra o arquivo `data/output/produtos_worten.xlsx`
2. Verifique que os dados do scraping estão lá
3. Crie um produto via API
4. Baixe novamente a planilha
5. Confirme que o novo produto aparece no arquivo

---

## Resumo dos Endpoints

| Método | Endpoint                            | Descrição                     |
| ------ | ----------------------------------- | ----------------------------- |
| GET    | `/api/products/`                    | Listar todos os produtos      |
| POST   | `/api/products/`                    | Criar novo produto            |
| GET    | `/api/products/{id}/`               | Obter produto específico      |
| PUT    | `/api/products/{id}/`               | Atualizar produto completo    |
| PATCH  | `/api/products/{id}/`               | Atualizar parcialmente        |
| DELETE | `/api/products/{id}/`               | Deletar produto               |
| GET    | `/api/products/download/`           | Download da planilha XLSX     |
| POST   | `/api/products/import_products/`    | Importar da planilha original |
| POST   | `/api/products/scrape/`             | Scraping de todos os produtos |
| POST   | `/api/products/{id}/scrape_single/` | Scraping de um produto        |

---

## Instalação Completa

### Requisitos

- Python 3.8+
- Google Chrome (para scraping)
- pip

### Passos

```bash
# 1. Criar ambiente virtual
python -m venv venv

# 2. Ativar ambiente virtual (Windows)
venv\Scripts\activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar migrações
python manage.py migrate

# 5. Iniciar servidor
python manage.py runserver
```

### Documentação

- **Swagger UI**: http://127.0.0.1:8000/swagger/
- **ReDoc**: http://127.0.0.1:8000/redoc/

---

## Estrutura do Projeto

```
worten_api/
├── config/                 # Configurações Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── products/               # App principal
│   ├── management/
│   │   └── commands/
│   │       └── import_and_scrape.py
│   ├── services/
│   │   ├── scraper.py      # Web scraping Worten
│   │   └── spreadsheet.py  # Manipulação de planilhas
│   ├── models.py           # Modelo Product
│   ├── serializers.py      # Serializers DRF
│   ├── views.py            # ViewSet com CRUD
│   └── urls.py
├── data/
│   ├── input/
│   │   └── worten.xlsx         # Planilha de entrada (produtos a buscar)
│   └── output/
│       └── produtos_worten.xlsx  # Planilha de saída (resultado)
├── manage.py
├── requirements.txt
└── README.md
```

---

## Campos do Produto

| Campo           | Tipo     | Descrição                 |
| --------------- | -------- | ------------------------- |
| `id`            | int      | ID interno do banco       |
| `original_id`   | string   | ID original da planilha   |
| `ean`           | string   | Código de barras EAN      |
| `original_name` | string   | Nome original do produto  |
| `worten_name`   | string   | Nome encontrado na Worten |
| `worten_url`    | string   | Link do produto na Worten |
| `lowest_price`  | decimal  | Menor preço encontrado    |
| `seller_name`   | string   | Vendedor com menor preço  |
| `is_available`  | boolean  | Disponibilidade           |
| `last_scraped`  | datetime | Data do último scraping   |
| `scrape_error`  | string   | Erro (se houver)          |

---

## Sobre o Web Scraping

### Estratégia Utilizada

O site Worten.pt utiliza proteção **Cloudflare** que bloqueia requisições automatizadas.
Para contornar, o scraper utiliza:

1. **undetected-chromedriver**: ChromeDriver modificado que evita detecção
2. **Modo visível**: Chrome abre em janela (headless é bloqueado pelo Cloudflare)
3. **Sessão persistente**: Reutiliza a mesma sessão para todas as buscas

### Dados Extraídos

Para cada produto, o scraper busca na Worten e extrai:

- Nome do produto na Worten
- Link direto para a página
- Menor preço disponível
- Nome do vendedor/loja

### Produtos Não Encontrados

Quando um produto não é encontrado na Worten:

- `is_available` = `false`
- `scrape_error` = mensagem descritiva
- Campos de preço/vendedor ficam vazios

---

## Sincronizacao Automatica

**Toda alteracao via API e salva automaticamente no arquivo XLSX:**

- `POST /api/products/` → Cria produto → Atualiza XLSX
- `PUT /api/products/{id}/` → Atualiza produto → Atualiza XLSX
- `PATCH /api/products/{id}/` → Atualiza parcial → Atualiza XLSX
- `DELETE /api/products/{id}/` → Deleta produto → Atualiza XLSX

O arquivo de saida fica em: `data/output/produtos_worten.xlsx`

---

## Tecnologias Utilizadas

| Tecnologia              | Uso                   |
| ----------------------- | --------------------- |
| Django 5.2              | Framework web         |
| Django REST Framework   | API REST              |
| drf-yasg                | Documentacao Swagger  |
| Selenium                | Automacao de browser  |
| undetected-chromedriver | Bypass Cloudflare     |
| BeautifulSoup4          | Parsing HTML          |
| Pandas                  | Manipulacao de dados  |
| openpyxl                | Leitura/escrita Excel |

---

## Comandos Uteis

```bash
# Importar e fazer scraping completo
python manage.py import_and_scrape

# Apenas importar planilha (sem scraping)
python manage.py import_and_scrape --import-only

# Apenas scraping (sem reimportar)
python manage.py import_and_scrape --scrape-only

# Limitar quantidade (para testes)
python manage.py import_and_scrape --scrape-only --limit 10

# Ajustar delay entre requisicoes
python manage.py import_and_scrape --delay 1.0
```

---

## Autor

Desenvolvido como teste técnico para vaga de Backend Python.
