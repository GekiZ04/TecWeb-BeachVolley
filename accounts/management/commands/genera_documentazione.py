from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# le quattro app/moduli del progetto: pdoc legge le docstring di ognuno e ci costruisce
# una pagina HTML, collegata alle altre (è più o meno il Doxygen di Python)
MODULI_DA_DOCUMENTARE = ['beachvolley', 'accounts', 'struttura', 'prenotazioni']

CARTELLA_OUTPUT = settings.BASE_DIR / 'documentazione'


class Command(BaseCommand):
    """`python manage.py genera_documentazione` — legge le docstring del codice e genera
    la documentazione HTML del progetto con pdoc (va nei dev-packages, quindi serve
    `pipenv install --dev` prima di usarlo). Il risultato finisce in "documentazione/"
    nella root, esclusa da git perché tanto si rigenera al volo quando serve."""
    help = 'Genera la documentazione HTML del progetto (pdoc) nella cartella documentazione/.'

    def handle(self, *args, **options):
        try:
            import pdoc
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "pdoc non è installato. Esegui prima: pipenv install --dev"
            ))
            return

        CARTELLA_OUTPUT.mkdir(exist_ok=True)
        pdoc.pdoc(*MODULI_DA_DOCUMENTARE, output_directory=Path(CARTELLA_OUTPUT))
        self.stdout.write(self.style.SUCCESS(f'Documentazione generata in {CARTELLA_OUTPUT}'))
