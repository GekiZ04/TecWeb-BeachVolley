"""Le view del flusso di prenotazione (creazione, modifica, cancellazione, storico),
lista d'attesa, notifiche, e quelle riservate all'admin per l'economia della struttura."""

import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from accounts.permissions import admin_required, cliente_required
from struttura.models import Tariffa
from struttura.services import intervallo_disponibile
from struttura.time_utils import minuti_dalla_mezzanotte

from . import services
from .forms import ListaAttesaForm, PrenotazioneForm
from .models import PARTECIPANTI_MASSIMO, ListaAttesa, Notifica, Prenotazione
from .pricing import calcola_prezzo


def _parse_data(request):
    """Legge il parametro GET "data"; se manca o non è valido usa la data di oggi."""
    valore = request.GET.get('data')
    if valore:
        try:
            return datetime.date.fromisoformat(valore)
        except ValueError:
            pass
    return timezone.localdate()


@cliente_required
def nuova_prenotazione(request):
    """Pagina di prenotazione. La scelta di data/orario/durata la fa il JavaScript (fetch
    verso struttura:disponibilita_json e prenotazioni:prezzo); qui mi limito a renderizzare
    la pagina iniziale (GET) e a gestire la creazione vera e propria (POST)."""
    if request.method == 'POST':
        form = PrenotazioneForm(request.POST)
        data_redirect = request.POST.get('data', '')
        if form.is_valid():
            cd = form.cleaned_data
            # ricontrollo la disponibilità anche lato server: i dati arrivano dal browser
            # e nel frattempo potrebbe essere cambiato qualcosa (es. un altro utente ha
            # prenotato proprio quello slot), quindi il solo JavaScript non basta a fidarsi
            disponibile = intervallo_disponibile(cd['data'], cd['ora_inizio'], cd['ora_fine'])
            if cd['data'] < timezone.localdate():
                messages.error(request, 'Non puoi prenotare una data passata.')
            elif not disponibile:
                messages.error(request, 'Lo slot scelto non è più disponibile. Puoi metterti in lista d\'attesa.')
            else:
                services.crea_prenotazione(
                    utente=request.user, data=cd['data'], ora_inizio=cd['ora_inizio'],
                    ora_fine=cd['ora_fine'], spogliatoio=cd['spogliatoio'],
                    numero_partecipanti=cd['numero_partecipanti'],
                )
                messages.success(request, 'Prenotazione effettuata con successo.')
                return redirect('prenotazioni:mie')
        else:
            messages.error(request, 'Dati non validi, riprova.')
        return redirect(f"{request.path}?data={data_redirect}")

    data = _parse_data(request)

    # Se si arriva qui da un click su uno slot libero nel calendario della home, l'orario
    # è già nella URL: lo passo al template così il JS preseleziona subito quello slot
    # invece di lasciare il menù vuoto. Se manca o non è un orario valido, pace, si parte
    # senza preselezione.
    ora_richiesta = None
    valore_ora = request.GET.get('ora', '')
    try:
        ora_richiesta = datetime.time.fromisoformat(valore_ora)
    except ValueError:
        pass

    return render(request, 'prenotazioni/nuova.html', {'data': data, 'ora_richiesta': ora_richiesta})


@cliente_required
def anteprima_prezzo(request):
    """Endpoint AJAX che calcola il prezzo di una possibile prenotazione senza crearla
    davvero, per aggiornarlo in tempo reale mentre l'utente cambia orario/durata/
    spogliatoio/partecipanti nel form."""
    try:
        ora_inizio = datetime.time.fromisoformat(request.GET.get('ora_inizio', ''))
        ora_fine = datetime.time.fromisoformat(request.GET.get('ora_fine', ''))
        spogliatoio = request.GET.get('spogliatoio') == 'true'
        partecipanti = int(request.GET.get('partecipanti', 1))
    except (ValueError, TypeError):
        return JsonResponse({'errore': 'parametri non validi'}, status=400)
    if minuti_dalla_mezzanotte(ora_fine, fine_giornata=True) <= minuti_dalla_mezzanotte(ora_inizio):
        return JsonResponse({'errore': 'intervallo non valido'}, status=400)
    if not 1 <= partecipanti <= PARTECIPANTI_MASSIMO:
        return JsonResponse({'errore': 'numero di partecipanti non valido'}, status=400)
    tariffa = Tariffa.get_attuale()
    prezzo = calcola_prezzo(ora_inizio, ora_fine, spogliatoio, partecipanti, tariffa)
    return JsonResponse({'prezzo': str(prezzo)})


