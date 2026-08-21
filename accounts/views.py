from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SignupForm
from .models import User
from .permissions import admin_required


def signup(request):
    """Registrazione pubblica. Chiunque può crearsi un account, ma sempre come cliente:
    il ruolo gestore non si può scegliere qui, deve assegnarlo un admin in un secondo
    momento (altrimenti chiunque potrebbe registrarsi come gestore della struttura)."""
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            form.role = User.Ruolo.CLIENTE
            user = form.save()
            login(request, user)  # loggo subito l'utente appena creato, per comodità
            return redirect('home')
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


@admin_required
def gestione_utenti(request):
    """Pagina riservata all'admin, per passare un utente da cliente a gestore (o viceversa).

    Un admin non è mai modificabile da qui, nemmeno da un altro admin: senza questo
    controllo basterebbe un errore per lasciare la struttura senza amministratori.
    """
    if request.method == 'POST':
        utente = get_object_or_404(User, pk=request.POST.get('user_id'))
        nuovo_ruolo = request.POST.get('ruolo')
        if utente.role == User.Ruolo.ADMIN or nuovo_ruolo not in (User.Ruolo.CLIENTE, User.Ruolo.GESTORE):
            messages.error(request, 'Operazione non consentita.')
        else:
            utente.role = nuovo_ruolo
            utente.save()
            messages.success(request, f'{utente.username} ora è {utente.get_role_display()}.')
        return redirect('accounts:gestione_utenti')

    # gli admin non compaiono in elenco: da questa pagina non devono essere "toccabili"
    utenti = User.objects.exclude(role=User.Ruolo.ADMIN).order_by('username')
    return render(request, 'accounts/gestione_utenti.html', {'utenti': utenti})
