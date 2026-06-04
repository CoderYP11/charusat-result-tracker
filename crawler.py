import requests
from bs4 import BeautifulSoup

URL = "https://support.charusat.edu.in/Uniexamresult/"


def get_session():
    return requests.Session()


def get_home(session):
    html = session.get(URL, timeout=30).text
    soup = BeautifulSoup(html, "html.parser")

    return {
        "soup": soup,
        "viewstate": soup.find(id="__VIEWSTATE")["value"],
        "generator": soup.find(id="__VIEWSTATEGENERATOR")["value"]
    }
