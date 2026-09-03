from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    """`python manage.py elenca_utenti`: stampa a schermo tutti gli utenti registrati
    (clienti, gestori, admin) con ruolo, email, data di registrazione e ultimo accesso.
    Mi serviva un modo rapido per controllare chi c'è nel database senza aprire l'admin."""
    help = 'Interroga il database ed elenca tutti gli utenti registrati (clienti, gestori, admin).'

    def handle(self, *args, **options):
        # list() esegue subito la query e la tiene in memoria: così per contare gli
        # elementi uso len() invece di interrogare di nuovo il database con .count()
        utenti = list(User.objects.all().order_by('role', 'username'))
        if not utenti:
            self.stdout.write('Nessun utente registrato.')
            return

        intestazione = f"{'USERNAME':<20} {'RUOLO':<10} {'EMAIL':<30} {'REGISTRATO IL':<20} {'ULTIMO ACCESSO'}"
        self.stdout.write(intestazione)
        self.stdout.write('-' * len(intestazione))
        for u in utenti:
            ultimo_accesso = u.last_login.strftime('%d/%m/%Y %H:%M') if u.last_login else 'mai'
            registrato_il = u.date_joined.strftime('%d/%m/%Y %H:%M')
            self.stdout.write(
                f"{u.username:<20} {u.get_role_display():<10} {u.email or '-':<30} "
                f"{registrato_il:<20} {ultimo_accesso}"
            )
        self.stdout.write(f'\nTotale: {len(utenti)} utenti.')
