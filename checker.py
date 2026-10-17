import hashlib
import os
import requests
from bs4 import BeautifulSoup

# URL der Standesamt-Buchungsseite von Aabenra eintragen
URL = "HIER_DIE_EXAKTE_URL_DES_STANDISAMTS_EINTRAGEN"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
HASH_FILE = "last_hash.txt"


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
      print(f"Fehler: Webseite antwortet mit Status {response.status_code}")
      return

    soup = BeautifulSoup(response.text, "html.parser")

    # WICHTIG: Hier kannst du den Bereich eingrenzen (z.B. den Haupt-Container der Seite),
    # damit nicht wegen jeder kleinen Werbe-Änderung oder Uhrzeit in der Fußzeile Alarm geschlagen wird.
    # Wenn du die gesamte Seite willst, nimm einfach: content = str(soup)
    # Beispiel mit Container (suche im Browser nach der ID des Kalender-Bereichs, z.B. id="booking-container"):
    # target_area = soup.find("div", {"id": "booking-container"})
    # content = str(target_area) if target_area else str(soup)

    content = str(soup)  # Überwacht standardmäßig die gesamte Seite

    # Erstelle einen eindeutigen Hash (Prüfsumme) vom aktuellen Inhalt
    current_hash = hashlib.md5(content.encode("utf-8")).hexdigest()

    # Lade den alten Hash, falls die Datei existiert
    old_hash = ""
    if os.path.exists(HASH_FILE):
      with open(HASH_FILE, "r") as f:
        old_hash = f.read().strip()

    # Vergleiche alt und neu
    if old_hash == "":
      # Erster Lauf: Speichere den Hash einfach ab, ohne Alarm zu schlagen
      print(
          "Erster Lauf: Initialer Hash gespeichert. Überwachung aktiv ab dem"
          " nächsten Mal."
      )
      with open(HASH_FILE, "w") as f:
        f.write(current_hash)

    elif current_hash != old_hash:
      # ÄNDERUNG ERKANNT!
      print("Änderung auf der Webseite festgestellt!")
      send_discord_message(
          "🚨 **Achtung! Es gab eine Änderung auf der Standesamt-Seite von"
          f" Aabenra!**\nPrüfe die Seite sofort: {URL}"
      )

      # Speichere den neuen Hash für zukünftige Vergleiche
      with open(HASH_FILE, "w") as f:
        f.write(current_hash)
    else:
      print("Keine Änderung der Webseite.")

  except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
  check_site()
