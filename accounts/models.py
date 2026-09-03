from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Di default Django permette fino a 150 caratteri per username/nome/cognome, che per un
# nome vero è francamente troppo. Uso limiti più realistici.
USERNAME_MASSIMO_CARATTERI = 30
NOME_MASSIMO_CARATTERI = 50


class User(AbstractUser):
    """Estende l'utente base di Django (che già gestisce password, permessi, ecc.) con un
    campo "role" per distinguere i tre ruoli della consegna: cliente, gestore, admin.
    username/first_name/last_name sono ridefiniti solo per accorciarne la lunghezza massima."""

    username = models.CharField(
        _('username'),
        max_length=USERNAME_MASSIMO_CARATTERI,
        unique=True,
        help_text=f'Obbligatorio. Massimo {USERNAME_MASSIMO_CARATTERI} caratteri. Solo lettere, cifre e @/./+/-/_ .',
        validators=[UnicodeUsernameValidator()],
        error_messages={'unique': 'Esiste già un utente con questo nome utente.'},
    )
    first_name = models.CharField(_('first name'), max_length=NOME_MASSIMO_CARATTERI, blank=True)
    last_name = models.CharField(_('last name'), max_length=NOME_MASSIMO_CARATTERI, blank=True)

    class Ruolo(models.TextChoices):
        CLIENTE = 'cliente', 'Cliente'
        GESTORE = 'gestore', 'Gestore'
        ADMIN = 'admin', 'Admin'

    # Un nuovo iscritto è sempre "cliente" di default: solo l'admin può promuoverlo a
    # gestore, dalla pagina "Gestione utenti" (vedi views.py).
    role = models.CharField(max_length=10, choices=Ruolo.choices, default=Ruolo.CLIENTE)

    # Scorciatoie per non scrivere ovunque "utente.role == User.Ruolo.CLIENTE": più
    # leggibili sia nel codice che nei template.

    @property
    def is_cliente(self):
        return self.role == self.Ruolo.CLIENTE

    @property
    def is_gestore(self):
        return self.role == self.Ruolo.GESTORE

    @property
    def is_admin_struttura(self):
        return self.role == self.Ruolo.ADMIN

    @property
    def is_gestore_or_admin(self):
        return self.role in (self.Ruolo.GESTORE, self.Ruolo.ADMIN)

    def __str__(self):
        return self.get_full_name() or self.username
