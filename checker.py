import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Die Startseite des Standesamts Aabenra
START_URL = "https://reservation.frontdesksuite.com/aabenraavielse/vielse/Home/Index?pageid=9ac8c849-d203-47e2-94a1-173c7f471237&culture=de&uiculture=de"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

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
      browser = p.chromium.launch(headless=True)
      page = browser.new_page()

      print(f"Öffne Startseite: {START_URL}")
      page.goto(START_URL, timeout=30000)

      # Klicke auf den Trauzeugen-Button
      print("Suche nach dem Trauzeugen-Button...")
      button = page.get_by_text(
          "Ja - wir bringen unsere eigenen Trauzeugen mit"
      )

      if button.count() > 0:
        button.first.click()
        page.wait_for_load_state("networkidle")
        print("Erfolgreich geklickt, auf Zielseite angekommen.")
      else:
        print("Warnung: Trauzeugen-Button nicht gefunden.")

      current_url = page.url
      html_content = page.content()
      browser.close()

      soup = BeautifulSoup(html_content, "html.parser")

      # 1. Alle Datumszeilen und Statusmeldungen auslesen
      # Laut Screenshot stehen die Daten in Überschriften/Blöcken und daneben "Keine freien Termine"
      page_text = soup.get_text()

      # Wir suchen nach allen Wochentagen / Daten im Text (z.B. "Donnerstag, 22. Oktober 2026")
      # Oder wir zählen, wie oft "Keine freien Termine" vorkommt vs. ob es andere Buttons gibt.
      
      # Prüfen, ob das Wort "Keine freien Termine" fehlt oder ob es eine positive Änderung gibt
      # Alternativ: Wir prüfen, ob sich die Liste der gefundenen Termine geändert hat.
      
      # Lassen wir uns alle gefundenen Datums-ähnlichen Strings oder den Text ausgeben
      # Für den Anfang prüfen wir, ob irgendwo der Text "Keine freien Termine" NICHT mehr steht
      # oder ob ein Buchungs-Button ("Buchen", "Wählen" etc.) auftaucht.

      # Lassen wir uns den aktuellen Status per Debug ausgeben:
      print("Seite erfolgreich ausgelesen.")

      # Immer-Nachricht für Discord (kann später auf False gestellt werden)
      if SEND_DEBUG_MESSAGE:
        send_discord_message("-------------------Seite wird geprüft------------------")

      # Hier bauen wir jetzt die smarte Logik ein:
      # Wir prüfen, ob ein Hinweis auf freie Termine existiert oder ob sich der Inhalt signifikant ändert.
      # Da du meintest: "vielleicht eine Datumsprüfung - ein neueres Datum als das letztvorhandene":
      
      # Wir extrahieren alle Datumsangaben im Format "Tag, DD. Monat YYYY"
      date_pattern = r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s\d{1,2}\.\s[A-Za-zäöüÄÖÜ]+\s\d{4}"
      found_dates = re.findall(date_pattern, page_text)
      
      # Alternativ: Den gesamten relevanten Textblock der Kalenderliste speichern
      calendar_elements = soup.find_all(text=re.compile("Keine freien Termine"))
      
      # Wir können die Anzahl der "Keine freien Termine"-Meldungen zählen oder den Text vergleichen
      # Wenn sich die Anzahl ändert oder ein Datum dazukommt, ist das ein starkes Indiz.
      
      print(f"Gefundene 'Keine freien Termine'-Einträge: {len(calendar_elements)}")

  except Exception as e:
    exception_msg = f"❌ Ein Fehler ist aufgetreten: {e}"
    print(exception_msg)
    if SEND_DEBUG_MESSAGE:
      send_discord_message(exception_msg)


if __name__ == "__main__":
  check_site()
