from django.urls import path

from . import views

# namespace 'prenotazioni': negli altri file si usa {% url 'prenotazioni:mie' %}
app_name = 'prenotazioni'

urlpatterns = [
    path('nuova/', views.nuova_prenotazione, name='nuova'),
    path('prezzo/', views.anteprima_prezzo, name='prezzo'),
    path('lista-attesa/', views.iscrivi_lista_attesa, name='lista_attesa'),
    path('mie/', views.mie_prenotazioni, name='mie'),
    path('<int:pk>/modifica/', views.modifica_prenotazione, name='modifica'),
    path('<int:pk>/cancella/', views.cancella_prenotazione, name='cancella'),
    path('notifiche/', views.notifiche, name='notifiche'),
    path('economia/', views.economia, name='economia'),
    path('economia/<int:pk>/sconto/', views.applica_sconto, name='applica_sconto'),
    path('economia/<int:pk>/gestore/', views.riassegna_gestore, name='riassegna_gestore'),
]
