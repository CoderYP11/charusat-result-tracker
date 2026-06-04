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

html = session.get(URL).text
soup = BeautifulSoup(html, "html.parser")

generator = soup.find(id="__VIEWSTATEGENERATOR")["value"]

inst_select = soup.find(id="ddlInst")

if not inst_select:
    send("Institution dropdown not found")
    raise SystemExit

summary = []
total_degrees = 0

for inst_option in inst_select.find_all("option"):

    inst_id = inst_option.get("value", "").strip()
    inst_name = inst_option.text.strip()

    if not inst_id or inst_id == "0":
        continue

    html = session.get(URL).text
    soup = BeautifulSoup(html, "html.parser")

    viewstate = soup.find(id="__VIEWSTATE")["value"]

    payload = {
        "__EVENTTARGET": "ddlInst",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst": inst_id,
        "ddlDegree": "0",
        "txtEnrNo": ""
    }

    html2 = session.post(URL, data=payload).text
    soup2 = BeautifulSoup(html2, "html.parser")

    degree_select = soup2.find(id="ddlDegree")

    degree_count = 0

    if degree_select:

        for degree_option in degree_select.find_all("option"):

            degree_id = degree_option.get("value", "").strip()

            if degree_id and degree_id != "0":
                degree_count += 1

    total_degrees += degree_count

    summary.append(
        f"{inst_name} -> {degree_count} degrees"
    )

message = (
    "CHARUSAT DEGREE DISCOVERY\n\n"
    + "\n".join(summary)
    + f"\n\nTOTAL DEGREES: {total_degrees}"
)

send(message)
