"""Decorator per proteggere le view in base al ruolo dell'utente loggato.

Sono solo un sottile involucro attorno a user_passes_test di Django: se il controllo
fallisce, l'utente finisce rediretto alla pagina di login.
"""

from django.contrib.auth.decorators import user_passes_test


def _is_gestore_or_admin(user):
    return user.is_authenticated and user.is_gestore_or_admin


def _is_admin(user):
    return user.is_authenticated and user.is_admin_struttura


def _is_cliente(user):
    return user.is_authenticated and user.is_cliente


def gestore_or_admin_required(view_func):
    """Solo gestori e admin, es. per l'area gestore della struttura."""
    return user_passes_test(_is_gestore_or_admin, login_url='accounts:login')(view_func)


def admin_required(view_func):
    """Solo l'admin, es. per la pagina economia e la gestione utenti."""
    return user_passes_test(_is_admin, login_url='accounts:login')(view_func)


def cliente_required(view_func):
    """Solo i clienti, es. per creare una prenotazione."""
    return user_passes_test(_is_cliente, login_url='accounts:login')(view_func)
