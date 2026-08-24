"""
Configurazione WSGI del progetto: espone il callable ``application`` che gestisce ogni
richiesta HTTP. Nonostante il nome sia legato al deploy, serve anche in locale: quando
lanci `manage.py runserver`, Django costruisce il suo server di sviluppo proprio a partire
da qui, leggendo WSGI_APPLICATION da settings.py.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'beachvolley.settings')

application = get_wsgi_application()
