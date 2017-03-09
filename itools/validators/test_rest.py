
from httplib2 import Http
import json
from pprint import pprint

uri = 'http://ikaaro.agicia.net/;test_validators'
h = Http()
headers = {'Content-type': 'application/json'}
body = {'field_1': 5}
body = json.dumps(body)
resp, content = h.request(uri, "POST", headers=headers, body=body)
data = json.loads(content)
pprint(data)

