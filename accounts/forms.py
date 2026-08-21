from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignupForm(UserCreationForm):
    """Form di registrazione, basato su quello standard di Django per creare utenti (che si
    occupa già di validare/confermare la password). Il ruolo non è tra i campi: non deve
    poterlo scegliere l'utente, lo imposta la view su self.role prima di chiamare save()."""
    role = None

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.role
        if commit:
            user.save()
        return user
