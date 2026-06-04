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

# STEP 2 - Select Institution (CMPICA = 2)

payload1 = {
    "__EVENTTARGET": "ddlInst",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": generator,
    "ddlInst": "2",
    "ddlDegree": "0",
    "txtEnrNo": ""
}

html = session.post(URL, data=payload1).text
soup = BeautifulSoup(html, "html.parser")

viewstate = soup.find(id="__VIEWSTATE")["value"]

# STEP 3 - Select Degree (M.Sc.(IT)-NEP = 176)

payload2 = {
    "__EVENTTARGET": "ddlDegree",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": generator,
    "ddlInst": "2",
    "ddlDegree": "176",
    "txtEnrNo": ""
}

html = session.post(URL, data=payload2).text
soup = BeautifulSoup(html, "html.parser")

semester_select = soup.find(id="ddlSem")

if not semester_select:
    send("Semester dropdown not found")
    raise SystemExit

semesters = []

for option in semester_select.find_all("option"):
    value = option.get("value", "").strip()
    text = option.text.strip()

    if value and value != "0":
        semesters.append(f"{value} | {text}")

send(
    "SEMESTERS\n\n" +
    "\n".join(semesters)
)
