#!env/bin/python
from requests.auth import HTTPBasicAuth
import requests
import credentials
from bs4 import BeautifulSoup
import pyjsparser

def getHtml():
    s = requests.Session()
    # initially call a random page to get the XSRF token, will return 401
    s.get('http://192.168.0.1/')

    a = HTTPBasicAuth(credentials.username, credentials.password)
    r = s.get('http://192.168.0.1/DocsisStatus.htm', auth=a)

    return BeautifulSoup(r.content, 'html.parser')


def go():
    html = getHtml()
    script_tag = html.find_all('script', src=None)[0]
    script = pyjsparser.parse(script_tag.text)['body']
    initFunc = next(x for x in script if x['type'] == 'FunctionDeclaration' and x['id']['name'] == 'InitDsTableTagValue')

    vals = initFunc['body']['body'][0]['declarations'][0]['init']['value'].split("|")
    channelCount = int(vals[0])
    channels = list()
    properties = ['index','status','modulation','id','frequency','power','snr','correctables','uncorrectables']
    for i in range(channelCount):
        channels.append(dict(zip(properties, [vals[j] for j in range(len(properties))])))
    print(channels)

if __name__ == "__main__":
    go()
