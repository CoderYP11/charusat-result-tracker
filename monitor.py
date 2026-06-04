import requests
from bs4 import BeautifulSoup
import os

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

URL = "https://support.charusat.edu.in/Uniexamresult/"

def send(msg):
    requests.get(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    params={
    "chat_id": CHAT_ID,
    "text": msg[:4000]
    }
  )

html = requests.get(URL).text

soup = BeautifulSoup(html, "html.parser")

inst_select = soup.find(id="ddlInst")

if not inst_select:
  send("Institution dropdown not found")
  raise SystemExit

institutions = []

for option in inst_select.find_all("option"):
  value = option.get("value", "").strip()
  text = option.text.strip()

  if value and value != "0":
      institutions.append(f"{value} | {text}")

send(
"INSTITUTIONS\n\n"
+ "\n".join(institutions)
)

