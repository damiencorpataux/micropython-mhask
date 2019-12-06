import mhask

app = mhask.App(__name__)

@app.route('/')
def index():
    return 'Hello'

app.run()
