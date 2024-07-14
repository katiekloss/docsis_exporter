#!env/bin/python

"""Exports Netgear C3000 telemetry as a Prometheus exporter"""

import pyjsparser
import requests
from bs4 import BeautifulSoup
from requests.auth import HTTPBasicAuth
from prometheus_client import start_http_server
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily, REGISTRY
from prometheus_client.registry import Collector
from tabulate import tabulate

import credentials

def get_html():
    s = requests.Session()
    a = HTTPBasicAuth(credentials.USERNAME, credentials.PASSWORD)

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

def get_metrics():
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

    return us_channels, ds_channels

def go():
    us_channels, ds_channels = get_metrics()
    print(tabulate(us_channels, headers="keys"))
    print(tabulate(ds_channels, headers="keys"))

class DocsisCollector(Collector): # pylint: disable=too-few-public-methods
    def collect(self):

        _, down = get_metrics()

        correctable_counter = CounterMetricFamily('downstream_correctable', 'Correctable downstream errors', labels=['channel_id', 'frequency'])
        uncorrectable_counter = CounterMetricFamily('downstream_uncorrectable', 'Uncorrectable downstream errors', labels=['channel_id', 'frequency'])
        snr_gauge = GaugeMetricFamily('downstream_snr', 'Downstream signal-to-noise ratio', labels=['channel_id', 'frequency'])
        down_power_gauge = GaugeMetricFamily('downstream_power', 'Downstream power (dBmV)', labels=['channel_id', 'frequency'])

        for channel in down:
            id_frequency_labels = [channel['id'], str(channel['frequency'])]

            correctable_counter.add_metric(id_frequency_labels, channel['correctables'])
            uncorrectable_counter.add_metric(id_frequency_labels, channel['uncorrectables'])

            snr_gauge.add_metric(id_frequency_labels, channel['snr'])

            down_power_gauge.add_metric(id_frequency_labels, channel['power'])

        yield correctable_counter
        yield uncorrectable_counter
        yield snr_gauge
        yield down_power_gauge

if __name__ == "__main__":
    REGISTRY.register(DocsisCollector())
    _, t = start_http_server(8000)
    t.join()
