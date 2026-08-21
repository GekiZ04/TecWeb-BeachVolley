"""Form della dashboard gestore/admin — sono quasi tutti ModelForm "banali" (campi presi
di peso dal modello), tranne il formset per gli orari."""

from django import forms

from .models import ChiusuraStraordinaria, OrarioApertura, Servizio, Tariffa


class OrarioAperturaForm(forms.ModelForm):
    class Meta:
        model = OrarioApertura
        fields = ['aperto', 'ora_apertura', 'ora_chiusura']
        # senza questi widget Django mostrerebbe un campo di testo libero per l'orario:
        # con TimeInput(type='time') il browser mostra selettore d'orario.
        widgets = {
            'ora_apertura': forms.TimeInput(attrs={'type': 'time'}),
            'ora_chiusura': forms.TimeInput(attrs={'type': 'time'}),
        }


# Con un formset modifico tutte e 7 le righe di OrarioApertura in un solo POST, invece
# di dover fare 7 form/view separate una per giorno.
OrarioAperturaFormSet = forms.modelformset_factory(
    OrarioApertura, form=OrarioAperturaForm, extra=0, can_delete=False,
)


class TariffaForm(forms.ModelForm):
    class Meta:
        model = Tariffa
        fields = [
            'prezzo_diurno_no_spogliatoio', 'prezzo_diurno_spogliatoio',
            'prezzo_serale_no_spogliatoio', 'prezzo_serale_spogliatoio',
            'soglia_partecipanti', 'sovrapprezzo_persona_extra',
        ]


class ChiusuraStraordinariaForm(forms.ModelForm):
    class Meta:
        model = ChiusuraStraordinaria
        fields = ['data_inizio', 'data_fine', 'ora_inizio', 'ora_fine', 'motivo']
        widgets = {
            'data_inizio': forms.DateInput(attrs={'type': 'date'}),
            'data_fine': forms.DateInput(attrs={'type': 'date'}),
            'ora_inizio': forms.TimeInput(attrs={'type': 'time'}),
            'ora_fine': forms.TimeInput(attrs={'type': 'time'}),
        }


class ServizioForm(forms.ModelForm):
    class Meta:
        model = Servizio
        fields = ['nome', 'descrizione', 'disponibile']
