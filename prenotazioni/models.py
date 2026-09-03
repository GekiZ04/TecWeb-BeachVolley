"""I modelli principali dell'app: la prenotazione, la lista d'attesa e le notifiche
in-app mostrate agli utenti."""

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from struttura.time_utils import minuti_dalla_mezzanotte

QUOTA_ADMIN = Decimal('0.60')  # percentuale che spetta all'admin su ogni prenotazione
PARTECIPANTI_MASSIMO = 50


class Prenotazione(models.Model):
    """Una prenotazione del campo. Il prezzo (prezzo_listino) si calcola e si "congela" al
    momento della creazione: se poi il gestore cambia il prezzario, le prenotazioni già
    fatte tengono il vecchio prezzo, cambiano solo quelle nuove."""

    class Stato(models.TextChoices):
        CONFERMATA = 'confermata', 'Confermata'
        CANCELLATA = 'cancellata', 'Cancellata'

    utente = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='prenotazioni')
    # Gestore a cui è assegnata (serve per il resoconto economico). SET_NULL invece di
    # CASCADE: se un gestore venisse eliminato non ha senso perdere anche la prenotazione,
    # resta nel database solo senza gestore assegnato.
    gestore = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prenotazioni_gestite',
    )
    data = models.DateField()
    ora_inizio = models.TimeField()
    ora_fine = models.TimeField()
    spogliatoio = models.BooleanField(default=False)
    numero_partecipanti = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(PARTECIPANTI_MASSIMO)],
    )
    stato = models.CharField(max_length=12, choices=Stato.choices, default=Stato.CONFERMATA)
    prezzo_listino = models.DecimalField(max_digits=7, decimal_places=2)
    # Se un admin lo imposta, sovrascrive prezzo_listino come importo da pagare (è lo
    # sconto): resta visibile solo al cliente interessato e all'admin, mai agli altri.
    prezzo_finale = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    creato_il = models.DateTimeField(auto_now_add=True)
    cancellata_il = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-data', '-ora_inizio']

    def __str__(self):
        return f'{self.utente} - {self.data} {self.ora_inizio}'

    @property
    def importo_dovuto(self):
        """Quanto deve pagare davvero il cliente: il prezzo scontato se c'è, altrimenti
        quello di listino."""
        return self.prezzo_finale if self.prezzo_finale is not None else self.prezzo_listino

    @property
    def ha_sconto(self):
        return self.prezzo_finale is not None and self.prezzo_finale != self.prezzo_listino

    @property
    def quota_admin(self):
        """Il 60% dell'incassato, che va all'admin."""
        return (self.importo_dovuto * QUOTA_ADMIN).quantize(Decimal('0.01'))

    @property
    def quota_gestore(self):
        """Il restante 40%, per il gestore che si è preso in carico la prenotazione."""
        return self.importo_dovuto - self.quota_admin

    @property
    def durata_minuti(self):
        return minuti_dalla_mezzanotte(self.ora_fine, fine_giornata=True) - minuti_dalla_mezzanotte(self.ora_inizio)


class ListaAttesa(models.Model):
    """Un utente in attesa che si liberi uno slot già occupato. Quando la prenotazione che
    occupava lo slot viene cancellata, chi era in coda per quell'orario riceve una
    Notifica (vedi services.notifica_lista_attesa) ed esce dalla lista."""
    utente = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='liste_attesa')
    data = models.DateField()
    ora_inizio = models.TimeField()
    ora_fine = models.TimeField()
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creato_il']
        # un utente non può mettersi due volte in lista d'attesa per lo stesso slot
        unique_together = ('utente', 'data', 'ora_inizio')

    def __str__(self):
        return f'{self.utente} in attesa per {self.data} {self.ora_inizio}'


class Notifica(models.Model):
    """Notifica mostrata all'utente nella sua area personale (es. "si è liberato uno
    slot"). Semplice e "in-app": niente invio di email."""
    utente = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifiche')
    messaggio = models.CharField(max_length=255)
    link = models.CharField(max_length=255, blank=True)
    letta = models.BooleanField(default=False)
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creato_il']

    def __str__(self):
        return f'Notifica per {self.utente}: {self.messaggio[:30]}'
