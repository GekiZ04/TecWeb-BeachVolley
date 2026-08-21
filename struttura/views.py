"""View pubbliche (home, disponibilità) e view dell'area gestore (orari, prezzario,
chiusure straordinarie, servizi)."""

import datetime

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.permissions import gestore_or_admin_required

from .forms import ChiusuraStraordinariaForm, OrarioAperturaFormSet, ServizioForm, TariffaForm
from .models import Campo, ChiusuraStraordinaria, OrarioApertura, Servizio, Tariffa
from .services import calendario_settimana, slot_disponibili


def _parse_lunedi(request):
    """Legge il parametro GET "inizio" e ritorna il lunedì della settimana a cui appartiene
    quella data (senza parametro, o con uno non valido, usa la settimana corrente). Serve
    per i link "settimana precedente/successiva" del calendario in home."""
    valore = request.GET.get('inizio')
    if valore:
        try:
            data = datetime.date.fromisoformat(valore)
        except ValueError:
            data = timezone.localdate()
    else:
        data = timezone.localdate()
    return data - datetime.timedelta(days=data.weekday())


def _assicura_orari_default():
    """Crea le righe OrarioApertura mancanti (una per giorno della settimana), così il
    sito non si rompe anche se non è mai stato lanciato seed_demo_data."""
    if OrarioApertura.objects.count() < 7:
        esistenti = set(OrarioApertura.objects.values_list('giorno_settimana', flat=True))
        for giorno, _ in OrarioApertura.Giorno.choices:
            if giorno not in esistenti:
                OrarioApertura.objects.create(giorno_settimana=giorno)


def home(request):
    """Pagina pubblica: presentazione della struttura, servizi, orari, prezzario e il
    calendario settimanale (cliccabile solo per chi può prenotare)."""
    _assicura_orari_default()
    lunedi = _parse_lunedi(request)
    return render(request, 'struttura/home.html', {
        'campo': Campo.objects.first(),
        'servizi': Servizio.objects.filter(disponibile=True),
        'orari': OrarioApertura.objects.all(),
        'tariffa': Tariffa.get_attuale(),
        'lunedi': lunedi,
        'calendario': calendario_settimana(lunedi),
        'settimana_prec': lunedi - datetime.timedelta(days=7),
        'settimana_succ': lunedi + datetime.timedelta(days=7),
        # un gestore/admin che guarda il calendario non deve poter cliccare gli slot —
        # solo un cliente (o un visitatore non loggato, che finirà comunque al login) può farlo
        'puo_prenotare': not request.user.is_authenticated or request.user.is_cliente,
        'oggi': timezone.localdate(),
    })


def disponibilita_json(request):
    """Endpoint AJAX chiamato da static/js/disponibilita.js: ritorna in JSON gli slot
    disponibili per una data. Il parametro "escludi" serve alla pagina di modifica, per
    mostrare come libero lo slot della prenotazione che si sta modificando — ma solo se è
    dell'utente che sta facendo la richiesta, altrimenti basterebbe conoscere l'id per far
    apparire libera una prenotazione altrui."""
    valore = request.GET.get('data')
    try:
        data = datetime.date.fromisoformat(valore)
    except (TypeError, ValueError):
        return JsonResponse({'errore': 'data non valida'}, status=400)

    escludi_id = None
    escludi_param = request.GET.get('escludi')
    if escludi_param and request.user.is_authenticated:
        from prenotazioni.models import Prenotazione
        escludi_id = Prenotazione.objects.filter(pk=escludi_param, utente=request.user).values_list('pk', flat=True).first()

    slots = slot_disponibili(data, escludi_prenotazione_id=escludi_id)
    return JsonResponse({
        'data': data.isoformat(),
        'aperto': bool(slots),
        'slots': [
            {'ora_inizio': s['ora_inizio'].strftime('%H:%M'), 'ora_fine': s['ora_fine'].strftime('%H:%M'), 'stato': s['stato']}
            for s in slots
        ],
    })


