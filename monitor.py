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

results = []

# STEP 1 - Open page

html = session.get(URL).text
soup = BeautifulSoup(html, "html.parser")

generator = soup.find(id="__VIEWSTATEGENERATOR")["value"]

# STEP 2 - Institution

viewstate = soup.find(id="__VIEWSTATE")["value"]

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

# STEP 3 - Degree

viewstate = soup.find(id="__VIEWSTATE")["value"]

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

    if value and value != "0":
        semesters.append(value)

for sem in semesters:

    viewstate = soup.find(id="__VIEWSTATE")["value"]

    payload3 = {
        "__EVENTTARGET": "ddlSem",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": generator,
        "ddlInst": "2",
        "ddlDegree": "176",
        "ddlSem": sem,
        "txtEnrNo": ""
    }

    html2 = session.post(URL, data=payload3).text
    soup2 = BeautifulSoup(html2, "html.parser")

    exam_select = soup2.find(id="ddlScheduleExam")

    if not exam_select:
        continue

    for option in exam_select.find_all("option"):

        exam = option.text.strip()

        if exam and exam != "Select...":

            results.append(
                f"M.Sc.(IT)-NEP | Sem {sem} | {exam}"
            )

if not results:
    send("No exams found")
else:
    send(
        "M.Sc.(IT)-NEP RESULTS\n\n" +
        "\n".join(results)
    )
