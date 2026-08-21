"""URL principali del progetto: smista le richieste alle tre app (accounts, struttura,
prenotazioni), ognuna col proprio file urls.py e il proprio namespace."""

from django.contrib import admin
from django.urls import include, path

from struttura.views import home

urlpatterns = [
    # 'django-admin/' invece del solito 'admin/', per non confonderlo con l'area
    # gestore/admin della struttura che vive sotto struttura/gestore/
    path('django-admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('struttura/', include('struttura.urls')),
    path('prenotazioni/', include('prenotazioni.urls')),
    path('', home, name='home'),  # home page pubblica, alla radice del sito
]
