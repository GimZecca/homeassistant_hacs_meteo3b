# 3bMeteo — Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Integrazione non ufficiale per [3bMeteo](https://www.3bmeteo.com) che porta le previsioni meteo italiane in Home Assistant.

> **Disclaimer:** This is an unofficial integration, not affiliated with or endorsed by 3bMeteo.
> Intended for personal, non-commercial use only. Use at your own risk.

---

## Funzionalità

- **Entità `weather`** con:
  - Condizioni meteo correnti (temperatura, umidità, pressione, vento)
  - **Previsioni orarie** fino a 7 giorni
  - **Previsioni giornaliere** fino a 7 giorni
- **12 sensori** dedicati:

  | Sensore | Unità |
  |---|---|
  | Temperatura attuale | °C |
  | Temperatura percepita | °C |
  | Temperatura min/max oggi | °C |
  | Umidità | % |
  | Pressione | hPa |
  | Velocità vento | km/h |
  | Condizione meteo | testo |
  | Indice UV | numero |
  | Attendibilità previsione | testo |
  | Alba / Tramonto | ora |
  | Precipitazioni oggi | mm |

---

## Installazione via HACS

Clicca il pulsante per aggiungere automaticamente il repository:

[![Open your Home Assistant instance and add this repository.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GimZecca&repository=homeassistant_hacs_meteo3b&category=integration)

Oppure manualmente:

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. Aggiungi l'URL di questo repo, categoria **Integration**
3. Cerca **3bMeteo** e clicca **Download**
4. Riavvia Home Assistant
   
## Installazione manuale

1. Copia la cartella `custom_components/meteo3b/` in `config/custom_components/`
2. Riavvia Home Assistant

---

## Configurazione

1. **Impostazioni** → **Dispositivi e Servizi** → **Aggiungi Integrazione** → cerca **3bMeteo**
2. Digita il nome della località (es. `Milano`, `Roma`)
3. Seleziona la località corretta dalla lista
4. Conferma

La ricerca avviene live tramite l'API di 3bMeteo — non serve conoscere alcun ID.

### Inserimento manuale (opzionale)

Se preferisci, puoi inserire direttamente l'ID località e l'ID settore
restituiti dalla ricerca.

---

## Aggiornamento dati

Le previsioni si aggiornano ogni **15 minuti**.

---

## Note legali

Questa integrazione è destinata esclusivamente all'uso personale e non commerciale.
Non è affiliata né approvata da 3bMeteo. Utilizza a tuo rischio e pericolo.

---

## Contribuire

Pull request benvenute. Per segnalare problemi apri una issue su GitHub.

## Licenza

MIT — vedi [LICENSE](LICENSE).
