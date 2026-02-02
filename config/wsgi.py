"""
Configuração WSGI do projeto.

Expõe o servidor WSGI através da variável 'application'.

Mais informações sobre WSGI:
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
