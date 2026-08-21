# Configurazione di /django-admin/ per i modelli di questa app — mi è tornata utile
# soprattutto per correggere i dati a mano durante lo sviluppo.
from django.contrib import admin

from .models import ListaAttesa, Notifica, Prenotazione


@admin.register(Prenotazione)
class PrenotazioneAdmin(admin.ModelAdmin):
    list_display = ('utente', 'gestore', 'data', 'ora_inizio', 'ora_fine', 'stato', 'prezzo_listino', 'prezzo_finale')
    list_filter = ('stato', 'data', 'gestore')


@admin.register(ListaAttesa)
class ListaAttesaAdmin(admin.ModelAdmin):
    list_display = ('utente', 'data', 'ora_inizio', 'ora_fine')


@admin.register(Notifica)
class NotificaAdmin(admin.ModelAdmin):
    list_display = ('utente', 'messaggio', 'letta', 'creato_il')
    list_filter = ('letta',)
