from django.urls import path

from . import views

# namespace 'struttura': serve a scrivere {% url 'struttura:dashboard' %} nei template
app_name = 'struttura'

urlpatterns = [
    path('disponibilita/', views.disponibilita_json, name='disponibilita_json'),
    path('gestore/', views.dashboard, name='dashboard'),
    path('gestore/orari/', views.salva_orari, name='salva_orari'),
    path('gestore/tariffa/', views.salva_tariffa, name='salva_tariffa'),
    path('gestore/chiusure/nuova/', views.nuova_chiusura, name='nuova_chiusura'),
    path('gestore/chiusure/<int:pk>/elimina/', views.elimina_chiusura, name='elimina_chiusura'),
    path('gestore/servizi/nuovo/', views.nuovo_servizio, name='nuovo_servizio'),
    path('gestore/servizi/<int:pk>/elimina/', views.elimina_servizio, name='elimina_servizio'),
]