@cliente_required
def iscrivi_lista_attesa(request):
    """Iscrive l'utente alla lista d'attesa per lo slot indicato. Uso get_or_create così
    se clicca due volte per sbaglio non finisce iscritto due volte allo stesso slot."""
    if request.method == 'POST':
        form = ListaAttesaForm(request.POST)
        data_redirect = request.POST.get('data', '')
        if form.is_valid():
            cd = form.cleaned_data
            _, creato = ListaAttesa.objects.get_or_create(
                utente=request.user, data=cd['data'], ora_inizio=cd['ora_inizio'], ora_fine=cd['ora_fine'],
            )
            if creato:
                messages.success(request, 'Ti abbiamo iscritto alla lista d\'attesa per questo slot.')
            else:
                messages.info(request, 'Sei già in lista d\'attesa per questo slot.')
        return redirect(f"{reverse('prenotazioni:nuova')}?data={data_redirect}")
    return redirect('prenotazioni:nuova')


@login_required
def mie_prenotazioni(request):
    """Storico personale: separa le prenotazioni future e confermate ("prossime") dal
    resto, passate o cancellate, che finisce nello "storico"."""
    oggi = timezone.localdate()
    qs = Prenotazione.objects.filter(utente=request.user)
    prossime = [p for p in qs if p.stato == Prenotazione.Stato.CONFERMATA and p.data >= oggi]
    storico = [p for p in qs if p not in prossime]
    return render(request, 'prenotazioni/mie.html', {'prossime': prossime, 'storico': storico, 'oggi': oggi})


@cliente_required
def modifica_prenotazione(request, pk):
    """Modifica di una prenotazione esistente. Il filtro utente=request.user dentro
    get_object_or_404 fa sì che un cliente possa modificare solo le proprie: se prova
    l'id di una prenotazione altrui prende un 404 come se non esistesse, non un errore
    di permesso, così non capisce nemmeno che quell'id è valido."""
    prenotazione = get_object_or_404(Prenotazione, pk=pk, utente=request.user)
    oggi = timezone.localdate()
    if prenotazione.stato != Prenotazione.Stato.CONFERMATA or prenotazione.data < oggi:
        messages.error(request, 'Questa prenotazione non può più essere modificata.')
        return redirect('prenotazioni:mie')

    if request.method == 'POST':
        form = PrenotazioneForm(request.POST)
        data_redirect = request.POST.get('data', '')
        if form.is_valid():
            cd = form.cleaned_data
            # senza escludi_prenotazione_id, lo slot che occupa già questa prenotazione
            # risulterebbe "occupato" da sé stessa, e non si potrebbe mai risalvare senza
            # cambiare almeno un minuto di orario
            disponibile = intervallo_disponibile(
                cd['data'], cd['ora_inizio'], cd['ora_fine'], escludi_prenotazione_id=prenotazione.id,
            )
            if cd['data'] < oggi:
                messages.error(request, 'Non puoi spostare la prenotazione a una data passata.')
            elif not disponibile:
                messages.error(request, 'Lo slot scelto non è disponibile.')
            else:
                services.modifica_prenotazione(
                    prenotazione, data=cd['data'], ora_inizio=cd['ora_inizio'], ora_fine=cd['ora_fine'],
                    spogliatoio=cd['spogliatoio'], numero_partecipanti=cd['numero_partecipanti'],
                )
                messages.success(request, 'Prenotazione aggiornata.')
                return redirect('prenotazioni:mie')
        return redirect(f"{request.path}?data={data_redirect}")

    # senza data in query string parto dalla data della prenotazione stessa e non da
    # "oggi": ha senso vedere subito il proprio slot invece della settimana corrente
    data = datetime.date.fromisoformat(request.GET['data']) if 'data' in request.GET else prenotazione.data
    return render(request, 'prenotazioni/modifica.html', {'prenotazione': prenotazione, 'data': data})


@cliente_required
def cancella_prenotazione(request, pk):
    prenotazione = get_object_or_404(Prenotazione, pk=pk, utente=request.user)
    oggi = timezone.localdate()
    if request.method == 'POST':
        if prenotazione.stato == Prenotazione.Stato.CONFERMATA and prenotazione.data >= oggi:
            services.cancella_prenotazione(prenotazione)
            messages.success(request, 'Prenotazione cancellata.')
        else:
            messages.error(request, 'Questa prenotazione non può più essere cancellata.')
    return redirect('prenotazioni:mie')


