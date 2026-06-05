from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup

URL = "https://support.charusat.edu.in/Uniexamresult/"


def process_institute(inst_option):

    session = requests.Session()

    results = {}

    inst_id = inst_option.get("value", "").strip()
    inst_name = inst_option.text.strip()

    if not inst_id or inst_id == "0":
        return results

    try:

        html = session.get(URL, timeout=30).text
        soup = BeautifulSoup(html, "html.parser")

        generator = soup.find(id="__VIEWSTATEGENERATOR")["value"]
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

        soup1 = BeautifulSoup(html1, "html.parser")

        degree_select = soup1.find(id="ddlDegree")

        if not degree_select:
            return results

        for degree_option in degree_select.find_all("option"):

            degree_id = degree_option.get("value", "").strip()
            degree_name = degree_option.text.strip()

            if not degree_id or degree_id == "0":
                continue

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

            html2 = session.post(
                URL,
                data=payload2,
                timeout=30
            ).text

            soup2 = BeautifulSoup(html2, "html.parser")

            semester_select = soup2.find(id="ddlSem")

            if not semester_select:
                continue

            for sem_option in semester_select.find_all("option"):

                sem_id = sem_option.get("value", "").strip()

                if not sem_id or sem_id == "0":
                    continue

                viewstate = soup2.find(id="__VIEWSTATE")["value"]

                payload3 = {
                    "__EVENTTARGET": "ddlSem",
                    "__EVENTARGUMENT": "",
                    "__VIEWSTATE": viewstate,
                    "__VIEWSTATEGENERATOR": generator,
                    "ddlInst": inst_id,
                    "ddlDegree": degree_id,
                    "ddlSem": sem_id,
                    "txtEnrNo": ""
                }

                html3 = session.post(
                    URL,
                    data=payload3,
                    timeout=30
                ).text

                soup3 = BeautifulSoup(html3, "html.parser")

                exam_select = soup3.find(id="ddlScheduleExam")

                if not exam_select:
                    continue

                for exam_option in exam_select.find_all("option"):

                    exam_name = exam_option.text.strip()

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

    except Exception as e:

        print(f"[ERROR] {inst_name}: {e}")
        return results

    return results


def discover_all_results():

    session = requests.Session()

    html = session.get(
        URL,
        timeout=30
    ).text

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    inst_select = soup.find(
        id="ddlInst"
    )

    if not inst_select:
        return {}

    results = {}

    with ThreadPoolExecutor(
        max_workers=11
    ) as executor:

        futures = []

        for inst_option in inst_select.find_all(
            "option"
        ):

            futures.append(
                executor.submit(
                    process_institute,
                    inst_option
                )
            )

        for future in as_completed(
            futures
        ):

            results.update(
                future.result()
            )

    return results
