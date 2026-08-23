import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from struttura.models import OrarioApertura, Tariffa

from . import services
from .models import ListaAttesa, Notifica, Prenotazione
from .pricing import calcola_prezzo


class PricingTests(TestCase):
    """pricing.calcola_prezzo: fasce diurna/serale, spogliatoio, sovrapprezzo partecipanti
    oltre soglia, e i casi limite (quarti d'ora, a cavallo tra le fasce, mezzanotte)."""

    def setUp(self):
        self.tariffa = Tariffa.get_attuale()  # 12/18/18/24, soglia 8, extra 5€

    def test_fascia_diurna_senza_spogliatoio_un_ora(self):
        prezzo = calcola_prezzo(datetime.time(10, 0), datetime.time(11, 0), False, 4, self.tariffa)
        self.assertEqual(prezzo, Decimal('12.00'))

    def test_fascia_diurna_con_spogliatoio(self):
        prezzo = calcola_prezzo(datetime.time(10, 0), datetime.time(11, 0), True, 4, self.tariffa)
        self.assertEqual(prezzo, Decimal('18.00'))

    def test_fascia_serale_inizia_alle_18(self):
        prezzo = calcola_prezzo(datetime.time(18, 0), datetime.time(19, 0), False, 4, self.tariffa)
        self.assertEqual(prezzo, Decimal('18.00'))

    def test_fascia_serale_con_spogliatoio(self):
        prezzo = calcola_prezzo(datetime.time(20, 0), datetime.time(21, 0), True, 4, self.tariffa)
        self.assertEqual(prezzo, Decimal('24.00'))

    def test_sovrapprezzo_partecipanti_oltre_la_soglia(self):
        # 10 partecipanti, soglia 8 -> 2 persone extra * 5€ = 10€ in più
        prezzo = calcola_prezzo(datetime.time(10, 0), datetime.time(11, 0), False, 10, self.tariffa)
        self.assertEqual(prezzo, Decimal('22.00'))

    def test_quarto_dora(self):
        # 15 minuti diurni senza spogliatoio: 12€/h / 4 = 3€
        prezzo = calcola_prezzo(datetime.time(10, 0), datetime.time(10, 15), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('3.00'))

    def test_un_ora_e_mezza(self):
        # 1h30 diurno senza spogliatoio: 12 * 1.5 = 18€
        prezzo = calcola_prezzo(datetime.time(9, 0), datetime.time(10, 30), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('18.00'))

    def test_prenotazione_a_cavallo_tra_diurno_e_serale(self):
        # 17:00-19:00 senza spogliatoio: 1h diurno (12) + 1h serale (18) = 30€
        prezzo = calcola_prezzo(datetime.time(17, 0), datetime.time(19, 0), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('30.00'))

    def test_prenotazione_a_cavallo_con_quarto_dora(self):
        # 17:45-18:30 senza spogliatoio: 15 min diurno (3€) + 30 min serale (18/2=9€) = 12€
        prezzo = calcola_prezzo(datetime.time(17, 45), datetime.time(18, 30), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('12.00'))

    def test_prenotazione_fino_a_mezzanotte_e_serale(self):
        # 23:00-00:00 (mezzanotte), senza spogliatoio: 1h serale = 18€
        prezzo = calcola_prezzo(datetime.time(23, 0), datetime.time(0, 0), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('18.00'))

    def test_prenotazione_lunga_fino_a_mezzanotte(self):
        # 18:15-20:30 (2h15) senza spogliatoio, tutta serale: 18 * 2.25 = 40.50€
        prezzo = calcola_prezzo(datetime.time(18, 15), datetime.time(20, 30), False, 2, self.tariffa)
        self.assertEqual(prezzo, Decimal('40.50'))


