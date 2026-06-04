import json
import requests
from bs4 import BeautifulSoup

from github_state import save_structure

URL = "https://support.charusat.edu.in/Uniexamresult/"

session = requests.Session()

structure = {}

html = session.get(URL, timeout=30).text
soup = BeautifulSoup(html, "html.parser")

generator = soup.find(id="__VIEWSTATEGENERATOR")["value"]

inst_select = soup.find(id="ddlInst")

for inst_option in inst_select.find_all("option"):

    inst_id = inst_option.get("value", "").strip()
    inst_name = inst_option.text.strip()

    if not inst_id or inst_id == "0":
        continue

    html = session.get(URL, timeout=30).text
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

    html1 = session.post(
        URL,
        data=payload1,
        timeout=30
    ).text

    soup1 = BeautifulSoup(
        html1,
        "html.parser"
    )

    degree_select = soup1.find(
        id="ddlDegree"
    )

    structure[inst_id] = {
        "name": inst_name,
        "degrees": {}
    }

    if not degree_select:
        continue

    for degree_option in degree_select.find_all("option"):

        degree_id = degree_option.get(
            "value",
            ""
        ).strip()

        degree_name = degree_option.text.strip()

        if not degree_id or degree_id == "0":
            continue

        viewstate = soup1.find(
            id="__VIEWSTATE"
        )["value"]

        payload2 = {
            "__EVENTTARGET": "ddlDegree",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": generator,
            "ddlInst": inst_id,
            "ddlDegree": degree_id,
            "txtEnrNo": ""
        }

        html2 = session.post(
            URL,
            data=payload2,
            timeout=30
        ).text

        soup2 = BeautifulSoup(
            html2,
            "html.parser"
        )

        semester_select = soup2.find(
            id="ddlSem"
        )

        semesters = []

        if semester_select:

            for sem_option in semester_select.find_all(
                "option"
            ):

                sem_id = sem_option.get(
                    "value",
                    ""
                ).strip()

                if sem_id and sem_id != "0":

                    semesters.append(
                        sem_id
                    )

        structure[inst_id]["degrees"][degree_id] = {
            "name": degree_name,
            "semesters": semesters
        }

save_structure(structure)

total_degrees = 0
total_semesters = 0

for inst in structure.values():

    total_degrees += len(
        inst["degrees"]
    )

    for degree in inst["degrees"].values():

        total_semesters += len(
            degree["semesters"]
        )

print(
    f"Institutions: {len(structure)}"
)

print(
    f"Degrees: {total_degrees}"
)

print(
    f"Semesters: {total_semesters}"
)

print(
    "structure.json saved to GitHub"
)
