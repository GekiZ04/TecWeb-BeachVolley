"""Form per creare/modificare una prenotazione e per iscriversi alla lista d'attesa.

I campi data/ora_inizio/ora_fine sono HiddenInput perché l'utente non li scrive a mano:
li imposta il JavaScript (static/js/disponibilita.js) quando sceglie uno slot dal menù,
e vengono inviati insieme al resto del form.
"""

from django import forms

from struttura.services import DURATA_MASSIMA_MINUTI, DURATA_MINIMA_MINUTI
from struttura.time_utils import minuti_dalla_mezzanotte

from .models import PARTECIPANTI_MASSIMO


class PrenotazioneForm(forms.Form):
    data = forms.DateField(widget=forms.HiddenInput)
    ora_inizio = forms.TimeField(widget=forms.HiddenInput)
    ora_fine = forms.TimeField(widget=forms.HiddenInput)
    spogliatoio = forms.BooleanField(required=False, label='Includi spogliatoio')
    numero_partecipanti = forms.IntegerField(
        min_value=1, max_value=PARTECIPANTI_MASSIMO, initial=1, label='Numero di partecipanti',
        error_messages={'max_value': f'Non puoi indicare più di {PARTECIPANTI_MASSIMO} partecipanti.'},
    )

    def clean(self):
        """Controlla che la durata (ora_fine - ora_inizio) sia positiva, un multiplo di
        15 minuti e dentro i limiti min/max. È questo il controllo che conta davvero:
        anche se uno smanettasse con i campi nascosti nel browser, il server scarta
        comunque i valori che non tornano."""
        cleaned = super().clean()
        ora_inizio = cleaned.get('ora_inizio')
        ora_fine = cleaned.get('ora_fine')
        if ora_inizio is not None and ora_fine is not None:
            durata = minuti_dalla_mezzanotte(ora_fine, fine_giornata=True) - minuti_dalla_mezzanotte(ora_inizio)
            if durata <= 0:
                raise forms.ValidationError("L'orario di fine deve essere successivo a quello di inizio.")
            if durata % 15 != 0:
                raise forms.ValidationError('La durata deve essere un multiplo di 15 minuti.')
            if durata < DURATA_MINIMA_MINUTI:
                raise forms.ValidationError(f'La durata minima è di {DURATA_MINIMA_MINUTI} minuti.')
            if durata > DURATA_MASSIMA_MINUTI:
                raise forms.ValidationError(f'La durata massima è di {DURATA_MASSIMA_MINUTI // 60} ore.')
        return cleaned


class ListaAttesaForm(forms.Form):
    """Form minimo per iscriversi alla lista d'attesa di uno slot occupato: bastano data
    e orario, partecipanti/spogliatoio non servono finché non si prenota per davvero."""
    data = forms.DateField(widget=forms.HiddenInput)
    ora_inizio = forms.TimeField(widget=forms.HiddenInput)
    ora_fine = forms.TimeField(widget=forms.HiddenInput)
