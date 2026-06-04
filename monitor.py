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
total_semesters = 0

for inst_option in inst_select.find_all("option"):

    inst_id = inst_option.get("value", "").strip()
    inst_name = inst_option.text.strip()

    if not inst_id or inst_id == "0":
        continue

    html = session.get(URL).text
    soup = BeautifulSoup(html, "html.parser")

    viewstate = soup.find(id="__VIEWSTATE")["value"]

    payload1 = {
        "__EVENTTARGET": "ddlInst",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst": inst_id,
        "ddlDegree": "0",
        "txtEnrNo": ""
    }

    html1 = session.post(URL, data=payload1).text
    soup1 = BeautifulSoup(html1, "html.parser")

    degree_select = soup1.find(id="ddlDegree")

    institution_degree_count = 0
    institution_semester_count = 0

    if degree_select:

        for degree_option in degree_select.find_all("option"):

            degree_id = degree_option.get("value", "").strip()

            if not degree_id or degree_id == "0":
                continue

            institution_degree_count += 1
            total_degrees += 1

            viewstate = soup1.find(id="__VIEWSTATE")["value"]

            payload2 = {
                "__EVENTTARGET": "ddlDegree",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate,
                "__VIEWSTATEGENERATOR": generator,
                "ddlInst": inst_id,
                "ddlDegree": degree_id,
                "txtEnrNo": ""
            }

            html2 = session.post(URL, data=payload2).text
            soup2 = BeautifulSoup(html2, "html.parser")

            semester_select = soup2.find(id="ddlSem")

            if semester_select:

                semester_count = 0

                for sem_option in semester_select.find_all("option"):

                    sem_id = sem_option.get("value", "").strip()

                    if sem_id and sem_id != "0":
                        semester_count += 1

                institution_semester_count += semester_count
                total_semesters += semester_count

    summary.append(
        f"{inst_name} -> {institution_degree_count} degrees -> {institution_semester_count} semesters"
    )

message = (
    "CHARUSAT SEMESTER DISCOVERY\n\n"
    + "\n".join(summary)
    + f"\n\nTOTAL DEGREES: {total_degrees}"
    + f"\nTOTAL SEMESTERS: {total_semesters}"
)

send(message)
