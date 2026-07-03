"""Costanti per l'integrazione 3bMeteo."""

DOMAIN = "meteo3b"

# Endpoint API
BASE_URL = "https://api.3bmeteo.com/mobilev3/"

# Chiave usata dall'app ufficiale per autenticare le chiamate.
# Ottenuta tramite reverse engineering dell'APK Android (com.Meteosolutions.Meteo3b).
# A differenza di ilMeteo, questa chiave è statica (non ruota giornalmente).
API_KEY = "TVIBVd7cmCagdU3uob6Mof1hI9yM48scSSYZVrnw"

LANGUAGE = "it"

# Numero di giorni di previsione da richiedere all'API
FORECAST_DAYS = 7

# Update interval in minuti
UPDATE_INTERVAL_MINUTES = 15

# Storage
STORAGE_VERSION = 1
