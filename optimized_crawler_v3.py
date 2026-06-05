import requests
from bs4 import BeautifulSoup
import json

URL = "https://support.charusat.edu.in/Uniexamresult/"


def discover_all_results(structure):

    session = requests.Session()

    results = {}

    for inst_id, inst_data in structure.items():

        inst_name = inst_data["name"]

        html = session.get(URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        generator = soup.find(
            id="__VIEWSTATEGENERATOR"
        )["value"]

        viewstate = soup.find(
            id="__VIEWSTATE"
        )["value"]

        payload_inst = {
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
            data=payload_inst,
            timeout=30
        ).text

        soup1 = BeautifulSoup(
            html1,
            "html.parser"
        )

        for degree_id, degree_data in inst_data[
            "degrees"
        ].items():

            degree_name = degree_data["name"]

            viewstate1 = soup1.find(
                id="__VIEWSTATE"
            )["value"]

            payload_degree = {
                "__EVENTTARGET": "ddlDegree",
                "__EVENTARGUMENT": "",
                "__VIEWSTATE": viewstate1,
                "__VIEWSTATEGENERATOR": generator,
                "ddlInst": inst_id,
                "ddlDegree": degree_id,
                "txtEnrNo": ""
            }

            html2 = session.post(
                URL,
                data=payload_degree,
                timeout=30
            ).text

            soup2 = BeautifulSoup(
                html2,
                "html.parser"
            )

            for sem_id in degree_data[
                "semesters"
            ]:

                viewstate2 = soup2.find(
                    id="__VIEWSTATE"
                )["value"]

                payload_sem = {
                    "__EVENTTARGET": "ddlSem",
                    "__EVENTARGUMENT": "",
                    "__VIEWSTATE": viewstate2,
                    "__VIEWSTATEGENERATOR": generator,
                    "ddlInst": inst_id,
                    "ddlDegree": degree_id,
                    "ddlSem": sem_id,
                    "txtEnrNo": ""
                }

                html3 = session.post(
                    URL,
                    data=payload_sem,
                    timeout=30
                ).text

                soup3 = BeautifulSoup(
                    html3,
                    "html.parser"
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
        f"TOTAL RESULTS: {len(results)}"
    )
