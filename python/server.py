import asyncio
from aiohttp import web
import aiohttp
import os
import pty
import fcntl

import sys

async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    loop = asyncio.get_running_loop()

    master, slave = pty.openpty()

    name = os.ttyname(slave)

    pid = os.fork() 
    if pid == 0:
        os.setsid()
        os.dup2(slave,0)
        os.dup2(slave,1)
        os.dup2(slave,2)
        os._exit(os.execv(sys.argv[1],(sys.argv[1], sys.argv[1:])))

    stdin = os.fdopen(master, 'wb+', buffering=0)

    fl = fcntl.fcntl(master, fcntl.F_GETFL)
    fcntl.fcntl(master, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def pipe_data_received(ws):
        data = stdin.read()
        try:
            asyncio.ensure_future(ws.send_str(data.decode()))
        except:
            os.kill(pid,15)

    loop.add_reader(master, pipe_data_received, ws)

    async for msg in ws:
        
        if msg.type == aiohttp.WSMsgType.TEXT:
            stdin.write(msg.data.encode())

        elif msg.type == aiohttp.WSMsgType.BINARY:
            stdin.write(msg.data)

        elif msg.type == aiohttp.WSMsgType.CLOSE:
            await ws.close()
            os.kill(pid,15)

        elif msg.type == aiohttp.WSMsgType.CLOSED:
            os.kill(pid,15)
        elif msg.type == aiohttp.WSMsgType.ERROR:
            os.kill(pid,15)
    
    os.kill(pid,15)
    os.waitpid(pid, 0)
    return ws


app = web.Application()
app.add_routes([web.get('/term', websocket_handler)])
app.router.add_static('/', '../html')
web.run_app(app)
