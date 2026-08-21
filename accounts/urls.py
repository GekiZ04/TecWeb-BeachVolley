from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

# il namespace 'accounts' evita conflitti quando due app hanno un URL con lo stesso nome
# (es. 'nuova'): negli altri file si scrive {% url 'accounts:login' %} invece di solo 'login'
app_name = 'accounts'

urlpatterns = [
    path('registrati/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('utenti/', views.gestione_utenti, name='gestione_utenti'),
]
