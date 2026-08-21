def notifiche(request):
    """Context processor registrato in settings.py: rende "notifiche_non_lette"
    disponibile in tutti i template senza doverla passare a mano da ogni view. Mi serve
    per il badge con il numero di notifiche nella navbar (templates/base.html)."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    return {'notifiche_non_lette': user.notifiche.filter(letta=False).count()}
