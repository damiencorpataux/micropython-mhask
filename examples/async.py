import mhask
import uasyncio

app = mhask.App(__name__)

@app.route('/')
def index():
    return 'Hello'


async def task_web():
    print('Starting web server')
    await uasyncio.start_server(mhask.Asyncio(app).serve, '0.0.0.0', 80)

async def task_other():
    while True:
        print('My other task running')
        await uasyncio.sleep(2.5)

try:
    loop = uasyncio.get_event_loop()
    loop.create_task(task_web())
    loop.create_task(task_other())
    loop.run_forever()
finally:
    loop.close()
