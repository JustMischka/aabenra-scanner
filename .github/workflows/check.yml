import hashlib
import os
import requests
from bs4 import BeautifulSoup

# URL der Standesamt-Buchungsseite von Aabenra eintragen
URL = "HIER_DIE_EXAKTE_URL_DES_STANDISAMTS_EINTRAGEN"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
HASH_FILE = "last_hash.txt"

# SCHALTER: True = Sendet nach JEDER Prüfung eine Statusnachricht, False = Nur bei Änderungen
SEND_DEBUG_MESSAGE = True


def send_discord_message(message):
  if not DISCORD_WEBHOOK_URL:
    print("Discord Webhook URL fehlt!")
    return
  payload = {"content": message}
  response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
  if response.status_code != 204:
    print(f"Fehler beim Senden an Discord: {response.text}")


def check_site():
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/120.0.0.0 Safari/537.36"
      )
  }

  try:
    response = requests.get(URL, headers=headers, timeout=15)
    if response.status_code != 200:
      error_msg = (
          "⚠️ **Achtung! Standesamt-Seite antwortet mit Fehler:**"
          f" {response.status_code}"
      )
      print(error_msg)
      if SEND_DEBUG_MESSAGE:
        send_discord_message(error_msg)
      return

    soup = BeautifulSoup(response.text, "html.parser")
    content = str(soup)  # Überwacht die gesamte Seite

    # Erstelle einen Hash vom aktuellen Inhalt
    current_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

    # Lade den alten Hash, falls vorhanden
    old_hash = ""
    if os.path.exists(HASH_FILE):
      with open(HASH_FILE, "r") as f:
        old_hash = f.read().strip()

    # Immer-Nachricht senden, falls aktiviert
    if SEND_DEBUG_MESSAGE:
      send_discord_message("-------------------Seite wird geprüft------------------")

    # Vergleiche alt und neu
    if old_hash == "":
      print(
          "Erster Lauf: Initialer Hash gespeichert. Überwachung aktiv ab dem"
          " nächsten Mal."
      )
      with open(HASH_FILE, "w") as f:
        f.write(current_hash)

    elif current_hash != old_hash:
      print("Änderung auf der Webseite festgestellt!")
      send_discord_message(
          "🚨 **Achtung! Es gab eine Änderung auf der Standesamt-Seite von"
          f" Aabenra!**\nPrüfe die Seite sofort: {URL}"
      )
      # Speichere den neuen Hash
      with open(HASH_FILE, "w") as f:
        f.write(current_hash)
    else:
      print("Keine Änderung der Webseite.")

  except Exception as e:
    exception_msg = f"❌ Ein Fehler ist aufgetreten: {e}"
    print(exception_msg)
    if SEND_DEBUG_MESSAGE:
      send_discord_message(exception_msg)


if __name__ == "__main__":
  check_site()
