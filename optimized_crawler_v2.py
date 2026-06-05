import requests
from bs4 import BeautifulSoup
import json

URL = "https://support.charusat.edu.in/Uniexamresult/"

def post_and_parse(session, payload):

    html = session.post(
        URL,
        data=payload,
        timeout=30
    ).text

    return BeautifulSoup(
        html,
        "html.parser"
    )

def discover_all_results(structure):

    session = requests.Session()

    results = {}

    for inst_id, inst_data in structure.items():

        inst_name = inst_data["name"]

        for degree_id, degree_data in inst_data["degrees"].items():

            degree_name = degree_data["name"]

            for sem_id in degree_data["semesters"]:

                try:

                    html = session.get(
                        URL,
                        timeout=30
                    ).text

                    soup = BeautifulSoup(
                        html,
                        "html.parser"
                    )

                    viewstate = soup.find(
                        id="__VIEWSTATE"
                    )["value"]

                    generator = soup.find(
                        id="__VIEWSTATEGENERATOR"
                    )["value"]

                    payload1 = {
                        "__EVENTTARGET": "ddlInst",
                        "__EVENTARGUMENT": "",
                        "__VIEWSTATE": viewstate,
                        "__VIEWSTATEGENERATOR": generator,
                        "ddlInst": inst_id,
                        "ddlDegree": "0",
                        "txtEnrNo": ""
                    }

                    soup1 = post_and_parse(
                        session,
                        payload1
                    )

                    viewstate1 = soup1.find(
                        id="__VIEWSTATE"
                    )["value"]

                    payload2 = {
                        "__EVENTTARGET": "ddlDegree",
                        "__EVENTARGUMENT": "",
                        "__VIEWSTATE": viewstate1,
                        "__VIEWSTATEGENERATOR": generator,
                        "ddlInst": inst_id,
                        "ddlDegree": degree_id,
                        "txtEnrNo": ""
                    }

                    soup2 = post_and_parse(
                        session,
                        payload2
                    )

                    viewstate2 = soup2.find(
                        id="__VIEWSTATE"
                    )["value"]

                    payload3 = {
                        "__EVENTTARGET": "ddlSem",
                        "__EVENTARGUMENT": "",
                        "__VIEWSTATE": viewstate2,
                        "__VIEWSTATEGENERATOR": generator,
                        "ddlInst": inst_id,
                        "ddlDegree": degree_id,
                        "ddlSem": sem_id,
                        "txtEnrNo": ""
                    }

                    soup3 = post_and_parse(
                        session,
                        payload3
                    )

                    exam_select = soup3.find(
                        id="ddlScheduleExam"
                    )

                    if not exam_select:
                        continue

                    for option in exam_select.find_all(
                        "option"
                    ):

                        exam_name = option.text.strip()

                        if (
                            not exam_name
                            or exam_name == "Select..."
                        ):
                            continue

                        key = (
                            f"{inst_name}|"
                            f"{degree_name}|"
                            f"{sem_id}|"
                            f"{exam_name}"
                        )

                        results[key] = True

                except Exception:
                    continue

    return results

if __name__ == "__main__":

    with open(
        "structure.json",
        "r",
        encoding="utf-8"
    ) as f:

        structure = json.load(f)

    results = discover_all_results(
        structure
    )

    print(
        "TOTAL RESULTS:",
        len(results)
    )
