import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User

from .models import ChiusuraStraordinaria, OrarioApertura, Tariffa
from .services import calendario_settimana, intervallo_disponibile, slot_disponibili


class DisponibilitaTests(TestCase):
    """Il calcolo degli slot liberi/occupati (slot_disponibili, intervallo_disponibile,
    calendario_settimana), compreso il caso limite dell'apertura fino a mezzanotte e il
    posizionamento grafico dei blocchi occupati."""

    def setUp(self):
        for giorno, _ in OrarioApertura.Giorno.choices:
            OrarioApertura.objects.create(giorno_settimana=giorno)

    def test_slot_disponibili_copre_intera_apertura(self):
        lunedi = datetime.date(2026, 7, 27)  # è un lunedì
        slots = slot_disponibili(lunedi)
        self.assertEqual(len(slots), 64)  # 08:00-00:00 -> 64 slot da 15 minuti
        self.assertEqual(slots[-1]['ora_fine'], datetime.time(0, 0))  # l'ultimo slot arriva a mezzanotte
        self.assertTrue(all(s['stato'] == 'libero' for s in slots))

    def test_slot_disponibili_giorno_chiuso(self):
        orario = OrarioApertura.objects.get(giorno_settimana=0)
        orario.aperto = False
        orario.save()
        lunedi = datetime.date(2026, 7, 27)
        self.assertEqual(slot_disponibili(lunedi), [])

    def test_intervallo_disponibile_multiorario(self):
        lunedi = datetime.date(2026, 7, 27)
        self.assertTrue(intervallo_disponibile(lunedi, datetime.time(10, 15), datetime.time(12, 30)))

    def test_intervallo_non_disponibile_fuori_orario_apertura(self):
        lunedi = datetime.date(2026, 7, 27)
        self.assertFalse(intervallo_disponibile(lunedi, datetime.time(7, 0), datetime.time(8, 0)))

    def test_intervallo_disponibile_fino_a_mezzanotte(self):
        lunedi = datetime.date(2026, 7, 27)
        self.assertTrue(intervallo_disponibile(lunedi, datetime.time(22, 30), datetime.time(0, 0)))

    def test_calendario_settimana_copre_7_giorni_e_ore_di_apertura(self):
        lunedi = datetime.date(2026, 7, 27)
        calendario = calendario_settimana(lunedi)
        self.assertEqual(len(calendario['giorni']), 7)
        self.assertEqual(calendario['giorni'][0], lunedi)
        self.assertEqual(len(calendario['righe']), 16)  # 08:00-00:00 -> 16 righe da 1 ora
        self.assertTrue(all(cella['stato'] == 'libero' and not cella['blocchi']
                             for riga in calendario['righe'] for cella in riga['celle']))

    def test_calendario_settimana_segna_giorno_chiuso(self):
        lunedi = datetime.date(2026, 7, 27)
        orario = OrarioApertura.objects.get(giorno_settimana=0)  # lunedì
        orario.aperto = False
        orario.save()
        calendario = calendario_settimana(lunedi)
        colonna_lunedi = [riga['celle'][0]['stato'] for riga in calendario['righe']]
        colonna_martedi = [riga['celle'][1]['stato'] for riga in calendario['righe']]
        self.assertTrue(all(c == 'chiuso' for c in colonna_lunedi))
        self.assertTrue(all(c == 'libero' for c in colonna_martedi))

    def test_calendario_settimana_segna_prenotazione_come_occupato(self):
        from accounts.models import User as Utente
        from prenotazioni import services as prenotazioni_services

        cliente = Utente.objects.create_user(username='cliente_cal', password='pw12345678', role=Utente.Ruolo.CLIENTE)
        lunedi = datetime.date(2026, 7, 27)
        prenotazioni_services.crea_prenotazione(cliente, lunedi, datetime.time(10, 0), datetime.time(11, 0), False, 2)

        calendario = calendario_settimana(lunedi)
        riga_10 = next(r for r in calendario['righe'] if r['ora_inizio'] == datetime.time(10, 0))
        cella = riga_10['celle'][0]
        self.assertEqual(cella['stato'], 'occupato')
        self.assertEqual(cella['blocchi'], [{'top': 0, 'altezza': 100}])

    def test_calendario_settimana_blocco_spostato_per_prenotazione_a_quarto_dora(self):
        from accounts.models import User as Utente
        from prenotazioni import services as prenotazioni_services

        cliente = Utente.objects.create_user(username='cliente_cal2', password='pw12345678', role=Utente.Ruolo.CLIENTE)
        lunedi = datetime.date(2026, 7, 27)
        # prenotazione di 30 minuti che inizia un quarto d'ora dopo le 10: 10:15-10:45
        prenotazioni_services.crea_prenotazione(cliente, lunedi, datetime.time(10, 15), datetime.time(10, 45), False, 2)

        calendario = calendario_settimana(lunedi)
        riga_10 = next(r for r in calendario['righe'] if r['ora_inizio'] == datetime.time(10, 0))
        cella = riga_10['celle'][0]
        self.assertEqual(cella['stato'], 'occupato')
        # offset 15 min su 60 = 25%, durata 30 min su 60 = 50%
        self.assertEqual(cella['blocchi'], [{'top': 25.0, 'altezza': 50.0}])

    def test_calendario_settimana_segna_chiusura_straordinaria(self):
        lunedi = datetime.date(2026, 7, 27)
        ChiusuraStraordinaria.objects.create(data_inizio=lunedi, data_fine=lunedi, motivo='Manutenzione')
        calendario = calendario_settimana(lunedi)
        colonna_lunedi = [riga['celle'][0]['stato'] for riga in calendario['righe']]
        self.assertTrue(all(c == 'chiuso' for c in colonna_lunedi))

    def test_calendario_settimana_ogni_cella_riporta_il_proprio_giorno(self):
        lunedi = datetime.date(2026, 7, 27)
        calendario = calendario_settimana(lunedi)
        for riga in calendario['righe']:
            for indice, cella in enumerate(riga['celle']):
                self.assertEqual(cella['data'], calendario['giorni'][indice])


