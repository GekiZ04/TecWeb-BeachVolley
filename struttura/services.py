"""Qui c'è tutta la logica di "quando si può prenotare". L'ho tenuta separata dalle view
sia per poterla testare più facilmente, sia perché serve sia al form di prenotazione sia
alla pagina pubblica con il calendario."""

import datetime

from .models import ChiusuraStraordinaria, OrarioApertura
from .time_utils import minuti_dalla_mezzanotte, si_sovrappongono

SLOT_MINUTI = 15  # granularità delle prenotazioni: un quarto d'ora
DURATA_MINIMA_MINUTI = 15
DURATA_MASSIMA_MINUTI = 240  # 4 ore


def slot_disponibili(data, escludi_prenotazione_id=None):
    """Ritorna la lista di slot da 15 minuti per il giorno indicato, ognuno con il proprio
    stato (libero/occupato/chiuso). Uno slot è 'occupato' se si sovrappone a una
    prenotazione confermata; se la chiusura è alle 00:00 l'ultimo slot arriva a mezzanotte.
    escludi_prenotazione_id serve quando si sta modificando una prenotazione esistente, per
    non conteggiare come occupato lo slot che occupa lei stessa."""
    # Import fatto qui dentro e non in cima al file perché prenotazioni.models importa a
    # sua volta da struttura: mettendolo in cima si creerebbe un import circolare e Django
    # si pianterebbe all'avvio.
    from prenotazioni.models import Prenotazione

    orario = OrarioApertura.objects.filter(giorno_settimana=data.weekday()).first()
    if orario is None or not orario.aperto:
        return []

    chiusure = list(ChiusuraStraordinaria.objects.filter(data_inizio__lte=data, data_fine__gte=data))
    prenotazioni_occupate = Prenotazione.objects.filter(data=data, stato=Prenotazione.Stato.CONFERMATA)
    if escludi_prenotazione_id:
        prenotazioni_occupate = prenotazioni_occupate.exclude(id=escludi_prenotazione_id)
    prenotazioni_occupate = list(prenotazioni_occupate)

    slots = []
    inizio = datetime.datetime.combine(data, orario.ora_apertura)
    fine_apertura = datetime.datetime.combine(data, orario.ora_chiusura)
    if orario.ora_chiusura <= orario.ora_apertura:
        fine_apertura += datetime.timedelta(days=1)

    while inizio + datetime.timedelta(minutes=SLOT_MINUTI) <= fine_apertura:
        ora_inizio = inizio.time()
        ora_fine = (inizio + datetime.timedelta(minutes=SLOT_MINUTI)).time()

        if any(c.copre(data, ora_inizio, ora_fine) for c in chiusure):
            stato = 'chiuso'
        elif any(si_sovrappongono(p.ora_inizio, p.ora_fine, ora_inizio, ora_fine) for p in prenotazioni_occupate):
            stato = 'occupato'
        else:
            stato = 'libero'

        slots.append({'ora_inizio': ora_inizio, 'ora_fine': ora_fine, 'stato': stato})
        inizio += datetime.timedelta(minutes=SLOT_MINUTI)

    return slots


CALENDARIO_STEP_MINUTI = 60


