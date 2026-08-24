# VSBA (Volley Sassuolo Beach Arena)

Progetto d'esame per il corso di Tecnologie Web. Ho realizzato un sito per gestire le prenotazioni di un campo da beach volley, ispirato al vero "Volley Sassuolo Beach Arena" di Sassuolo. È fatto con Django, mentre la parte di calendario e disponibilità è dinamica grazie a un po' di JavaScript, senza framework aggiuntivi.

Ho fatto in modo che le prenotazioni non fossero bloccate all'ora esatta. Si può iniziare a qualsiasi quarto d'ora e scegliere una durata a piacere, da 15 minuti a 4 ore, sempre in multipli di 15 minuti, e il prezzo viene calcolato in proporzione. Se una prenotazione attraversa le 18:00, il costo viene diviso automaticamente tra tariffa diurna e serale.

Per la grafica ho usato il logo, le foto del campo e lo sfondo che si trovano in `static/img/`. Li ho presi dal sito ufficiale [volleysassuolo.com](https://volleysassuolo.com), nella sezione Beach Arena.

## Chi può fare cosa

Ho previsto quattro livelli di accesso.

Un visitatore non registrato può consultare disponibilità, orari, servizi e prezzario, ma non può prenotare.

Un cliente può prenotare, modificare o cancellare le proprie prenotazioni, consultare lo storico, mettersi in lista d'attesa se uno slot è occupato e ricevere notifiche all'interno del sito.

Un gestore, di cui può essercene più di uno, si occupa di orari di apertura, prezzario, chiusure straordinarie e servizi. Le prenotazioni vengono assegnate automaticamente al gestore che ne ha in carico di meno, così il lavoro si distribuisce da solo.

Un admin ha tutte le funzioni di un gestore, oltre alla parte economica: vede la propria quota (il 60% dell'incassato), può generare il resoconto settimanale diviso per gestore e può applicare uno sconto a una prenotazione specifica, visibile solo al cliente coinvolto.

## Come avviarlo

Serve Python 3.12 e pipenv (si installa con `pip install pipenv`).

```bash
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py seed_demo_data
pipenv run python manage.py runserver
```

Il sito sarà raggiungibile su http://127.0.0.1:8000/.

In alternativa, da terminale (Git Bash su Windows, oppure il Terminale su Mac e Linux) si può usare lo script `./run.sh`, che esegue tutti questi passaggi in automatico. L'elenco completo dei comandi utili è nel file [COMANDI.md](COMANDI.md).

## Credenziali per provare il sito

Vengono create dal comando `seed_demo_data`, che può essere rilanciato quante volte serve senza creare duplicati.

| Ruolo    | Username   | Password       |
|----------|------------|----------------|
| Admin    | `admin`     | `admin12345`    |
| Gestore  | `gestore1`  | `gestore12345`  |
| Gestore  | `gestore2`  | `gestore12345`  |
| Cliente  | `cliente1`  | `cliente12345`  |
| Cliente  | `cliente2`  | `cliente12345`  |
| Capodieci| `capodieci` | `nicola`        |
| Zanini   | `zanini`    | `giacomo`       |

Lo stesso comando crea anche il prezzario, gli orari di apertura (tutti i giorni dalle 08:00 alle 00:00) e un paio di servizi, oltre a due prenotazioni di esempio per il giorno successivo. In questo modo, appena si apre il sito, si trova già uno slot occupato ed è possibile provare subito la lista d'attesa e il resoconto economico.

## Test

```bash
pipenv run python manage.py test
```

## Struttura del progetto

Il progetto è diviso in tre app Django, ciascuna con una propria responsabilità.

L'app `accounts` gestisce l'utente personalizzato con i tre ruoli, la registrazione e il login/logout.

L'app `struttura` si occupa di tutto ciò che riguarda il campo: orari, chiusure straordinarie, prezzario e calcolo degli slot disponibili.

L'app `prenotazioni` gestisce le prenotazioni vere e proprie, la lista d'attesa, le notifiche, il calcolo dei prezzi e la dashboard economica.

## Documentazione del codice

```bash
pipenv run python manage.py genera_documentazione
```

Questo comando legge le docstring presenti nel codice e genera una documentazione HTML navigabile, tramite [pdoc](https://pdoc.dev/), nella cartella `documentazione/`. Basta aprire `documentazione/index.html` per consultarla.

## Note

Il progetto è pensato per girare solo in locale, sul mio computer: non c'è nessuna configurazione per pubblicarlo online.

La `SECRET_KEY` è scritta in chiaro in `beachvolley/settings.py` e `DEBUG = True`: per un sito che gira solo in locale va bene così.

Le password demo, come `admin12345`, sono volutamente semplici per rendere più rapidi i test.
