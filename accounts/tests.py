from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import User

# i nomi dei test sono già abbastanza parlanti (stile "test_cosa_verifica"), quindi i
# commenti qui sotto ci sono solo dove il "perché" non era scontato dal solo nome


class SignupTests(TestCase):
    """Il form pubblico di registrazione: crea sempre un cliente, mai un gestore/admin,
    e rispetta i limiti di lunghezza dei campi del modello User."""

    def test_signup_crea_sempre_un_utente_con_ruolo_cliente(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'marco', 'password1': 'passwordsolida123', 'password2': 'passwordsolida123',
        })
        self.assertEqual(response.status_code, 302)
        utente = User.objects.get(username='marco')
        self.assertEqual(utente.role, User.Ruolo.CLIENTE)
        self.assertTrue(utente.is_cliente)

    def test_login_utente_registrato(self):
        User.objects.create_user(username='paolo', password='passwordsolida123', role=User.Ruolo.CLIENTE)
        response = self.client.post(reverse('accounts:login'), {'username': 'paolo', 'password': 'passwordsolida123'})
        self.assertEqual(response.status_code, 302)
        area_personale = self.client.get(reverse('prenotazioni:mie'))
        self.assertEqual(area_personale.status_code, 200)

    def test_username_troppo_lungo_rifiutato(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'u' * 31,  # limite è 30
            'password1': 'passwordsolida123', 'password2': 'passwordsolida123',
        })
        self.assertEqual(response.status_code, 200)  # form non valido, ripropone la pagina
        self.assertFalse(User.objects.filter(username__startswith='uuu').exists())

    def test_username_al_limite_accettato(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'u' * 30,
            'password1': 'passwordsolida123', 'password2': 'passwordsolida123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='u' * 30).exists())

    def test_nome_troppo_lungo_rifiutato(self):
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'utentenome', 'first_name': 'n' * 51,
            'password1': 'passwordsolida123', 'password2': 'passwordsolida123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='utentenome').exists())


class GestioneUtentiTests(TestCase):
    """Solo l'admin può promuovere/retrocedere un utente tra cliente e gestore, e
    nemmeno lui può toccare il ruolo di un altro admin."""

    def setUp(self):
        self.admin = User.objects.create_user(username='admin', password='pw12345678', role=User.Ruolo.ADMIN)
        self.cliente = User.objects.create_user(username='cliente', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.gestore = User.objects.create_user(username='gestore', password='pw12345678', role=User.Ruolo.GESTORE)

    def test_anonimo_non_accede_alla_gestione_utenti(self):
        response = self.client.get(reverse('accounts:gestione_utenti'))
        self.assertEqual(response.status_code, 302)

    def test_cliente_non_puo_promuovere_se_stesso(self):
        self.client.login(username='cliente', password='pw12345678')
        response = self.client.post(reverse('accounts:gestione_utenti'), {
            'user_id': self.cliente.pk, 'ruolo': User.Ruolo.GESTORE,
        })
        self.assertEqual(response.status_code, 302)  # redirect al login, permesso negato
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.is_cliente)

    def test_admin_promuove_cliente_a_gestore(self):
        self.client.login(username='admin', password='pw12345678')
        response = self.client.post(reverse('accounts:gestione_utenti'), {
            'user_id': self.cliente.pk, 'ruolo': User.Ruolo.GESTORE,
        })
        self.assertEqual(response.status_code, 302)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.is_gestore)

    def test_admin_puo_riportare_un_gestore_a_cliente(self):
        self.client.login(username='admin', password='pw12345678')
        self.client.post(reverse('accounts:gestione_utenti'), {
            'user_id': self.gestore.pk, 'ruolo': User.Ruolo.CLIENTE,
        })
        self.gestore.refresh_from_db()
        self.assertTrue(self.gestore.is_cliente)

    def test_admin_non_puo_modificare_un_altro_admin(self):
        altro_admin = User.objects.create_user(username='admin2', password='pw12345678', role=User.Ruolo.ADMIN)
        self.client.login(username='admin', password='pw12345678')
        self.client.post(reverse('accounts:gestione_utenti'), {
            'user_id': altro_admin.pk, 'ruolo': User.Ruolo.GESTORE,
        })
        altro_admin.refresh_from_db()
        self.assertTrue(altro_admin.is_admin_struttura)


class ElencaUtentiCommandTests(TestCase):
    """Il management command `elenca_utenti` (controllo l'output testuale su stdout)."""

    def test_elenca_tutti_gli_utenti_registrati(self):
        User.objects.create_user(username='cliente_cmd', password='pw12345678', role=User.Ruolo.CLIENTE)
        User.objects.create_user(username='admin_cmd', password='pw12345678', role=User.Ruolo.ADMIN)

        output = StringIO()
        call_command('elenca_utenti', stdout=output)
        risultato = output.getvalue()

        self.assertIn('cliente_cmd', risultato)
        self.assertIn('admin_cmd', risultato)
        self.assertIn('Totale: 2 utenti.', risultato)

    def test_nessun_utente_registrato(self):
        output = StringIO()
        call_command('elenca_utenti', stdout=output)
        self.assertIn('Nessun utente registrato.', output.getvalue())