@login_required
def notifiche(request):
    """Elenco delle notifiche. Appena si apre la pagina, tutte quelle non lette vengono
    segnate come lette, così il contatore in navbar torna a zero."""
    lista = list(Notifica.objects.filter(utente=request.user))
    Notifica.objects.filter(utente=request.user, letta=False).update(letta=True)
    return render(request, 'prenotazioni/notifiche.html', {'notifiche': lista})


@admin_required
def economia(request):
    """Resoconto economico settimanale, solo per l'admin: incassato e quota (40%/60%)
    per ciascun gestore, più il dettaglio di ogni singola prenotazione."""
    oggi = timezone.localdate()
    inizio_param = request.GET.get('inizio')
    if inizio_param:
        try:
            inizio = datetime.date.fromisoformat(inizio_param)
        except ValueError:
            inizio = oggi
    else:
        inizio = oggi
    # sposto sempre indietro al lunedì della settimana scelta, così i link "settimana
    # precedente/successiva" restano coerenti qualunque giorno passi il parametro
    inizio = inizio - datetime.timedelta(days=inizio.weekday())
    fine = inizio + datetime.timedelta(days=6)

    prenotazioni = Prenotazione.objects.filter(
        data__gte=inizio, data__lte=fine, stato=Prenotazione.Stato.CONFERMATA,
    ).select_related('utente', 'gestore')

    per_gestore = {}
    totale_incassato = Decimal('0')
    totale_admin = Decimal('0')
    for p in prenotazioni:
        nome = str(p.gestore) if p.gestore else 'Non assegnato'
        riga = per_gestore.setdefault(nome, {'incassato': Decimal('0'), 'quota_gestore': Decimal('0'), 'quota_admin': Decimal('0')})
        riga['incassato'] += p.importo_dovuto
        riga['quota_gestore'] += p.quota_gestore
        riga['quota_admin'] += p.quota_admin
        totale_incassato += p.importo_dovuto
        totale_admin += p.quota_admin

    return render(request, 'prenotazioni/economia.html', {
        'inizio': inizio, 'fine': fine, 'prenotazioni': prenotazioni,
        'per_gestore': per_gestore, 'totale_incassato': totale_incassato,
        'totale_admin': totale_admin, 'totale_gestori': totale_incassato - totale_admin,
        'settimana_prec': inizio - datetime.timedelta(days=7),
        'settimana_succ': inizio + datetime.timedelta(days=7),
        'gestori': User.objects.filter(role=User.Ruolo.GESTORE).order_by('username'),
    })


@admin_required
def riassegna_gestore(request, pk):
    """Permette all'admin di cambiare a mano il gestore di una prenotazione, in aggiunta
    all'assegnazione automatica che avviene alla creazione."""
    prenotazione = get_object_or_404(Prenotazione, pk=pk)
    if request.method == 'POST':
        gestore_id = request.POST.get('gestore_id', '').strip()
        if not gestore_id:
            prenotazione.gestore = None
            prenotazione.save()
            messages.success(request, 'Gestore rimosso dalla prenotazione.')
        else:
            gestore = User.objects.filter(pk=gestore_id, role=User.Ruolo.GESTORE).first()
            if gestore is None:
                messages.error(request, 'Gestore non valido.')
            else:
                prenotazione.gestore = gestore
                prenotazione.save()
                messages.success(request, f'Prenotazione assegnata a {gestore}.')
    # riporto alla stessa settimana da cui si era partiti, non sempre a quella corrente
    settimana = request.POST.get('inizio', '')
    url = reverse('prenotazioni:economia')
    return redirect(f'{url}?inizio={settimana}' if settimana else url)


@admin_required
def applica_sconto(request, pk):
    """Permette all'admin di applicare uno sconto a una prenotazione, cambiando il prezzo
    finale. Resta visibile solo al cliente coinvolto (vedi Prenotazione.importo_dovuto)
    e all'admin, nessun altro lo vede."""
    prenotazione = get_object_or_404(Prenotazione, pk=pk)
    if request.method == 'POST':
        valore = request.POST.get('prezzo_finale', '').strip()
        if valore == '':
            prenotazione.prezzo_finale = None
            prenotazione.save()
            messages.success(request, 'Sconto rimosso.')
        else:
            try:
                nuovo_prezzo = Decimal(valore)
                if nuovo_prezzo < 0:
                    raise InvalidOperation
                prenotazione.prezzo_finale = nuovo_prezzo
                prenotazione.save()
                messages.success(request, 'Sconto applicato.')
            except InvalidOperation:
                messages.error(request, 'Importo non valido.')
        return redirect('prenotazioni:economia')
    return render(request, 'prenotazioni/applica_sconto.html', {'prenotazione': prenotazione})
