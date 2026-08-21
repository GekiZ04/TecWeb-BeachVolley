"""
Settings di Django per il progetto "beachvolley" (Volley Sassuolo Beach Arena).

File generato da 'django-admin startproject' e poi adattato per il progetto d'esame.
Doc ufficiale se serve: https://docs.djangoproject.com/en/5.2/topics/settings/
"""

from pathlib import Path

# Cartella principale del progetto (quella con manage.py), così tutti gli altri percorsi
# si costruiscono da qui invece di essere scritti a mano.
BASE_DIR = Path(__file__).resolve().parent.parent


# Chiave che Django usa per firmare sessioni, cookie, token CSRF ecc. Di solito si tiene
# fuori dal repository, ma per un progetto d'esame che gira solo sul mio pc non vale la
# pena complicarsi la vita con file .env: se mai dovesse finire online per davvero,
# andrebbe rigenerata.
SECRET_KEY = 'django-insecure-cth4gk!8c3@(q&9f$@^m+s+!nm#u9nridxb9b2u7b%qd-gc$lt'

DEBUG = True  # in sviluppo tenerlo acceso aiuta parecchio a leggere gli errori

# '*' accetta richieste con qualunque Host. Mi serve perché ogni tanto condivido il sito
# in locale con un tunnel SSH (localhost.run), che lo espone con un dominio diverso ogni volta.
ALLOWED_HOSTS = ['*']

# Senza questa riga, quando il sito passa dal tunnel (che è in HTTPS), Django rifiuta i
# form POST — login, prenotazioni, ecc. — con un errore "Origin checking failed".
CSRF_TRUSTED_ORIGINS = ['https://*.lhr.life']


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',      # utenti, ruoli, login/registrazione
    'struttura',     # campo, orari, prezzario, servizi
    'prenotazioni',  # prenotazioni, lista d'attesa, notifiche, economia
]

# Uso il modello utente custom (accounts.User) al posto di quello di default di Django,
# perché mi serve il campo "role" per distinguere cliente/gestore/admin.
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'beachvolley.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # aggiunge il numero di notifiche non lette in ogni pagina, per il badge in navbar
                'prenotazioni.context_processors.notifiche',
            ],
        },
    },
]

WSGI_APPLICATION = 'beachvolley.wsgi.application'


# SQLite: niente server da installare a parte, e per un progetto di queste dimensioni
# va benissimo. Il file db.sqlite3 viene creato nella root del progetto (escluso da git).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# I 4 validator standard di Django per le password in registrazione (niente password
# troppo simili ai dati dell'utente, lunghezza minima, non tra le più comuni, non solo numeri).
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'it-it'
TIME_ZONE = 'Europe/Rome'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Dove mandare chi non è loggato, e dove riportarlo dopo login/logout.
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