class PermessiStrutturaTests(TestCase):
    """Solo gestori/admin possono entrare nella dashboard e modificare il prezzario; la
    home pubblica invece resta visibile a chiunque."""

    def setUp(self):
        self.cliente = User.objects.create_user(username='cliente', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.gestore = User.objects.create_user(username='gestore', password='pw12345678', role=User.Ruolo.GESTORE)

    def test_anonimo_non_accede_alla_dashboard(self):
        response = self.client.get(reverse('struttura:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_cliente_non_accede_alla_dashboard(self):
        self.client.login(username='cliente', password='pw12345678')
        response = self.client.get(reverse('struttura:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_gestore_accede_alla_dashboard(self):
        self.client.login(username='gestore', password='pw12345678')
        response = self.client.get(reverse('struttura:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_solo_gestore_puo_aggiornare_tariffa(self):
        tariffa = Tariffa.get_attuale()
        payload = {
            'prezzo_diurno_no_spogliatoio': '15', 'prezzo_diurno_spogliatoio': '20',
            'prezzo_serale_no_spogliatoio': '20', 'prezzo_serale_spogliatoio': '26',
            'soglia_partecipanti': '8', 'sovrapprezzo_persona_extra': '5',
        }
        self.client.login(username='cliente', password='pw12345678')
        self.client.post(reverse('struttura:salva_tariffa'), payload)
        tariffa.refresh_from_db()
        self.assertEqual(str(tariffa.prezzo_diurno_no_spogliatoio), '12.00')

        self.client.login(username='gestore', password='pw12345678')
        self.client.post(reverse('struttura:salva_tariffa'), payload)
        tariffa.refresh_from_db()
        self.assertEqual(str(tariffa.prezzo_diurno_no_spogliatoio), '15.00')

    def test_home_pubblica_mostra_prezzario(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Prezzario')


class CalendarioClickabileTests(TestCase):
    """Gli slot liberi nel calendario in home sono cliccabili (portano dritti al form di
    prenotazione) solo per chi può prenotare, e solo se non sono già nel passato."""

    def setUp(self):
        self.cliente = User.objects.create_user(username='cliente_click', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.gestore = User.objects.create_user(username='gestore_click', password='pw12345678', role=User.Ruolo.GESTORE)

    def test_anonimo_vede_slot_liberi_cliccabili(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'cella-link')
        self.assertContains(response, reverse('prenotazioni:nuova'))

    def test_cliente_vede_slot_liberi_cliccabili(self):
        self.client.login(username='cliente_click', password='pw12345678')
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'cella-link')

    def test_gestore_non_vede_slot_cliccabili(self):
        self.client.login(username='gestore_click', password='pw12345678')
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'cella-link')

    def test_settimana_passata_non_ha_slot_cliccabili(self):
        self.client.login(username='cliente_click', password='pw12345678')
        due_settimane_fa = (timezone.localdate() - datetime.timedelta(days=14)).isoformat()
        response = self.client.get(reverse('home'), {'inizio': due_settimane_fa})
        self.assertNotContains(response, 'cella-link')


class CalendarioAjaxTests(TestCase):
    """L'endpoint usato da static/js/calendario.js per scorrere le settimane senza
    ricaricare la pagina: deve ritornare solo il frammento del calendario, non la pagina intera."""

    def test_ritorna_solo_il_frammento_non_la_pagina_intera(self):
        response = self.client.get(reverse('struttura:calendario_ajax'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'calendario-settimanale')
        # se contenesse la navbar o il <!DOCTYPE>, vorrebbe dire che sta renderizzando
        # l'intera pagina invece del solo frammento
        self.assertNotContains(response, '<!DOCTYPE')
        self.assertNotContains(response, 'class="navbar"')

    def test_rispetta_il_parametro_inizio(self):
        lunedi = datetime.date(2026, 7, 27)
        response = self.client.get(reverse('struttura:calendario_ajax'), {'inizio': lunedi.isoformat()})
        self.assertContains(response, lunedi.strftime('%d/%m'))


class DisponibilitaJsonTests(TestCase):
    """L'endpoint AJAX usato dal form di prenotazione, in particolare il parametro
    "escludi" che alla pagina di modifica serve per mostrare come libero lo slot della
    prenotazione che si sta modificando — ma solo se è del proprietario."""

    def setUp(self):
        for giorno, _ in OrarioApertura.Giorno.choices:
            OrarioApertura.objects.create(giorno_settimana=giorno)
        from prenotazioni import services as prenotazioni_services

        self.cliente = User.objects.create_user(username='cliente_json', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.altro_cliente = User.objects.create_user(username='altro_json', password='pw12345678', role=User.Ruolo.CLIENTE)
        self.lunedi = datetime.date(2026, 7, 27)
        self.prenotazione = prenotazioni_services.crea_prenotazione(
            self.cliente, self.lunedi, datetime.time(10, 0), datetime.time(11, 0), False, 2,
        )

    def _slot_10(self, response):
        payload = response.json()
        return next(s for s in payload['slots'] if s['ora_inizio'] == '10:00')

    def test_slot_occupato_di_default(self):
        response = self.client.get(reverse('struttura:disponibilita_json'), {'data': self.lunedi.isoformat()})
        self.assertEqual(self._slot_10(response)['stato'], 'occupato')

    def test_escludi_propria_prenotazione_la_mostra_libera(self):
        self.client.login(username='cliente_json', password='pw12345678')
        response = self.client.get(reverse('struttura:disponibilita_json'), {
            'data': self.lunedi.isoformat(), 'escludi': self.prenotazione.pk,
        })
        self.assertEqual(self._slot_10(response)['stato'], 'libero')

    def test_non_puo_escludere_prenotazione_di_un_altro_utente(self):
        self.client.login(username='altro_json', password='pw12345678')
        response = self.client.get(reverse('struttura:disponibilita_json'), {
            'data': self.lunedi.isoformat(), 'escludi': self.prenotazione.pk,
        })
        self.assertEqual(self._slot_10(response)['stato'], 'occupato')
