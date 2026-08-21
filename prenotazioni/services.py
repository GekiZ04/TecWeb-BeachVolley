"""Operazioni sulle prenotazioni che coinvolgono più passaggi (calcolo prezzo,
assegnazione del gestore, notifiche). Le ho tenute qui e non dentro le view così le
posso richiamare anche dai comandi da terminale (es. seed_demo_data), e sono più
comode da testare da sole."""

from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from struttura.time_utils import si_sovrappongono

from .models import ListaAttesa, Notifica, Prenotazione
from .pricing import calcola_prezzo


def assegna_gestore():
    """Sceglie il gestore con meno prenotazioni attive, così il carico si distribuisce da
    solo tra tutti i gestori. A parità di prenotazioni vince l'id più basso — giusto per
    avere un risultato prevedibile e non un po' a caso."""
    from accounts.models import User

    gestori = User.objects.filter(role=User.Ruolo.GESTORE).annotate(
        n_prenotazioni=Count(
            'prenotazioni_gestite',
            filter=Q(prenotazioni_gestite__stato=Prenotazione.Stato.CONFERMATA),
        )
    ).order_by('n_prenotazioni', 'id')
    return gestori.first()


def slot_occupato(data, ora_inizio, ora_fine, escludi_id=None):
    """Vero se esiste già una prenotazione confermata esattamente su questo slot (stessa
    ora di inizio e fine — non rileva sovrapposizioni parziali come fa invece
    struttura.services.intervallo_disponibile). Uso questa versione "semplice" solo in
    seed_demo_data, per non ricreare due volte la stessa prenotazione demo se il comando
    viene rilanciato."""
    qs = Prenotazione.objects.filter(
        data=data, ora_inizio=ora_inizio, ora_fine=ora_fine, stato=Prenotazione.Stato.CONFERMATA,
    )
    if escludi_id:
        qs = qs.exclude(id=escludi_id)
    return qs.exists()


def crea_prenotazione(utente, data, ora_inizio, ora_fine, spogliatoio, numero_partecipanti):
    """Crea una nuova prenotazione: calcola e "congela" il prezzo secondo il prezzario
    attuale e assegna automaticamente un gestore."""
    from struttura.models import Tariffa

    tariffa = Tariffa.get_attuale()
    prezzo = calcola_prezzo(ora_inizio, ora_fine, spogliatoio, numero_partecipanti, tariffa)
    gestore = assegna_gestore()
    return Prenotazione.objects.create(
        utente=utente, gestore=gestore, data=data, ora_inizio=ora_inizio, ora_fine=ora_fine,
        spogliatoio=spogliatoio, numero_partecipanti=numero_partecipanti, prezzo_listino=prezzo,
    )


def modifica_prenotazione(prenotazione, data, ora_inizio, ora_fine, spogliatoio, numero_partecipanti):
    """Aggiorna una prenotazione esistente e ricalcola il prezzo in base ai nuovi dati.
    Se c'era uno sconto (prezzo_finale) impostato dall'admin, lo azzero: essendo cambiati
    orario o partecipanti, andrebbe comunque rivalutato da capo, meglio non lasciarlo lì
    per sbaglio."""
    from struttura.models import Tariffa

    tariffa = Tariffa.get_attuale()
    prenotazione.data = data
    prenotazione.ora_inizio = ora_inizio
    prenotazione.ora_fine = ora_fine
    prenotazione.spogliatoio = spogliatoio
    prenotazione.numero_partecipanti = numero_partecipanti
    prenotazione.prezzo_listino = calcola_prezzo(ora_inizio, ora_fine, spogliatoio, numero_partecipanti, tariffa)
    prenotazione.prezzo_finale = None
    prenotazione.save()
    return prenotazione


def notifica_lista_attesa(data, ora_inizio, ora_fine):
    """Avvisa con una Notifica chi era in lista d'attesa per uno slot appena liberato, poi
    lo toglie dalla coda — da lì in poi deve prenotare come chiunque altro, non c'è una
    prenotazione automatica, vince chi conferma per primo."""
    # Confronto per sovrapposizione e non per corrispondenza esatta, perché la prenotazione
    # cancellata può avere una durata diversa da quella che ogni utente in coda si aspettava.
    # Lo faccio in Python invece che con una query perché un 00:00 va letto come mezzanotte
    # di fine giornata, e confrontando i TimeField direttamente nel database questo non
    # verrebbe gestito bene.
    attese = [
        a for a in ListaAttesa.objects.filter(data=data)
        if si_sovrappongono(a.ora_inizio, a.ora_fine, ora_inizio, ora_fine)
    ]
    messaggio = (
        f'Si è liberato lo slot del {data.strftime("%d/%m/%Y")} '
        f'{ora_inizio.strftime("%H:%M")}-{ora_fine.strftime("%H:%M")}: prenota ora!'
    )
    for attesa in attese:
        Notifica.objects.create(utente=attesa.utente, messaggio=messaggio, link=reverse('prenotazioni:nuova'))
    ListaAttesa.objects.filter(pk__in=[a.pk for a in attese]).delete()


def cancella_prenotazione(prenotazione):
    """Cancella una prenotazione — senza eliminarla dal database, così ne resta lo storico
    — e libera lo slot avvisando chi era in lista d'attesa."""
    prenotazione.stato = Prenotazione.Stato.CANCELLATA
    prenotazione.cancellata_il = timezone.now()
    prenotazione.save()
    notifica_lista_attesa(prenotazione.data, prenotazione.ora_inizio, prenotazione.ora_fine)
