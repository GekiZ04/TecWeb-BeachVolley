from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Estende l'admin utenti di Django col campo "role" personalizzato, così è modificabile
    anche da /django-admin/ e non solo dalla pagina "Gestione utenti" pensata per l'admin
    della struttura."""
    fieldsets = UserAdmin.fieldsets + (
        ('Ruolo struttura', {'fields': ('role',)}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')
    list_filter = ('role', 'is_staff')
