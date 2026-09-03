from django.db import models

from .time_utils import si_sovrappongono


class Campo(models.Model):
    """Il campo da beach volley. L'ho fatto come tabella (e non con valori fissi nel
    codice) così nome e descrizione si possono cambiare dall'admin senza toccare niente,
    anche se di fatto esiste un solo record."""
    nome = models.CharField(max_length=100, default='Campo da Beach Volley')
    descrizione = models.TextField(blank=True)

    def __str__(self):
        return self.nome


class Servizio(models.Model):
    """Un servizio della struttura (spogliatoio, parcheggio...) mostrato in home page.
    "disponibile" serve a nasconderlo temporaneamente senza doverlo cancellare del tutto."""
    nome = models.CharField(max_length=100)
    descrizione = models.CharField(max_length=255, blank=True)
    disponibile = models.BooleanField(default=True)

    def __str__(self):
        return self.nome


class OrarioApertura(models.Model):
    """Orario di apertura per un giorno della settimana: un record per ciascuno dei 7
    giorni (giorno_settimana è unique)."""

    class Giorno(models.IntegerChoices):
        # questi numeri coincidono con quelli di date.weekday() in Python (Lunedì=0...
        # Domenica=6), giusto per poterli confrontare direttamente senza conversioni
        LUNEDI = 0, 'Lunedì'
        MARTEDI = 1, 'Martedì'
        MERCOLEDI = 2, 'Mercoledì'
        GIOVEDI = 3, 'Giovedì'
        VENERDI = 4, 'Venerdì'
        SABATO = 5, 'Sabato'
        DOMENICA = 6, 'Domenica'

    giorno_settimana = models.IntegerField(choices=Giorno.choices, unique=True)
    aperto = models.BooleanField(default=True)
    ora_apertura = models.TimeField(default='08:00')
    # 00:00 qui vuol dire "mezzanotte del giorno dopo", non l'inizio della giornata.
    # La conversione la fa time_utils.minuti_dalla_mezzanotte
    ora_chiusura = models.TimeField(default='00:00', help_text='00:00 = mezzanotte')

    class Meta:
        ordering = ['giorno_settimana']

    def __str__(self):
        return f'{self.get_giorno_settimana_display()}: {self.ora_apertura}-{self.ora_chiusura}'


class ChiusuraStraordinaria(models.Model):
    """Chiusura temporanea impostata da un gestore (manutenzione, maltempo...), valida
    per un intervallo di date e, se serve, solo per una fascia oraria dentro quei giorni."""
    data_inizio = models.DateField()
    data_fine = models.DateField()
    ora_inizio = models.TimeField(null=True, blank=True, help_text='Vuoto = tutto il giorno')
    ora_fine = models.TimeField(null=True, blank=True, help_text='Vuoto = tutto il giorno')
    motivo = models.CharField(max_length=255)
    creato_da = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, related_name='chiusure_create')
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inizio']

    def __str__(self):
        return f'{self.motivo} ({self.data_inizio} - {self.data_fine})'

    def copre(self, data, ora_inizio_slot, ora_fine_slot):
        """True se questa chiusura copre, anche solo in parte, l'intervallo passato. Usata
        sia per calcolare la disponibilità sia per il calendario settimanale. Se ora_inizio/
        ora_fine non sono impostate vale per tutta la giornata."""
        if not (self.data_inizio <= data <= self.data_fine):
            return False
        if self.ora_inizio is None or self.ora_fine is None:
            return True
        return si_sovrappongono(self.ora_inizio, self.ora_fine, ora_inizio_slot, ora_fine_slot)


class Tariffa(models.Model):
    """Prezzario della stagione in corso. Ne esiste un solo record "attuale" (vedi
    get_attuale sotto): se un gestore lo cambia, il nuovo prezzo vale solo per le
    prenotazioni future, perché ogni prenotazione si porta dietro il proprio prezzo
    congelato al momento della creazione (Prenotazione.prezzo_listino, in prenotazioni/models.py)."""
    prezzo_diurno_no_spogliatoio = models.DecimalField(max_digits=6, decimal_places=2, default=12)
    prezzo_diurno_spogliatoio = models.DecimalField(max_digits=6, decimal_places=2, default=18)
    prezzo_serale_no_spogliatoio = models.DecimalField(max_digits=6, decimal_places=2, default=18)
    prezzo_serale_spogliatoio = models.DecimalField(max_digits=6, decimal_places=2, default=24)
    soglia_partecipanti = models.PositiveIntegerField(default=8)
    sovrapprezzo_persona_extra = models.DecimalField(max_digits=6, decimal_places=2, default=5)
    aggiornata_il = models.DateTimeField(auto_now=True)

    @classmethod
    def get_attuale(cls):
        """Ritorna la tariffa in vigore. Se il sito è appena stato avviato e non esiste
        ancora nessuna riga, la crea al volo con i valori di default."""
        tariffa = cls.objects.first()
        if tariffa is None:
            tariffa = cls.objects.create()
        return tariffa

    def __str__(self):
        return 'Tariffa in vigore'
