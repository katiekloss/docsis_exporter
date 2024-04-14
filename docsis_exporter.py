#!env/bin/python
from requests.auth import HTTPBasicAuth
import requests
import credentials
from bs4 import BeautifulSoup
import pyjsparser

s = requests.Session()
a = HTTPBasicAuth(credentials.username, credentials.password)

def getHtml():
    # initially call a random page to get the XSRF token, will return 401
    s.get('http://192.168.0.1/')
    r = s.get('http://192.168.0.1/DocsisStatus.htm', auth=a)
    h = BeautifulSoup(r.content, 'html.parser')

    f = h.find('form')

    if 'name' not in f.attrs:
        print('Forcing logout with ' + f['action'])
        s.post('http://192.168.0.1' + f['action'], data={'yes':'','act':'yes'})

        r = s.get('http://192.168.0.1/DocsisStatus.htm', auth=a)
        h = BeautifulSoup(r.content, 'html.parser')
        f = h.find('form')

    assert 'name' in f.attrs
    return h

def go():
    html = getHtml()

    initFunc = None
    for script_tag in html.find_all('script', src=None):
        script = pyjsparser.parse(script_tag.text)['body']
        functions = { x['id']['name']:x for x in script if x['type'] == 'FunctionDeclaration' }

        if 'InitDsTableTagValue' in functions:
            initFunc = functions['InitDsTableTagValue']
            break

    assert initFunc != None

    vals = initFunc['body']['body'][0]['declarations'][0]['init']['value'].split("|")
    channelCount = int(vals[0])
    channels = list()
    properties = ['index','status','modulation','id','frequency','power','snr','correctables','uncorrectables']
    for i in range(channelCount):
        channels.append(dict(zip(properties, [vals[j] for j in range(len(properties))])))
    print(channels)

if __name__ == "__main__":
    go()