class PrenotazioneModelTests(TestCase):
    """Le property calcolate sul modello Prenotazione (importo_dovuto, quote admin/
    gestore, durata_minuti) e il vincolo sul numero massimo di partecipanti."""

    def setUp(self):
        self.cliente = User.objects.create_user(username='cliente', password='pw12345678', role=User.Ruolo.CLIENTE)

    def test_importo_dovuto_usa_prezzo_finale_se_presente(self):
        p = Prenotazione.objects.create(
            utente=self.cliente, data=timezone.localdate(), ora_inizio=datetime.time(10, 0),
            ora_fine=datetime.time(11, 0), prezzo_listino=Decimal('18'), prezzo_finale=Decimal('10'),
        )
        self.assertEqual(p.importo_dovuto, Decimal('10'))
        self.assertTrue(p.ha_sconto)

    def test_quota_admin_e_gestore(self):
        p = Prenotazione.objects.create(
            utente=self.cliente, data=timezone.localdate(), ora_inizio=datetime.time(10, 0),
            ora_fine=datetime.time(11, 0), prezzo_listino=Decimal('100'),
        )
        self.assertEqual(p.quota_admin, Decimal('60.00'))
        self.assertEqual(p.quota_gestore, Decimal('40.00'))

    def test_durata_minuti(self):
        p = Prenotazione.objects.create(
            utente=self.cliente, data=timezone.localdate(), ora_inizio=datetime.time(9, 15),
            ora_fine=datetime.time(11, 0), prezzo_listino=Decimal('21'),
        )
        self.assertEqual(p.durata_minuti, 105)

    def test_durata_minuti_fino_a_mezzanotte(self):
        p = Prenotazione.objects.create(
            utente=self.cliente, data=timezone.localdate(), ora_inizio=datetime.time(23, 0),
            ora_fine=datetime.time(0, 0), prezzo_listino=Decimal('18'),
        )
        self.assertEqual(p.durata_minuti, 60)

    def test_full_clean_rifiuta_piu_di_cinquanta_partecipanti(self):
        p = Prenotazione(
            utente=self.cliente, data=timezone.localdate(), ora_inizio=datetime.time(10, 0),
            ora_fine=datetime.time(11, 0), prezzo_listino=Decimal('12'), numero_partecipanti=51,
        )
        with self.assertRaises(ValidationError):
            p.full_clean()


