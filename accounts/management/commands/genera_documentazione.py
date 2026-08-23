from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

# Elenco esplicito (non le app intere) per due motivi: escludere i file "rumore" che
# pdoc includerebbe altrimenti (migrazioni auto-generate, apps.py, wsgi.py/asgi.py, tutta
# roba senza docstring utili), e per raggruppare l'output per macrosettore invece che in
# un unico elenco alfabetico piatto di tutti i file del progetto. Ogni sezione qui sotto
# diventa un blocco con intestazione nella pagina indice generata da _scrivi_indice.
SEZIONI = [
    ('Progetto', [
        'beachvolley.settings',
        'beachvolley.urls',
    ]),
    ('Account e utenti', [
        'accounts.models',
        'accounts.views',
        'accounts.forms',
        'accounts.permissions',
        'accounts.urls',
        'accounts.admin',
        'accounts.management.commands.elenca_utenti',
        'accounts.management.commands.genera_documentazione',
        'accounts.tests',
    ]),
    ('Struttura del campo (orari, prezzario, servizi)', [
        'struttura.models',
        'struttura.views',
        'struttura.forms',
        'struttura.services',
        'struttura.time_utils',
        'struttura.admin',
        'struttura.urls',
        'struttura.tests',
    ]),
    ('Prenotazioni, prezzi ed economia', [
        'prenotazioni.models',
        'prenotazioni.views',
        'prenotazioni.forms',
        'prenotazioni.services',
        'prenotazioni.pricing',
        'prenotazioni.context_processors',
        'prenotazioni.admin',
        'prenotazioni.urls',
        'prenotazioni.management.commands.seed_demo_data',
        'prenotazioni.tests',
    ]),
]

MODULI_DA_DOCUMENTARE = [modulo for _, moduli in SEZIONI for modulo in moduli]

CARTELLA_OUTPUT = settings.BASE_DIR / 'documentazione'


def _etichetta(modulo):
    """Trasforma 'accounts.management.commands.elenca_utenti' in un'etichetta più
    leggibile per il link, es. 'management/commands/elenca_utenti'."""
    return modulo.split('.', 1)[1] if '.' in modulo else modulo


def _scrivi_indice(cartella_output):
    """Sovrascrive l'index.html generato da pdoc (un unico elenco alfabetico piatto)
    con una pagina scritta a mano, divisa per macrosettore: più semplice da consultare
    per chi non conosce già la struttura del progetto."""
    blocchi = []
    for titolo, moduli in SEZIONI:
        righe = '\n'.join(
            f'      <li><a href="{modulo.replace(".", "/")}.html">{_etichetta(modulo)}</a></li>'
            for modulo in moduli
        )
        blocchi.append(f'    <section>\n      <h2>{titolo}</h2>\n      <ul>\n{righe}\n      </ul>\n    </section>')

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="color-scheme" content="light">
    <title>Documentazione VSBA</title>
    <style>
        html {{ color-scheme: light; }}
        body {{ font-family: "Segoe UI", Arial, sans-serif; max-width: 720px; margin: 2.5rem auto; padding: 0 1.5rem; color: #24242a; background: #ffffff; }}
        h1 {{ margin-bottom: 0.2rem; color: #15151a; }}
        p.sottotitolo {{ color: #666; margin-top: 0; }}
        section {{ margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #e2e2e6; }}
        h2 {{ font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.03em; color: #15151a; }}
        ul {{ list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.3rem 1.5rem; }}
        li {{ overflow-wrap: break-word; }}
        a {{ color: #1533e6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Documentazione VSBA</h1>
    <p class="sottotitolo">Generata da pdoc a partire dalle docstring del codice, divisa per macrosettore.</p>
{chr(10).join(blocchi)}
</body>
</html>
"""
    (cartella_output / 'index.html').write_text(html, encoding='utf-8')


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
        _scrivi_indice(CARTELLA_OUTPUT)
        self.stdout.write(self.style.SUCCESS(f'Documentazione generata in {CARTELLA_OUTPUT}'))
