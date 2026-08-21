# Comandi da terminale

Guida di riferimento a tutti i comandi utili per lavorare su questo progetto: avvio rapido, `manage.py` e la sua suite completa di comandi, gestione del database, test.

Tutti i comandi Python vanno eseguiti **dentro l'ambiente virtuale del progetto**, quindi sempre come `pipenv run python manage.py ...` (oppure apri una shell con `pipenv shell` e poi lanciali senza il prefisso).

## Avvio rapido

Da Git Bash, nella cartella del progetto:

```bash
./run.sh
```

Installa `pipenv` se manca, installa le dipendenze, applica le migrazioni e avvia il server su `http://127.0.0.1:8000/`. Per fermarlo: `Ctrl+C` nel terminale dove gira, oppure (se è in background):

```bash
netstat -ano | grep ":8000" | grep LISTENING   # trova il PID
taskkill //F //PID <numero_pid>                # lo termina
```

In alternativa, un comando singolo equivalente a `run.sh`:

```bash
python -m pip install --user pipenv; python -m pipenv install; python -m pipenv run python manage.py migrate; python -m pipenv run python manage.py runserver 127.0.0.1:8000
```

## Setup iniziale

```bash
pipenv install                              # installa le dipendenze (Django) nel virtualenv
pipenv run python manage.py migrate         # crea/aggiorna le tabelle del database
pipenv run python manage.py seed_demo_data  # crea utenti e dati demo (vedi README.md per le credenziali)
```

## Comandi custom di questo progetto

| Comando | Cosa fa |
|---|---|
| `pipenv run python manage.py seed_demo_data` | Crea utenti demo (admin, gestori, clienti), prezzario iniziale, orari di apertura, servizi e un paio di prenotazioni di esempio. Idempotente, si può rilanciare senza duplicare nulla. |
| `pipenv run python manage.py elenca_utenti` | Interroga il database e stampa tutti gli utenti registrati con username, ruolo, email, data di registrazione e ultimo accesso. |
| `pipenv run python manage.py genera_documentazione` | Genera la documentazione HTML del progetto (dalle docstring, via pdoc) nella cartella `documentazione/`. Richiede `pipenv install --dev`. |

## `manage.py` — comandi Django più usati

| Comando | Cosa fa |
|---|---|
| `runserver` | Avvia il server di sviluppo locale (default `127.0.0.1:8000`). |
| `migrate` | Applica al database le migrazioni non ancora eseguite. |
| `makemigrations` | Genera nuove migrazioni dopo aver modificato i modelli (`models.py`). |
| `test` | Esegue l'intera suite di test del progetto. |
| `shell` | Apre una shell Python con l'app Django già caricata (utile per query manuali sul database). |
| `createsuperuser` | Crea un utente amministratore da terminale, con prompt interattivi. |
| `changepassword <username>` | Cambia la password di un utente da terminale. |
| `collectstatic` | Raccoglie tutti i file statici (CSS/JS/immagini) in un'unica cartella, per il deploy in produzione. |

Esempi:

```bash
pipenv run python manage.py runserver 127.0.0.1:8000
pipenv run python manage.py makemigrations
pipenv run python manage.py migrate
pipenv run python manage.py test
pipenv run python manage.py test struttura        # solo i test di un'app
pipenv run python manage.py shell
```

## `manage.py` — comandi meno comuni / diagnostica

| Comando | Cosa fa |
|---|---|
| `check` | Controlla il progetto per errori di configurazione, senza avviarlo. |
| `dbshell` | Apre il client SQL nativo del database configurato (SQLite in questo progetto). |
| `dumpdata` / `loaddata` | Esporta/importa i dati del database in formato JSON (backup o fixture). |
| `showmigrations` | Mostra quali migrazioni sono applicate e quali no. |
| `sqlmigrate <app> <numero>` | Mostra l'SQL che una migrazione eseguirebbe, senza eseguirlo. |
| `flush` | ⚠️ Svuota **tutte** le tabelle del database. Distruttivo, chiede conferma. |
| `diffsettings` | Mostra le differenze tra le impostazioni del progetto e quelle di default di Django. |
| `startapp <nome>` / `startproject <nome>` | Creano una nuova app / un nuovo progetto Django da zero. |
| `clearsessions` | Elimina le sessioni utente scadute. |
| `inspectdb` | Genera modelli Django a partire da un database già esistente. |
| `sendtestemail` | Invia un'email di prova (verifica la configurazione email). |
| `compilemessages` / `makemessages` | Gestione delle traduzioni (i18n). |
| `remove_stale_contenttypes` | Pulisce riferimenti a modelli ormai rimossi dal codice. |
| `optimizemigration` / `squashmigrations` | Ottimizzano o comprimono le migrazioni esistenti. |
| `createcachetable` | Crea la tabella per la cache basata su database. |
| `findstatic <file>` | Mostra da dove Django prenderebbe un dato file statico. |
| `sqlflush` / `sqlsequencereset` | Mostrano l'SQL per svuotare le tabelle / resettare i contatori auto-incrementali. |
| `testserver` | Avvia un server con dati di test caricati da una fixture. |

Elenco sempre aggiornato e specifico per questo progetto:

```bash
pipenv run python manage.py help
```

Dettagli su un comando specifico:

```bash
pipenv run python manage.py help <comando>
```

## Database

```bash
pipenv run python manage.py dbshell                 # apre una shell SQL sul db.sqlite3
pipenv run python manage.py dumpdata > backup.json   # backup completo in JSON
pipenv run python manage.py showmigrations           # stato delle migrazioni
```

Per ripartire da un database vuoto (⚠️ cancella `db.sqlite3` e perdi tutti i dati):

```bash
rm db.sqlite3
pipenv run python manage.py migrate
pipenv run python manage.py seed_demo_data
```

## Test

```bash
pipenv run python manage.py test                 # tutta la suite
pipenv run python manage.py test accounts         # solo l'app accounts
pipenv run python manage.py test struttura.tests.DisponibilitaTests   # una classe specifica
```

## Da dove vengono i comandi custom

Django cerca, in ogni app elencata in `INSTALLED_APPS`, una cartella `management/commands/`: ogni file `.py` lì dentro diventa automaticamente un comando col nome del file. In questo progetto:

- `prenotazioni/management/commands/seed_demo_data.py`
- `accounts/management/commands/elenca_utenti.py`
- `accounts/management/commands/genera_documentazione.py`

Per aggiungerne uno nuovo basta creare un altro file in una di queste cartelle (o in una nuova app), con una classe `Command(BaseCommand)` e un metodo `handle()`.
