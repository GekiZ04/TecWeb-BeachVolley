"""Il calcolo del prezzo di una prenotazione, secondo le regole del prezzario descritte
nella proposta di progetto: fascia diurna/serale, supplemento spogliatoio, sovrapprezzo
oltre una certa soglia di partecipanti."""

from decimal import Decimal

from struttura.time_utils import minuti_dalla_mezzanotte

FASCIA_SERALE_DA_MINUTI = 18 * 60  # le 18:00, espresse in minuti dalla mezzanotte


def calcola_prezzo(ora_inizio, ora_fine, spogliatoio, numero_partecipanti, tariffa):
    """Calcola il costo di una prenotazione di durata qualsiasi (multipla di 15 minuti).
    Se l'intervallo attraversa le 18:00, il costo si divide proporzionalmente tra fascia
    diurna e serale. ora_fine può valere 00:00 per una prenotazione che arriva a mezzanotte."""
    inizio_min = minuti_dalla_mezzanotte(ora_inizio)
    fine_min = minuti_dalla_mezzanotte(ora_fine, fine_giornata=True)
    minuti_totali = fine_min - inizio_min

    if fine_min <= FASCIA_SERALE_DA_MINUTI:
        # la prenotazione finisce prima delle 18:00: tutta in fascia diurna
        minuti_diurni, minuti_serali = minuti_totali, 0
    elif inizio_min >= FASCIA_SERALE_DA_MINUTI:
        # inizia dalle 18:00 in poi: tutta in fascia serale
        minuti_diurni, minuti_serali = 0, minuti_totali
    else:
        # attraversa le 18:00: si spezza il costo in proporzione ai minuti di ciascuna fascia
        minuti_diurni = FASCIA_SERALE_DA_MINUTI - inizio_min
        minuti_serali = minuti_totali - minuti_diurni

    tariffa_diurna = tariffa.prezzo_diurno_spogliatoio if spogliatoio else tariffa.prezzo_diurno_no_spogliatoio
    tariffa_serale = tariffa.prezzo_serale_spogliatoio if spogliatoio else tariffa.prezzo_serale_no_spogliatoio

    prezzo = (Decimal(minuti_diurni) / 60) * tariffa_diurna + (Decimal(minuti_serali) / 60) * tariffa_serale

    extra_persone = max(0, numero_partecipanti - tariffa.soglia_partecipanti)
    prezzo += Decimal(extra_persone) * tariffa.sovrapprezzo_persona_extra

    return prezzo.quantize(Decimal('0.01'))
