"""
Try:
    curl -i -XPUT localhost --data 'Some plain text'
    curl -i -XPUT localhost --data '{"world": "hello"}'
"""

import mhask
import ujson

class Json(mhask.Response):
    def __init__(self, body, *args, **kwargs):
        body = ujson.dumps(body)
        super().__init__(body, *args, **kwargs)
        self.headers['content-type'] = 'application/json'

app = mhask.App(__name__)
app.debug = True

@app.route('/')
def index():
    return Json({'hello': 'world'})

@app.route('/', methods=['PUT'])
def put():
    return Json({'method': app.request.method,
                 'headers': app.request.headers,
                 'path': app.request.path,
                 'body': app.request.body,
                 'json': app.request.json()})

app.run()
