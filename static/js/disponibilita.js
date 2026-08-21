// Gestisce il menù a tendina degli orari nelle pagine di prenotazione (nuova.html e
// modifica.html): scarica gli slot disponibili via fetch senza ricaricare la pagina,
// popola il menù, e mostra il pannello giusto (prenotazione o lista d'attesa) a seconda
// che lo slot scelto sia libero o occupato.

const DURATA_STEP_MINUTI = 15;
const DURATA_DEFAULT_MINUTI = 60;
const DURATA_MASSIMA_MINUTI = 240; // 4 ore

// Riempie il menù "Orario" con gli slot ricevuti dal server. Gli slot "chiuso" (fuori
// orario o coperti da una chiusura straordinaria) non li mostro proprio: non avrebbe
// senso poterli selezionare.
function popolaOrari(select, slots) {
    select.innerHTML = '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = slots.length ? 'Seleziona un orario' : 'Campo chiuso in questa data';
    placeholder.disabled = true;
    placeholder.selected = true;
    select.appendChild(placeholder);

    slots.forEach(function (slot) {
        if (slot.stato === 'chiuso') return;
        const opt = document.createElement('option');
        opt.value = slot.ora_inizio;
        opt.textContent = slot.ora_inizio + ' - ' + slot.ora_fine + (slot.stato === 'occupato' ? ' (occupato)' : '');
        select.appendChild(opt);
    });
}

// Conta quanti quarti d'ora liberi ci sono uno dopo l'altro a partire dallo slot scelto —
// mi serve per sapere fin dove ci si può allungare senza "scavalcare" uno slot occupato.
function minutiLiberiConsecutivi(slots, indice) {
    let count = 0;
    for (let i = indice; i < slots.length; i++) {
        if (slots[i].stato !== 'libero') break;
        count++;
    }
    return count * DURATA_STEP_MINUTI;
}

// Trasforma un numero di minuti in un'etichetta leggibile, es. 90 -> "1h 30min".
function formattaDurata(minuti) {
    const ore = Math.floor(minuti / 60);
    const resto = minuti % 60;
    if (ore && resto) return ore + 'h ' + resto + 'min';
    if (ore) return ore + 'h';
    return resto + 'min';
}

// Riempie il menù "Durata" con le opzioni valide (multipli di 15 minuti fino al massimo
// consentito). Se c'è una durata preferita la seleziona — usato dalla pagina di modifica
// per preselezionare la durata della prenotazione che si sta cambiando.
function popolaDurate(select, maxMinuti, durataPreferita) {
    select.innerHTML = '';
    for (let m = DURATA_STEP_MINUTI; m <= maxMinuti; m += DURATA_STEP_MINUTI) {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = formattaDurata(m);
        select.appendChild(opt);
    }
    if (!select.options.length) return;
    const preferita = durataPreferita && durataPreferita <= maxMinuti ? durataPreferita : DURATA_DEFAULT_MINUTI;
    const opzioneDefault = Array.from(select.options).find(function (o) { return parseInt(o.value, 10) === preferita; });
    select.value = opzioneDefault ? preferita : select.options[select.options.length - 1].value;
}

// Somma ora di inizio + durata e ritorna l'ora di fine come stringa "HH:MM". Con % 24,
// se il totale arriva esattamente a mezzanotte (1440 minuti) l'ora torna a 0 invece di
// stampare un errato "24:00".
function calcolaOraFine(oraInizio, durataMinuti) {
    const [h, m] = oraInizio.split(':').map(Number);
    const totale = h * 60 + m + parseInt(durataMinuti, 10);
    const hh = Math.floor(totale / 60) % 24;
    const mm = totale % 60;
    return String(hh).padStart(2, '0') + ':' + String(mm).padStart(2, '0');
}

// Ricalcola l'ora di fine in base alla durata scelta, e aggiorna sia l'etichetta a
// schermo sia il campo nascosto ora_fine che poi verrà inviato col form.
function aggiornaOraFineESlotLabel(panel, data) {
    const select = panel.querySelector('[name=durata_minuti]');
    const oraInizio = panel.querySelector('[name=ora_inizio]').value;
    if (!select.value || !oraInizio) return;
    const oraFine = calcolaOraFine(oraInizio, select.value);
    panel.querySelector('[name=ora_fine]').value = oraFine;
    panel.querySelector('.slot-label').textContent = data + ' ' + oraInizio + '-' + oraFine;
    aggiornaAnteprimaPrezzo(panel);
}

// La funzione principale: parte ogni volta che si sceglie un orario dal menù (o quando
// la pagina preseleziona uno slot da sola) e mostra il pannello giusto — prenotazione
// se lo slot è libero, lista d'attesa se è occupato — preparandolo con i dati corretti.
function gestisciSelezioneOrario(container, data, slots, durataIniziale) {
    const select = container.querySelector('.orario-select');
    const scelto = select.value;
    const panelPrenota = document.getElementById('form-prenota');
    const panelAttesa = document.getElementById('form-attesa');

    if (!scelto) {
        panelPrenota && panelPrenota.classList.add('hidden');
        panelAttesa && panelAttesa.classList.add('hidden');
        return;
    }

    const indice = slots.findIndex(function (s) { return s.ora_inizio === scelto; });
    if (indice === -1) return;
    const slot = slots[indice];

    if (slot.stato === 'libero' && panelPrenota) {
        panelAttesa && panelAttesa.classList.add('hidden');
        panelPrenota.classList.remove('hidden');
        panelPrenota.querySelector('[name=data]').value = data;
        panelPrenota.querySelector('[name=ora_inizio]').value = slot.ora_inizio;

        const maxMinuti = Math.min(DURATA_MASSIMA_MINUTI, minutiLiberiConsecutivi(slots, indice));
        const durataSelect = panelPrenota.querySelector('[name=durata_minuti]');
        popolaDurate(durataSelect, maxMinuti, durataIniziale);
        aggiornaOraFineESlotLabel(panelPrenota, data);
    } else if (slot.stato === 'occupato' && panelAttesa) {
        panelPrenota && panelPrenota.classList.add('hidden');
        panelAttesa.classList.remove('hidden');
        panelAttesa.querySelector('[name=data]').value = data;
        panelAttesa.querySelector('[name=ora_inizio]').value = slot.ora_inizio;
        panelAttesa.querySelector('[name=ora_fine]').value = slot.ora_fine;
        panelAttesa.querySelector('.slot-label').textContent = data + ' ' + slot.ora_inizio + '-' + slot.ora_fine;
    }
}

