import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from prenotazioni import services
from struttura.models import Campo, OrarioApertura, Servizio, Tariffa

User = get_user_model()

# ogni tupla è: (username, password, ruolo, is_staff, is_superuser) — solo l'admin ha
# is_staff/is_superuser a True, così può entrare anche in /django-admin/
DEMO_USERS = [
    ('admin', 'admin12345', User.Ruolo.ADMIN, True, True),
    ('gestore1', 'gestore12345', User.Ruolo.GESTORE, False, False),
    ('gestore2', 'gestore12345', User.Ruolo.GESTORE, False, False),
    ('cliente1', 'cliente12345', User.Ruolo.CLIENTE, False, False),
    ('cliente2', 'cliente12345', User.Ruolo.CLIENTE, False, False),
    ('capodieci', 'nicola', User.Ruolo.CLIENTE, False, False),
    ('zanini', 'giacomo', User.Ruolo.GESTORE, False, False),
]


class Command(BaseCommand):
    """`python manage.py seed_demo_data` — popola il database con utenti demo, prezzario,
    orari, servizi e un paio di prenotazioni di esempio, così il sito è subito navigabile
    senza doverlo configurare a mano ogni volta. È idempotente (usa get_or_create invece
    di create ovunque), quindi si può rilanciare tranquillamente senza creare doppioni."""
    help = 'Crea utenti demo, prezzario, orari, servizi e alcune prenotazioni di esempio.'

    def handle(self, *args, **options):
        for username, password, role, is_staff, is_superuser in DEMO_USERS:
            user, creato = User.objects.get_or_create(username=username, defaults={
                'role': role, 'is_staff': is_staff, 'is_superuser': is_superuser,
            })
            if creato:
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Creato utente {username} ({role}) / password: {password}'))
            else:
                self.stdout.write(f'Utente {username} già esistente, saltato.')

        campo, _ = Campo.objects.get_or_create(defaults={
            'nome': 'Volley Sassuolo Beach Arena',
            'descrizione': (
                'Uno dei campi da beach volley più grandi di Sassuolo, immerso nel verde alle porte del '
                'percorso natura del Secchia, alle spalle della bocciofila. Sabbia regolamentare, '
                'illuminazione per le partite serali e spogliatoi a disposizione.'
            ),
        })

        for giorno, _label in OrarioApertura.Giorno.choices:
            OrarioApertura.objects.get_or_create(giorno_settimana=giorno)

        Tariffa.get_attuale()

        servizi_demo = [
            ('Spogliatoio', 'Spogliatoio con doccia calda', True),
            ('Parcheggio', 'Parcheggio gratuito riservato ai clienti', True),
            ('Illuminazione serale', 'Faretti a LED per le partite serali', True),
        ]
        for nome, descrizione, disponibile in servizi_demo:
            Servizio.objects.get_or_create(nome=nome, defaults={'descrizione': descrizione, 'disponibile': disponibile})

        cliente1 = User.objects.get(username='cliente1')
        cliente2 = User.objects.get(username='cliente2')
        domani = timezone.localdate() + datetime.timedelta(days=1)

        if not services.slot_occupato(domani, datetime.time(10, 0), datetime.time(11, 0)):
            services.crea_prenotazione(cliente1, domani, datetime.time(10, 0), datetime.time(11, 0), False, 4)
            self.stdout.write(self.style.SUCCESS('Creata prenotazione demo: cliente1, domani 10:00-11:00'))

        if not services.slot_occupato(domani, datetime.time(19, 0), datetime.time(20, 0)):
            services.crea_prenotazione(cliente2, domani, datetime.time(19, 0), datetime.time(20, 0), True, 10)
            self.stdout.write(self.style.SUCCESS('Creata prenotazione demo: cliente2, domani 19:00-20:00 (con spogliatoio, 10 partecipanti)'))

        self.stdout.write(self.style.SUCCESS('Dati demo pronti.'))
