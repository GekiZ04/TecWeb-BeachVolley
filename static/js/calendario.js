// Gestisce lo scorrimento tra settimane nel calendario della home: intercetta i click sui
// link "settimana precedente/successiva" e, invece di seguire il link (che ricaricherebbe
// tutta la pagina), scarica via fetch solo il nuovo frammento di calendario e lo sostituisce.

document.addEventListener('DOMContentLoaded', function () {
    const wrapper = document.getElementById('calendario-wrapper');
    if (!wrapper) return;

    function carica(inizio, aggiornaUrl) {
        const url = wrapper.dataset.endpoint + '?inizio=' + encodeURIComponent(inizio);
        fetch(url)
            .then(function (res) { return res.text(); })
            .then(function (html) {
                wrapper.innerHTML = html;
                if (aggiornaUrl) {
                    const nuovaUrl = new URL(window.location);
                    nuovaUrl.searchParams.set('inizio', inizio);
                    history.pushState({ inizio: inizio }, '', nuovaUrl);
                }
            });
    }

    // i link "precedente/successiva" vengono rigenerati a ogni fetch (sono dentro
    // l'HTML che sostituiamo), quindi il listener va messo sul wrapper (che resta sempre
    // lo stesso elemento) e non sui singoli link
    wrapper.addEventListener('click', function (e) {
        const link = e.target.closest('.calendario-nav');
        if (!link) return;
        e.preventDefault();
        carica(link.dataset.inizio, true);
    });

    // così anche i pulsanti avanti/indietro del browser funzionano dopo aver scorso le settimane
    window.addEventListener('popstate', function () {
        const params = new URLSearchParams(window.location.search);
        carica(params.get('inizio') || '', false);
    });
});
