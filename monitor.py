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

viewstate = soup.find(id="__VIEWSTATE")["value"]

# STEP 4 - Select Semester (Sem 2)

payload3 = {
    "__EVENTTARGET": "ddlSem",
    "__EVENTARGUMENT": "",
    "__VIEWSTATE": viewstate,
    "__VIEWSTATEGENERATOR": generator,
    "ddlInst": "2",
    "ddlDegree": "176",
    "ddlSem": "2",
    "txtEnrNo": ""
}

html = session.post(URL, data=payload3).text
soup = BeautifulSoup(html, "html.parser")

exam_select = soup.find(id="ddlScheduleExam")

if not exam_select:
    send("Exam dropdown not found")
    raise SystemExit

exams = []

for option in exam_select.find_all("option"):
    text = option.text.strip()

    if text and text != "Select...":
        exams.append(text)

send(
    "SEM 2 EXAMS\n\n" +
    "\n".join(exams)
)