def calendario_settimana(lunedi):
    """Costruisce la griglia settimanale mostrata in home (righe = ore, colonne = i 7 giorni
    a partire da `lunedi`) — è una vista d'insieme, la prenotazione vera resta comunque a
    quarti d'ora. Ogni cella ha uno stato base (libero/chiuso, per tutta l'ora) più una
    lista di "blocchi" occupati con posizione e altezza in percentuale: così una
    prenotazione di 15 minuti non colora l'intera ora ma solo il pezzo che occupa davvero,
    senza dover scrivere l'orario esatto sopra ogni cella."""
    from prenotazioni.models import Prenotazione

    giorni = [lunedi + datetime.timedelta(days=i) for i in range(7)]
    orari = {o.giorno_settimana: o for o in OrarioApertura.objects.all()}

    ora_min_min = ora_max_min = None
    for giorno in giorni:
        orario = orari.get(giorno.weekday())
        if orario and orario.aperto:
            apertura_min = minuti_dalla_mezzanotte(orario.ora_apertura)
            chiusura_min = minuti_dalla_mezzanotte(orario.ora_chiusura, fine_giornata=True)
            if ora_min_min is None or apertura_min < ora_min_min:
                ora_min_min = apertura_min
            if ora_max_min is None or chiusura_min > ora_max_min:
                ora_max_min = chiusura_min

    if ora_min_min is None:
        return {'giorni': giorni, 'righe': []}

    prenotazioni_per_giorno = {}
    for p in Prenotazione.objects.filter(
        data__gte=giorni[0], data__lte=giorni[-1], stato=Prenotazione.Stato.CONFERMATA,
    ):
        prenotazioni_per_giorno.setdefault(p.data, []).append(p)

    chiusure = list(ChiusuraStraordinaria.objects.filter(data_inizio__lte=giorni[-1], data_fine__gte=giorni[0]))

    righe = []
    mezzanotte = datetime.datetime.combine(datetime.date.today(), datetime.time(0, 0))
    inizio = mezzanotte + datetime.timedelta(minutes=ora_min_min)
    fine = mezzanotte + datetime.timedelta(minutes=ora_max_min)
    while inizio + datetime.timedelta(minutes=CALENDARIO_STEP_MINUTI) <= fine:
        ora_inizio = inizio.time()
        ora_fine = (inizio + datetime.timedelta(minutes=CALENDARIO_STEP_MINUTI)).time()
        riga_inizio_min = minuti_dalla_mezzanotte(ora_inizio)
        riga_fine_min = minuti_dalla_mezzanotte(ora_fine, fine_giornata=True)

        celle = []
        for giorno in giorni:
            orario = orari.get(giorno.weekday())
            if not orario or not orario.aperto:
                celle.append({'stato': 'chiuso', 'blocchi': [], 'data': giorno})
                continue
            apertura_min = minuti_dalla_mezzanotte(orario.ora_apertura)
            chiusura_min = minuti_dalla_mezzanotte(orario.ora_chiusura, fine_giornata=True)
            if riga_inizio_min < apertura_min or riga_fine_min > chiusura_min:
                celle.append({'stato': 'chiuso', 'blocchi': [], 'data': giorno})
                continue
            if any(c.copre(giorno, ora_inizio, ora_fine) for c in chiusure):
                celle.append({'stato': 'chiuso', 'blocchi': [], 'data': giorno})
                continue

            blocchi = []
            for p in prenotazioni_per_giorno.get(giorno, []):
                p_inizio_min = minuti_dalla_mezzanotte(p.ora_inizio)
                p_fine_min = minuti_dalla_mezzanotte(p.ora_fine, fine_giornata=True)
                if p_inizio_min < riga_fine_min and riga_inizio_min < p_fine_min:
                    seg_inizio_min = max(p_inizio_min, riga_inizio_min)
                    seg_fine_min = min(p_fine_min, riga_fine_min)
                    blocchi.append({
                        'top': round((seg_inizio_min - riga_inizio_min) / CALENDARIO_STEP_MINUTI * 100, 2),
                        'altezza': round((seg_fine_min - seg_inizio_min) / CALENDARIO_STEP_MINUTI * 100, 2),
                    })

            celle.append({'stato': 'occupato' if blocchi else 'libero', 'blocchi': blocchi, 'data': giorno})

        righe.append({'ora_inizio': ora_inizio, 'ora_fine': ora_fine, 'celle': celle})
        inizio += datetime.timedelta(minutes=CALENDARIO_STEP_MINUTI)

    return {'giorni': giorni, 'righe': righe}


def intervallo_disponibile(data, ora_inizio, ora_fine, escludi_prenotazione_id=None):
    """Controlla che l'intervallo [ora_inizio, ora_fine] sia prenotabile per intero in quella
    data: campo aperto, dentro l'orario di apertura, nessuna chiusura straordinaria e
    nessuna sovrapposizione con altre prenotazioni confermate. ora_fine può valere 00:00
    per una prenotazione che finisce a mezzanotte."""
    from prenotazioni.models import Prenotazione

    orario = OrarioApertura.objects.filter(giorno_settimana=data.weekday()).first()
    if orario is None or not orario.aperto:
        return False

    inizio_min = minuti_dalla_mezzanotte(ora_inizio)
    fine_min = minuti_dalla_mezzanotte(ora_fine, fine_giornata=True)
    apertura_min = minuti_dalla_mezzanotte(orario.ora_apertura)
    chiusura_min = minuti_dalla_mezzanotte(orario.ora_chiusura, fine_giornata=True)
    if inizio_min < apertura_min or fine_min > chiusura_min:
        return False

    chiusure = ChiusuraStraordinaria.objects.filter(data_inizio__lte=data, data_fine__gte=data)
    if any(c.copre(data, ora_inizio, ora_fine) for c in chiusure):
        return False

    prenotazioni = Prenotazione.objects.filter(data=data, stato=Prenotazione.Stato.CONFERMATA)
    if escludi_prenotazione_id:
        prenotazioni = prenotazioni.exclude(id=escludi_prenotazione_id)
    if any(si_sovrappongono(p.ora_inizio, p.ora_fine, ora_inizio, ora_fine) for p in prenotazioni):
        return False

    return True
