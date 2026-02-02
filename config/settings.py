"""
Configurações do Django para o projeto Worten API.
Documentação: https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent


# Chave secreta - em produção, usar variável de ambiente!
SECRET_KEY = "django-insecure-rzm6!^^y+68r2v7_kfo4h#=6(k#x3f%al5eendyxn-+24deds^"

# Modo debug - lembrar de desativar em produção
DEBUG = True

ALLOWED_HOSTS = []


# Apps instalados
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Bibliotecas de terceiros
    "rest_framework",
    "drf_yasg",
    # App do projeto
    "products",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Validadores de senha
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internacionalização
LANGUAGE_CODE = "pt-br"

TIME_ZONE = "America/Sao_Paulo"

USE_I18N = True

USE_TZ = True


# Arquivos estáticos
STATIC_URL = "static/"

# Tipo padrão de chave primária
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configurações do Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

# Configurações do Swagger
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {},
    "USE_SESSION_AUTH": False,
}

# Caminhos dos arquivos de dados
DATA_DIR = BASE_DIR / "data"
INPUT_SPREADSHEET = DATA_DIR / "input" / "worten.xlsx"
OUTPUT_SPREADSHEET = DATA_DIR / "output" / "produtos_worten.xlsx"
