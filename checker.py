import os
import requests
from bs4 import BeautifulSoup

# URL der Standesamt-Buchungsseite von Aabenra eintragen
URL = "https://reservation.frontdesksuite.com/aabenraavielse/vielse/ReserveTime/TimeSelection?pageId=9ac8c849-d203-47e2-94a1-173c7f471237&buttonId=cbe0127a-39ce-470f-8c86-26d8eab05e48&culture=de"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")


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
    page_text = soup.get_text()

    # BEISPIEL-LOGIK:
    # Passe das an den tatsächlichen Text/Inhalt der Aabenra-Seite an,
    # sobald dort Termine freigeschaltet werden (z.B. wenn "ausgebucht" verschwindet).
    if "Termin" in page_text and "ausgebucht" not in page_text:
      send_discord_message(
          "🚨 **Achtung! Mögliche Termin-Änderung beim Standesamt Aabenra"
          f" entdeckt!**\nPrüfe die Seite sofort: {URL}"
      )
    else:
      print("Keine relevanten Änderungen gefunden.")

  except Exception as e:
    print(f"Ein Fehler ist aufgetreten: {e}")


if __name__ == "__main__":
  check_site()