"""Un paio di funzioni per confrontare/sottrarre orari (datetime.time) senza dover passare
per datetime completi. Servono soprattutto a gestire bene il caso limite della mezzanotte,
visto che datetime.time non può rappresentare le "24:00"."""


def minuti_dalla_mezzanotte(ora, fine_giornata=False):
    """Converte un datetime.time in minuti dalla mezzanotte.

    Se fine_giornata=True e l'orario è esattamente 00:00, lo tratto come fine giornata
    (24:00) e non come inizio giornata. Mi serve per rappresentare con un normale
    TimeField (che 24:00 non lo sa contenere) un orario di chiusura o una prenotazione
    che arrivano fino a mezzanotte."""
    minuti = ora.hour * 60 + ora.minute
    if fine_giornata and minuti == 0:
        return 24 * 60
    return minuti


def si_sovrappongono(inizio_a, fine_a, inizio_b, fine_b):
    """True se i due intervalli [inizio_a, fine_a) e [inizio_b, fine_b), dello stesso
    giorno, si sovrappongono — gestendo il caso in cui una delle due "fine" sia in realtà
    la mezzanotte (00:00 = fine giornata, non inizio)."""
    a_inizio = minuti_dalla_mezzanotte(inizio_a)
    a_fine = minuti_dalla_mezzanotte(fine_a, fine_giornata=True)
    b_inizio = minuti_dalla_mezzanotte(inizio_b)
    b_fine = minuti_dalla_mezzanotte(fine_b, fine_giornata=True)
    return a_inizio < b_fine and b_inizio < a_fine
