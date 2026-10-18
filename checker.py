import hashlib
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Die Startseite des Standesamts Aabenra
START_URL = "https://reservation.frontdesksuite.com/aabenraavielse/vielse/Home/Index?pageid=9ac8c849-d203-47e2-94a1-173c7f471237&culture=de&uiculture=de"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
HASH_FILE = "last_hash.txt"

# SCHALTER: True = Sendet nach JEDER Prüfung eine Statusnachricht, False = Nur bei Änderungen
SEND_DEBUG_MESSAGE = True


def send_discord_message(message):
  if not DISCORD_WEBHOOK_URL:
    print("Discord Webhook URL fehlt!")
    return
  import requests

  payload = {"content": message}
  response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
  if response.status_code != 204:
    print(f"Fehler beim Senden an Discord: {response.text}")


def check_site():
  try:
    with sync_playwright() as p:
      # Startet einen unsichtbaren Browser
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()

      print(f"Öffne Startseite: {START_URL}")
      page.goto(START_URL, timeout=30000)

      # Suche und klicke auf den Button "Ja - wir bringen unsere eigenen Trauzeugen mit"
      # Wir suchen hier nach dem Text im Button
      print("Suche nach dem Trauzeugen-Button...")
      button = page.get_by_text(
          "Ja - wir bringen unsere eigenen Trauzeugen mit"
      )

      if button.count() > 0:
        button.first.click()
        # Warte, bis die Zielseite nach dem Klick geladen ist
        page.wait_for_load_state("networkidle")
        print("Erfolgreich geklickt, auf Zielseite angekommen.")
      else:
        print(
            "Warnung: Trauzeugen-Button nicht gefunden. Versuche Seite direkt"
            " zu überwachen."
        )

      # Aktuelle URL der Zielseite holen
      current_url = page.url
      print(f"Überwache Ziel-URL: {current_url}")

      # HTML der Zielseite auslesen
      html_content = page.content()
      browser.close()

      soup = BeautifulSoup(html_content, "html.parser")
      content = str(soup)

      # Erstelle einen Hash vom aktuellen Inhalt der Zielseite
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
        print("Änderung auf der Zielseite festgestellt!")
        send_discord_message(
            "🚨 **Achtung! Es gab eine Änderung auf der Standesamt-Zielseite von"
            f" Aabenra!**\nPrüfe die Seite sofort: {current_url}"
        )
        with open(HASH_FILE, "w") as f:
          f.write(current_hash)
      else:
        print("Keine Änderung der Zielseite.")

  except Exception as e:
    exception_msg = f"❌ Ein Fehler ist aufgetreten: {e}"
    print(exception_msg)
    if SEND_DEBUG_MESSAGE:
      send_discord_message(exception_msg)


if __name__ == "__main__":
  check_site()