@gestore_or_admin_required
def dashboard(request):
    """Area gestore/admin: modulo orari, prezzario, chiusure straordinarie, servizi, più
    l'elenco delle prenotazioni delle prossime settimane. L'admin vede tutte le
    prenotazioni, un gestore solo quelle assegnate a lui."""
    _assicura_orari_default()
    from prenotazioni.models import Prenotazione

    if request.user.is_admin_struttura:
        prenotazioni = Prenotazione.objects.filter(
            stato=Prenotazione.Stato.CONFERMATA, data__gte=timezone.localdate(),
        ).select_related('utente', 'gestore')[:30]
    else:
        prenotazioni = Prenotazione.objects.filter(
            gestore=request.user, stato=Prenotazione.Stato.CONFERMATA, data__gte=timezone.localdate(),
        ).select_related('utente')[:30]

    return render(request, 'struttura/dashboard.html', {
        'orario_formset': OrarioAperturaFormSet(queryset=OrarioApertura.objects.all()),
        'tariffa_form': TariffaForm(instance=Tariffa.get_attuale()),
        'chiusura_form': ChiusuraStraordinariaForm(),
        'servizio_form': ServizioForm(),
        'chiusure': ChiusuraStraordinaria.objects.all(),
        'servizi': Servizio.objects.all(),
        'prenotazioni': prenotazioni,
    })


# Le sei view qui sotto gestiscono i form della dashboard (orari, prezzario, chiusure,
# servizi). Avrei potuto accorparle in una view generica "salva_form", ma con 4 modelli
# diversi e messaggi diversi per ognuno mi sembrava finisse per essere più complicata da
# leggere che tenerle separate, quindi ho preferito la ripetizione a un'astrazione in più.

@gestore_or_admin_required
def salva_orari(request):
    """Salva gli orari di apertura modificati (un formset, una riga per giorno)."""
    if request.method == 'POST':
        formset = OrarioAperturaFormSet(request.POST, queryset=OrarioApertura.objects.all())
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Orari di apertura aggiornati.')
        else:
            messages.error(request, 'Controlla i dati inseriti negli orari.')
    return redirect('struttura:dashboard')


@gestore_or_admin_required
def salva_tariffa(request):
    """Aggiorna il prezzario in vigore — vale solo per le prenotazioni future."""
    if request.method == 'POST':
        form = TariffaForm(request.POST, instance=Tariffa.get_attuale())
        if form.is_valid():
            form.save()
            messages.success(request, 'Prezzario aggiornato: sarà applicato alle nuove prenotazioni.')
        else:
            messages.error(request, 'Controlla i valori del prezzario.')
    return redirect('struttura:dashboard')


@gestore_or_admin_required
def nuova_chiusura(request):
    """Crea una chiusura straordinaria, salvando anche quale gestore l'ha inserita."""
    if request.method == 'POST':
        form = ChiusuraStraordinariaForm(request.POST)
        if form.is_valid():
            chiusura = form.save(commit=False)
            chiusura.creato_da = request.user
            chiusura.save()
            messages.success(request, 'Chiusura straordinaria aggiunta.')
        else:
            messages.error(request, 'Controlla i dati della chiusura.')
    return redirect('struttura:dashboard')


@gestore_or_admin_required
def elimina_chiusura(request, pk):
    chiusura = get_object_or_404(ChiusuraStraordinaria, pk=pk)
    if request.method == 'POST':
        chiusura.delete()
        messages.success(request, 'Chiusura rimossa.')
    return redirect('struttura:dashboard')


@gestore_or_admin_required
def nuovo_servizio(request):
    if request.method == 'POST':
        form = ServizioForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Servizio aggiunto.')
        else:
            messages.error(request, 'Controlla i dati del servizio.')
    return redirect('struttura:dashboard')


@gestore_or_admin_required
def elimina_servizio(request, pk):
    servizio = get_object_or_404(Servizio, pk=pk)
    if request.method == 'POST':
        servizio.delete()
        messages.success(request, 'Servizio rimosso.')
    return redirect('struttura:dashboard')
