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


session = requests.Session()

# STEP 1 - Open page

html = session.get(URL).text
soup = BeautifulSoup(html, "html.parser")

viewstate = soup.find(id="__VIEWSTATE")["value"]
generator = soup.find(id="__VIEWSTATEGENERATOR")["value"]

# CMPICA = 2

payload = {
    "__EVENTTARGET": "ddlInst",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": generator,
    "ddlInst": "2",
    "ddlDegree": "0",
    "txtEnrNo": ""
}

html = session.post(URL, data=payload).text
soup = BeautifulSoup(html, "html.parser")

degree_select = soup.find(id="ddlDegree")

if not degree_select:
    send("Degree dropdown not found")
    raise SystemExit

degrees = []

for option in degree_select.find_all("option"):
    value = option.get("value", "").strip()
    text = option.text.strip()

    if value and value != "0":
        degrees.append(f"{value} | {text}")

send(
    "CMPICA DEGREES\n\n"
    + "\n".join(degrees)
)
