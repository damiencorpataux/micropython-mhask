micropython-mhask
=================

Micropython HTTP Asynchronous Service like Flask

Install
-------
```sh
micropython -m upip install micropython-mhask
```

Usage
-----
```python3
app = mhask.App(__name__)

@app.route('/')
def index():
    return 'Hello'

app.run()
```
See more examples at https://github.com/damiencorpataux/micropython-mhask/blob/master/examples.