class BookingFlowTests(TestCase):
    """Test end-to-end del flusso di prenotazione tramite il form: permessi, assegnazione
    automatica del gestore, sovrapposizioni, limiti di durata/partecipanti e cancellazione
    con notifica alla lista d'attesa."""

    def setUp(self):
        for giorno, _ in OrarioApertura.Giorno.choices:
            OrarioApertura.objects.create(giorno_settimana=giorno)
        self.gestore = User.objects.create_user(username='gestore', password='pw12345678', role=User.Ruolo.GESTORE)
        self.cliente1 = User.objects.create_user(username='cliente1', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.cliente2 = User.objects.create_user(username='cliente2', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.domani = timezone.localdate() + datetime.timedelta(days=1)

    def _prenota(self, client, ora_inizio='10:00', ora_fine='11:00', partecipanti=2):
        return client.post(reverse('prenotazioni:nuova'), {
            'data': self.domani.isoformat(), 'ora_inizio': ora_inizio, 'ora_fine': ora_fine,
            'numero_partecipanti': partecipanti,
        })

    def test_anonimo_non_puo_prenotare(self):
        response = self._prenota(self.client)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Prenotazione.objects.count(), 0)

    def test_pagina_nuova_preseleziona_orario_da_query_string(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:nuova'), {'data': self.domani.isoformat(), 'ora': '10:00'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-prefill-ora-inizio="10:00"')

    def test_pagina_nuova_ignora_orario_non_valido_in_query_string(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:nuova'), {'data': self.domani.isoformat(), 'ora': 'non-valido'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-prefill-ora-inizio')

    def test_cliente_puo_prenotare_slot_libero(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self._prenota(self.client)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Prenotazione.objects.count(), 1)
        prenotazione = Prenotazione.objects.first()
        self.assertEqual(prenotazione.gestore, self.gestore)

    def test_prenotazione_con_inizio_a_quarto_dora_e_durata_di_due_ore_e_mezza(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self._prenota(self.client, ora_inizio='10:15', ora_fine='12:45')
        self.assertEqual(response.status_code, 302)
        prenotazione = Prenotazione.objects.first()
        self.assertEqual(prenotazione.ora_inizio, datetime.time(10, 15))
        self.assertEqual(prenotazione.ora_fine, datetime.time(12, 45))
        self.assertEqual(prenotazione.durata_minuti, 150)

    def test_prenotazione_fino_a_mezzanotte(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self._prenota(self.client, ora_inizio='23:00', ora_fine='00:00')
        self.assertEqual(response.status_code, 302)
        prenotazione = Prenotazione.objects.first()
        self.assertEqual(prenotazione.ora_fine, datetime.time(0, 0))
        self.assertEqual(prenotazione.durata_minuti, 60)
        self.assertEqual(prenotazione.prezzo_listino, Decimal('18.00'))

    def test_sovrapposizione_rilevata_contro_prenotazione_fino_a_mezzanotte(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client, ora_inizio='23:00', ora_fine='00:00')
        self.client.login(username='cliente2', password='pw12345678')
        response = self._prenota(self.client, ora_inizio='23:30', ora_fine='00:00')
        self.assertEqual(Prenotazione.objects.filter(stato=Prenotazione.Stato.CONFERMATA).count(), 1)
        self.assertEqual(response.status_code, 302)

    def test_niente_sovrapposizioni_tra_prenotazioni(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client)
        self.client.login(username='cliente2', password='pw12345678')
        self._prenota(self.client)
        self.assertEqual(Prenotazione.objects.filter(stato=Prenotazione.Stato.CONFERMATA).count(), 1)

    def test_niente_sovrapposizioni_parziali(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client, ora_inizio='10:00', ora_fine='11:00')
        self.client.login(username='cliente2', password='pw12345678')
        response = self._prenota(self.client, ora_inizio='10:30', ora_fine='11:30')
        self.assertEqual(Prenotazione.objects.filter(stato=Prenotazione.Stato.CONFERMATA).count(), 1)
        self.assertEqual(response.status_code, 302)

    def test_durata_non_multipla_di_15_minuti_rifiutata(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client, ora_inizio='10:00', ora_fine='10:50')
        self.assertEqual(Prenotazione.objects.count(), 0)

    def test_durata_superiore_al_massimo_rifiutata(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client, ora_inizio='08:00', ora_fine='13:00')  # 5 ore, oltre il massimo di 4
        self.assertEqual(Prenotazione.objects.count(), 0)

    def test_cinquanta_partecipanti_accettato(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self._prenota(self.client, partecipanti=50)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Prenotazione.objects.count(), 1)

    def test_oltre_cinquanta_partecipanti_rifiutato(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client, partecipanti=51)
        self.assertEqual(Prenotazione.objects.count(), 0)

    def test_anteprima_prezzo_rifiuta_oltre_cinquanta_partecipanti(self):
        self.client.login(username='cliente1', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:prezzo'), {
            'ora_inizio': '10:00', 'ora_fine': '11:00', 'spogliatoio': 'false', 'partecipanti': '51',
        })
        self.assertEqual(response.status_code, 400)

    def test_cancellazione_libera_slot_e_notifica_lista_attesa(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client)
        prenotazione = Prenotazione.objects.first()

        self.client.login(username='cliente2', password='pw12345678')
        ListaAttesa.objects.create(
            utente=self.cliente2, data=self.domani, ora_inizio=datetime.time(10, 0), ora_fine=datetime.time(10, 15),
        )

        services.cancella_prenotazione(prenotazione)
        prenotazione.refresh_from_db()
        self.assertEqual(prenotazione.stato, Prenotazione.Stato.CANCELLATA)
        self.assertEqual(ListaAttesa.objects.count(), 0)
        self.assertEqual(Notifica.objects.filter(utente=self.cliente2, letta=False).count(), 1)

    def test_solo_proprietario_puo_cancellare(self):
        self.client.login(username='cliente1', password='pw12345678')
        self._prenota(self.client)
        prenotazione = Prenotazione.objects.first()

        self.client.login(username='cliente2', password='pw12345678')
        response = self.client.post(reverse('prenotazioni:cancella', args=[prenotazione.pk]))
        self.assertEqual(response.status_code, 404)
        prenotazione.refresh_from_db()
        self.assertEqual(prenotazione.stato, Prenotazione.Stato.CONFERMATA)


class EconomiaTests(TestCase):
    """La pagina economia (solo admin): resoconto settimanale, applicazione di uno sconto
    (visibile solo a cliente e admin) e riassegnazione manuale del gestore."""

    def setUp(self):
        for giorno, _ in OrarioApertura.Giorno.choices:
            OrarioApertura.objects.create(giorno_settimana=giorno)
        self.admin = User.objects.create_user(username='admin', password='pw12345678', role=User.Ruolo.ADMIN)
        self.gestore = User.objects.create_user(username='gestore', password='pw12345678', role=User.Ruolo.GESTORE)
        self.gestore2 = User.objects.create_user(username='gestore2', password='pw12345678', role=User.Ruolo.GESTORE)
        self.cliente = User.objects.create_user(username='cliente', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.domani = timezone.localdate() + datetime.timedelta(days=1)
        self.prenotazione = services.crea_prenotazione(
            self.cliente, self.domani, datetime.time(10, 0), datetime.time(11, 0), False, 2,
        )

    def test_gestore_non_admin_non_accede_a_economia(self):
        self.client.login(username='gestore', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:economia'))
        self.assertEqual(response.status_code, 302)

    def test_admin_vede_resoconto_settimanale(self):
        self.client.login(username='admin', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:economia'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Resoconto per gestore')

    def test_admin_applica_sconto_visibile_solo_a_proprietario(self):
        self.client.login(username='admin', password='pw12345678')
        response = self.client.post(reverse('prenotazioni:applica_sconto', args=[self.prenotazione.pk]), {
            'prezzo_finale': '5.00',
        })
        self.assertEqual(response.status_code, 302)
        self.prenotazione.refresh_from_db()
        self.assertEqual(self.prenotazione.importo_dovuto, Decimal('5.00'))

        self.client.login(username='cliente', password='pw12345678')
        response = self.client.get(reverse('prenotazioni:mie'))
        self.assertContains(response, '5,00')  # formato italiano, virgola come separatore decimale

    def test_admin_riassegna_prenotazione_a_un_altro_gestore(self):
        self.client.login(username='admin', password='pw12345678')
        response = self.client.post(reverse('prenotazioni:riassegna_gestore', args=[self.prenotazione.pk]), {
            'gestore_id': self.gestore2.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.prenotazione.refresh_from_db()
        self.assertEqual(self.prenotazione.gestore, self.gestore2)

    def test_admin_puo_rimuovere_assegnazione_gestore(self):
        self.client.login(username='admin', password='pw12345678')
        self.client.post(reverse('prenotazioni:riassegna_gestore', args=[self.prenotazione.pk]), {
            'gestore_id': '',
        })
        self.prenotazione.refresh_from_db()
        self.assertIsNone(self.prenotazione.gestore)

    def test_riassegnazione_id_non_valido_non_modifica_nulla(self):
        self.client.login(username='admin', password='pw12345678')
        self.client.post(reverse('prenotazioni:riassegna_gestore', args=[self.prenotazione.pk]), {
            'gestore_id': self.cliente.pk,  # non è un gestore
        })
        self.prenotazione.refresh_from_db()
        self.assertEqual(self.prenotazione.gestore, self.gestore)

    def test_non_admin_non_puo_riassegnare(self):
        self.client.login(username='gestore', password='pw12345678')
        response = self.client.post(reverse('prenotazioni:riassegna_gestore', args=[self.prenotazione.pk]), {
            'gestore_id': self.gestore2.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.prenotazione.refresh_from_db()
        self.assertEqual(self.prenotazione.gestore, self.gestore)
