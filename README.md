# VSBA — Volley Sassuolo Beach Arena

Progetto d'esame per il corso di Tecnologie Web: un sito per gestire le prenotazioni di un campo da beach volley, ispirato al vero "Volley Sassuolo Beach Arena" di Sassuolo. È fatto con Django, e la parte di calendario/disponibilità è dinamica con javascript.

Una cosa a cui tenevo particolarmente: le prenotazioni non sono bloccate all'ora esatta. Si può iniziare a qualsiasi quarto d'ora e scegliere una durata a piacere (da 15 minuti a 4 ore, sempre in multipli di 15), e il prezzo si calcola proporzionalmente. Se una prenotazione attraversa le 18:00 viene addirittura spezzata automaticamente tra tariffa diurna e serale.

**Sulla grafica**: logo, foto del campo e sfondo in `static/img/` li ho presi dal sito ufficiale [volleysassuolo.com](https://volleysassuolo.com) (sezione Beach Arena).

## Chi può fare cosa

- **Visitatore non registrato**: può solo guardare disponibilità, orari, servizi, prezzario.
- **Cliente**: prenota, modifica o cancella le proprie prenotazioni, vede lo storico, si mette in lista d'attesa se uno slot è occupato e riceve notifiche dentro al sito.
- **Gestore** (ce ne può essere più di uno): gestisce orari di apertura, prezzario, chiusure straordinarie e servizi. Le prenotazioni vengono assegnate in automatico al gestore che ne ha meno in carico, così il lavoro si distribuisce da solo.
- **Admin**: fa tutto quello che fa un gestore, più la parte economica vede la propria quota (40% dell'incassato), il resoconto settimanale diviso per gestore, e può applicare uno sconto a una prenotazione specifica (visibile solo al cliente coinvolto, non agli altri).

## Come avviarlo

Python 3.12 e [pipenv](https://pipenv.pypa.io/) (`pip install pipenv`).

```bash
pipenv install
pipenv run python manage.py migrate
pipenv run python manage.py seed_demo_data
pipenv run python manage.py runserver
```

Poi il sito è su http://127.0.0.1:8000/.

Se preferisci, da Git Bash c'è anche `./run.sh` che fa tutto questo da solo. Per l'elenco di tutti i comandi utili  **[COMANDI.md](COMANDI.md)**.

## Credenziali per provare il sito

Le crea `seed_demo_data` (si può rilanciare quante volte si vuole, non duplica niente):

| Ruolo    | Username   | Password       |
|----------|------------|----------------|
| Admin    | `admin`     | `admin12345`    |
| Gestore  | `gestore1`  | `gestore12345`  |
| Gestore  | `gestore2`  | `gestore12345`  |
| Cliente  | `cliente1`  | `cliente12345`  |
| Cliente  | `cliente2`  | `cliente12345`  |

Lo stesso comando riempie anche il prezzario, gli orari (tutti i giorni 08:00–00:00) e un paio di servizi, e crea due prenotazioni di esempio per il giorno dopo — così appena apri il sito trovi già uno slot occupato, puoi provare la lista d'attesa e c'è già qualcosa nel resoconto economico, senza doverlo configurare a mano.

## Test

```bash
pipenv run python manage.py test
```

## Struttura del progetto

Tre app Django, divise per responsabilità:

- `accounts/` — l'utente custom con i tre ruoli, registrazione, login/logout.
- `struttura/` — tutto ciò che riguarda il campo in sé: orari, chiusure straordinarie, prezzario, calcolo di quali slot sono liberi.
- `prenotazioni/` — le prenotazioni vere e proprie, lista d'attesa, notifiche, calcolo dei prezzi, dashboard economica.

## Documentazione del codice

```bash
pipenv run python manage.py genera_documentazione
```

Legge le docstring sparse nel codice e genera una documentazione HTML navigabile (uso [pdoc](https://pdoc.dev/) sotto il cofano) dentro `documentazione/` — basta aprire `documentazione/index.html`.

## Note di sicurezza

Alcune scelte fatte per comodità in locale, da NON portarsi dietro se questo diventasse mai un progetto vero:

- La `SECRET_KEY` è scritta in chiaro in `beachvolley/settings.py`. Per un progetto d'esame che gira solo sul mio PC va benissimo così, ma in un deploy reale andrebbe rigenerata e tenuta fuori dal repository.
- `DEBUG = True` e `ALLOWED_HOSTS = ['*']` (sempre in `settings.py`) servono a poter condividere il sito in locale, ad esempio con un tunnel SSH per farlo vedere a qualcuno senza deployarlo davvero. Da restringere se il sito restasse online stabilmente.
- Le password demo (`admin12345` ecc.) sono volutamente semplici, giusto per fare prima durante i test.