// Chiede al server il prezzo per la combinazione attuale di orario/durata/spogliatoio/
// partecipanti (senza ricaricare la pagina) e aggiorna l'anteprima a schermo.
function aggiornaAnteprimaPrezzo(panel) {
    const endpoint = panel.dataset.prezzoEndpoint;
    const oraInizio = panel.querySelector('[name=ora_inizio]').value;
    const oraFine = panel.querySelector('[name=ora_fine]').value;
    if (!oraInizio || !oraFine || !endpoint) return;
    const spogliatoio = panel.querySelector('[name=spogliatoio]').checked;
    const partecipanti = panel.querySelector('[name=numero_partecipanti]').value || 1;
    const url = endpoint + '?ora_inizio=' + oraInizio + '&ora_fine=' + oraFine +
        '&spogliatoio=' + spogliatoio + '&partecipanti=' + partecipanti;
    fetch(url)
        .then(function (res) { return res.json(); })
        .then(function (payload) {
            if (payload.prezzo) {
                panel.querySelector('.price-preview').textContent = '€ ' + payload.prezzo;
            }
        });
}

document.addEventListener('DOMContentLoaded', function () {
    // in pratica c'è un solo "selettore data + orario" per pagina, ma il codice
    // funziona comunque anche se in futuro ce ne fosse più di uno
    document.querySelectorAll('.prenota-picker').forEach(function (container) {
        const input = container.querySelector('.data-input');
        const select = container.querySelector('.orario-select');
        let slotsCorrenti = []; // ultima risposta ricevuta dal server, riusata al cambio orario

        function carica(data) {
            const endpoint = container.dataset.endpoint;
            const escludi = container.dataset.escludiPrenotazione ? '&escludi=' + container.dataset.escludiPrenotazione : '';
            return fetch(endpoint + '?data=' + encodeURIComponent(data) + escludi)
                .then(function (res) { return res.json(); })
                .then(function (payload) {
                    slotsCorrenti = payload.slots;
                    popolaOrari(select, slotsCorrenti);
                    return payload;
                });
        }

        // al caricamento, se c'è un orario da preselezionare (data-prefill-*, usato dalla
        // pagina di modifica o quando si arriva da un click sul calendario in home) lo
        // seleziono da solo appena gli slot sono pronti, aprendo già il pannello giusto
        carica(container.dataset.data).then(function () {
            if (container.dataset.prefillOraInizio) {
                const durataIniziale = container.dataset.prefillDurataMinuti
                    ? parseInt(container.dataset.prefillDurataMinuti, 10) : undefined;
                select.value = container.dataset.prefillOraInizio;
                gestisciSelezioneOrario(container, container.dataset.data, slotsCorrenti, durataIniziale);
                const panelPrenota = document.getElementById('form-prenota');
                if (panelPrenota && container.dataset.prefillSpogliatoio) {
                    panelPrenota.querySelector('[name=spogliatoio]').checked = container.dataset.prefillSpogliatoio === 'true';
                }
                if (panelPrenota && container.dataset.prefillPartecipanti) {
                    panelPrenota.querySelector('[name=numero_partecipanti]').value = container.dataset.prefillPartecipanti;
                }
                panelPrenota && aggiornaAnteprimaPrezzo(panelPrenota);
            }
        });

        // al cambio data ricarico gli slot e nascondo i pannelli già aperti, che
        // potrebbero riferirsi a uno slot del giorno precedente
        input && input.addEventListener('change', function () {
            container.dataset.data = input.value;
            carica(input.value);
            const panelPrenota = document.getElementById('form-prenota');
            const panelAttesa = document.getElementById('form-attesa');
            panelPrenota && panelPrenota.classList.add('hidden');
            panelAttesa && panelAttesa.classList.add('hidden');
        });

        select.addEventListener('change', function () {
            gestisciSelezioneOrario(container, container.dataset.data, slotsCorrenti);
        });
    });

    // ricalcolo il prezzo ogni volta che cambia spogliatoio, partecipanti o durata
    const panelPrenota = document.getElementById('form-prenota');
    if (panelPrenota) {
        const spogliatoio = panelPrenota.querySelector('[name=spogliatoio]');
        const partecipanti = panelPrenota.querySelector('[name=numero_partecipanti]');
        const durata = panelPrenota.querySelector('[name=durata_minuti]');
        const data = panelPrenota.querySelector('[name=data]');
        spogliatoio && spogliatoio.addEventListener('change', function () { aggiornaAnteprimaPrezzo(panelPrenota); });
        partecipanti && partecipanti.addEventListener('input', function () { aggiornaAnteprimaPrezzo(panelPrenota); });
        durata && durata.addEventListener('change', function () { aggiornaOraFineESlotLabel(panelPrenota, data.value); });
    }
});
