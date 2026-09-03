from django.contrib import admin

from .models import Campo, ChiusuraStraordinaria, OrarioApertura, Servizio, Tariffa

# Registrazione base, senza personalizzazioni, su /django-admin/: comoda ad avere per il
# superuser, anche se nel quotidiano si usa la dashboard gestore fatta apposta.
admin.site.register(Campo)
admin.site.register(Servizio)
admin.site.register(OrarioApertura)
admin.site.register(ChiusuraStraordinaria)
admin.site.register(Tariffa)
