from datetime import datetime
import json
import os
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Die Startseite des Standesamts Aabenra
START_URL = "https://reservation.frontdesksuite.com/aabenraavielse/vielse/Home/Index?pageid=9ac8c849-d203-47e2-94a1-173c7f471237&culture=de&uiculture=de"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
STATE_FILE = "last_state.json"

# SCHALTER: True = Sendet nach JEDER Prüfung eine Statusnachricht ("Seite wird geprüft"), False = Nur bei Alarm
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


# Deutscher Monatsname zu Zahl Mapping für den Datumsvergleich
GERMAN_MONTHS = {
    "Januar": 1,
    "Februar": 2,
    "März": 3,
    "April": 4,
    "Mai": 5,
    "Juni": 6,
    "Juli": 7,
    "August": 8,
    "September": 9,
    "Oktober": 10,
    "November": 11,
    "Dezember": 12,
}


def parse_german_date(date_str):
  """Wandelt einen Text wie 'Donnerstag, 22. Oktober 2026' in ein echtes datetime-Objekt um."""
  try:
    # Entferne den Wochentag am Anfang (alles vor dem ersten Komma)
    clean_str = date_str.split(",")[1].strip()
    parts = clean_str.split(" ")
    day = int(parts[0].replace(".", ""))
    month = GERMAN_MONTHS.get(parts[1], 0)
    year = int(parts[2])
    return datetime(year, month, day)
  except Exception as e:
    print(f"Fehler beim Parsen des Datums '{date_str}': {e}")
    return None


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

      # 1. Debug-Nachricht senden (falls aktiv)
      if SEND_DEBUG_MESSAGE:
        send_discord_message("-------------------Seite wird geprüft------------------")

      # 2. Wir suchen im HTML nach den einzelnen Termin-Zeilen/Blöcken
      # Im Screenshot sieht man, dass jedes Datum eine eigene Zeile/Überschrift hat
      # und direkt daneben oder darunter "Keine freien Termine" steht.
      
      # Wir extrahieren alle Textblöcke oder suchen nach dem Muster: [Datum] ... [Status]
      full_text = soup.get_text()

      # Regulärer Ausdruck, um alle Datumsangaben zu finden (z.B. "Donnerstag, 22. Oktober 2026")
      date_pattern = r"(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag),\s\d{1,2}\.\s[A-Za-zäöüÄÖÜ]+\s\d{4}"
      raw_dates = re.findall(date_pattern, full_text)
      
      # Da re.findall bei Gruppen (Montag, Dienstag...) Tupel zurückgibt, holen wir uns die genauen Matches
      found_date_strings = []
      for match in re.finditer(date_pattern, full_text):
        found_date_strings.append(match.group(0))

      # Duplikate entfernen, falls ein Datum mehrfach auf der Seite steht
      found_date_strings = list(dict.fromkeys(found_date_strings))

      if not found_date_strings:
        print("Keine Termine auf der Seite gefunden!")
        return

      # In datetime-Objekte umwandeln und sortieren
      valid_dates = []
      for d_str in found_date_strings:
        dt = parse_german_date(d_str)
        if dt:
          valid_dates.append((dt, d_str))

      if not valid_dates:
        print("Konnte keine gültigen Datumsangaben parsen.")
        return

      # Sortieren nach Datum
      valid_dates.sort(key=lambda x: x[0])
      latest_dt, latest_str = valid_dates[-1]  # Das späteste Datum

      # 3. Prüfen, ob bei IRGENDEINEM Datum NICHT "Keine freien Termine" steht
      # Dazu schauen wir uns die HTML-Struktur an: Wir suchen alle Abschnitte, in denen ein Datum steht,
      # und prüfen den Text in der unmittelbaren Umgebung.
      free_slots_found = []
      
      # Wir holen alle Zeilen/Divs und prüfen, ob ein Datum vorkommt und ob "Keine freien Termine" FEHLT
      for dt, d_str in valid_dates:
        # Suche nach dem HTML-Element, das dieses Datum enthält
        element = soup.find(text=lambda t: t and d_str in t)
        if element:
          # Wir schauen uns das Eltern-Element an (das den ganzen Block für diesen Tag umschließt)
          parent_box = element.find_parent(["div", "tr", "li", "section"])
          if parent_box:
            box_text = parent_box.get_text()
            # Wenn "Keine freien Termine" HIER NICHT STEHT -> GEFUNDEN!
            if "Keine freien Termine" not in box_text:
              free_slots_found.append(d_str)

      # 4. Alten Zustand aus JSON-Datei laden
      old_state = {"latest_date": "", "free_slots": []}
      if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
          try:
            old_state = json.load(f)
          except:
            pass

      old_latest_date = old_state.get("latest_date", "")

      # 5. ALARM-PRÜFUNGEN

      # Bedingung 1: Neues spätestes Datum ist weiter in der Zukunft
      new_date_added = False
      if old_latest_date == "":
        print(f"Erster Lauf: Spätestes Datum gespeichert: {latest_str}")
      elif latest_str != old_latest_date:
        # Vergleiche, ob das neue Datum tatsächlich *später* ist als das alte
        old_dt = parse_german_date(old_latest_date)
        if old_dt and latest_dt > old_dt:
          new_date_added = True
          print(f"Neues späteres Datum entdeckt: {latest_str}")
          send_discord_message(
              "🚨 **Neues Datum beim Standesamt Aabenra freigeschaltet!**\n"
              f"Das neue späteste Datum ist: **{latest_str}**\n"
              f"Prüfe die Seite sofort: {current_url}"
          )

      # Bedingung 2: Mindestens ein Feld ist NICHT als "Keine freien Termine" gekennzeichnet
      if free_slots_found:
        print(f"Mögliche freie Termine gefunden für: {free_slots_found}")
        send_discord_message(
            "🟢 **AHRTUNG! Möglicher freier Termin entdeckt!**\n"
            f"Folgende Tage haben nicht mehr den Status 'Keine freien Termine': {free_slots_found}\n"
            f"Prüfe die Seite sofort: {current_url}"
        )

      # 6. Zustand für den nächsten Lauf speichern
      new_state = {
          "latest_date": latest_str,
          "free_slots": free_slots_found
      }
      with open(STATE_FILE, "w") as f:
        json.dump(new_state, f, indent=4)

      print(f"Prüfung erfolgreich. Spätestes Datum aktuell: {latest_str}")

  except Exception as e:
    exception_msg = f"❌ Ein Fehler ist aufgetreten: {e}"
    print(exception_msg)
    if SEND_DEBUG_MESSAGE:
      send_discord_message(exception_msg)


if __name__ == "__main__":
  check_site()
