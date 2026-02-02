"""
Configuração ASGI do projeto.

Expõe o servidor ASGI através da variável 'application'.

Mais informações sobre ASGI:
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
