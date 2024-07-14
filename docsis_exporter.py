#!env/bin/python

"""Exports Netgear C3000 telemetry as a Prometheus exporter"""

import pyjsparser
import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from tabulate import tabulate

import credentials

s = requests.Session()
a = HTTPBasicAuth(credentials.USERNAME, credentials.PASSWORD)


def get_html():
    # initially call a random page to get the XSRF token, will return 401
    r = s.get("http://192.168.0.1/")
    assert r.status_code == 401

    r = s.get("http://192.168.0.1/DocsisStatus.htm", auth=a)
    r.raise_for_status()

    h = BeautifulSoup(r.content, "html.parser")

    f = h.find("form")

    if "name" not in f.attrs:
        print("Forcing logout with " + f["action"])
        s.post("http://192.168.0.1" + f["action"], data={"yes": "", "act": "yes"})

        r = s.get("http://192.168.0.1/DocsisStatus.htm", auth=a)
        r.raise_for_status()

        h = BeautifulSoup(r.content, "html.parser")
        f = h.find("form")

    assert "name" in f.attrs
    return h


def go():
    html = get_html()

    functions = {}
    for script_tag in html.find_all("script", src=None):
        script = pyjsparser.parse(script_tag.text)["body"]
        functions.update({
            x["id"]["name"]: x for x in script if x["type"] == "FunctionDeclaration"
        })

    assert "InitDsTableTagValue" in functions
    assert "InitUsTableTagValue" in functions

    vals = functions["InitDsTableTagValue"]["body"]["body"][0]["declarations"][0]["init"]["value"].split("|")
    channel_count = int(vals[0])
    ds_channels = []
    properties = [
        "index",
        "status",
        "modulation",
        "id",
        "frequency",
        "power",
        "snr",
        "correctables",
        "uncorrectables",
    ]
    for i in range(channel_count):
        channel_properties = dict(zip(properties, [vals[j + 1] for j in range(len(properties) * i, len(properties) * i + len(properties))]))
        channel_properties["frequency"] = int(channel_properties["frequency"].split(" ")[0])
        channel_properties["power"] = float(channel_properties["power"].split(" ")[0])
        channel_properties["snr"] = float(channel_properties["snr"].split(" ")[0])
        channel_properties["correctables"] = int(channel_properties["correctables"])
        channel_properties["uncorrectables"] = int(channel_properties["uncorrectables"])

        ds_channels.append(channel_properties)

    vals = functions["InitUsTableTagValue"]["body"]["body"][0]["declarations"][0]["init"]["value"].split("|")
    channel_count = int(vals[0])
    us_channels = []
    properties = [
        "index",
        "status",
        "type",
        "id",
        "rate",
        "frequency",
        "power"
    ]
    for i in range(channel_count):
        us_channels.append(
            dict(zip(properties, [vals[j + 1] for j in range(len(properties) * i, len(properties) * i + len(properties))]))
        )

    print(tabulate(us_channels, headers="keys"))
    print(tabulate(ds_channels, headers="keys"))


if __name__ == "__main__":
    go()
