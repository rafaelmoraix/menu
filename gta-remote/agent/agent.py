"""
Passa o Controle — agente local (roda no PC do dono, Windows).

O que ele faz:
  * Serve o painel do host em http://127.0.0.1:8765/host.html (só na sua máquina).
  * Cria UM controle virtual de Xbox 360 (via ViGEmBus) e aperta nele
    os botões que o painel mandar.

O que ele NÃO faz (de propósito):
  * Não escuta na rede: só 127.0.0.1, ninguém de fora conecta aqui.
  * Não aceita conexão de outros sites (checa Origin/Host).
  * Não sabe apertar o botão Xbox (guide). Não existe no mapa abaixo.
  * Não mexe em teclado, mouse, arquivos ou qualquer outra coisa do PC.
"""

import asyncio
import json
import math
import sys
import time
from pathlib import Path

from aiohttp import WSMsgType, web

HOST = "127.0.0.1"
PORT = 8765
WEB_DIR = (Path(__file__).resolve().parent.parent / "web").resolve()
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
ALLOWED_ORIGINS = {f"http://{h}" for h in ALLOWED_HOSTS}
IDLE_RESET_SECONDS = 1.0  # sem input por 1s → solta tudo

try:
    import vgamepad as vg
except Exception as exc:  # noqa: BLE001
    print("ERRO: não consegui carregar o vgamepad / ViGEmBus.")
    print("Rode: pip install -r requirements.txt  (e aceite instalar o driver ViGEmBus)")
    print("Detalhe:", exc)
    sys.exit(1)

B = vg.XUSB_BUTTON
# Ordem IGUAL à lista BUTTONS do web/shared.js. Sem XUSB_GAMEPAD_GUIDE.
BUTTON_ORDER = [
    B.XUSB_GAMEPAD_A,
    B.XUSB_GAMEPAD_B,
    B.XUSB_GAMEPAD_X,
    B.XUSB_GAMEPAD_Y,
    B.XUSB_GAMEPAD_LEFT_SHOULDER,
    B.XUSB_GAMEPAD_RIGHT_SHOULDER,
    B.XUSB_GAMEPAD_BACK,
    B.XUSB_GAMEPAD_START,
    B.XUSB_GAMEPAD_LEFT_THUMB,
    B.XUSB_GAMEPAD_RIGHT_THUMB,
    B.XUSB_GAMEPAD_DPAD_UP,
    B.XUSB_GAMEPAD_DPAD_DOWN,
    B.XUSB_GAMEPAD_DPAD_LEFT,
    B.XUSB_GAMEPAD_DPAD_RIGHT,
]
assert B.XUSB_GAMEPAD_GUIDE not in BUTTON_ORDER
MASK_ALL = (1 << len(BUTTON_ORDER)) - 1


def num(v, lo, hi):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(f):
        return 0.0
    return max(lo, min(hi, f))


class Pad:
    def __init__(self):
        self.pad = vg.VX360Gamepad()
        self.last_input = 0.0
        self.active = False
        self.reset()

    def reset(self):
        self.pad.reset()
        self.pad.update()
        self.active = False

    def apply(self, msg):
        try:
            b = int(msg.get("b", 0))
        except (TypeError, ValueError):
            return
        b &= MASK_ALL  # qualquer bit fora da lista permitida é descartado
        self.pad.reset()  # parte do zero: garante que nada "fica preso"
        for i, btn in enumerate(BUTTON_ORDER):
            if b & (1 << i):
                self.pad.press_button(button=btn)
        # No navegador Y positivo = baixo; no XInput Y positivo = cima.
        self.pad.left_joystick_float(num(msg.get("lx"), -1, 1), -num(msg.get("ly"), -1, 1))
        self.pad.right_joystick_float(num(msg.get("rx"), -1, 1), -num(msg.get("ry"), -1, 1))
        self.pad.left_trigger_float(num(msg.get("lt"), 0, 1))
        self.pad.right_trigger_float(num(msg.get("rt"), 0, 1))
        self.pad.update()
        self.last_input = time.monotonic()
        self.active = True


PAD: Pad | None = None


@web.middleware
async def guard(request, handler):
    # Protege contra DNS rebinding e contra outros sites falando com o agente.
    if request.host not in ALLOWED_HOSTS:
        return web.Response(status=403, text="host não permitido")
    origin = request.headers.get("Origin")
    if origin and origin not in ALLOWED_ORIGINS:
        return web.Response(status=403, text="origem não permitida")
    resp = await handler(request)
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Cache-Control"] = "no-store"
    return resp


async def ws_handler(request):
    if request.headers.get("Origin") not in ALLOWED_ORIGINS:
        return web.Response(status=403, text="origem não permitida")
    ws = web.WebSocketResponse(heartbeat=10, max_msg_size=4096)
    await ws.prepare(request)
    await ws.send_str(json.dumps({"t": "info", "text": "controle virtual pronto"}))
    print("Painel conectado.")
    try:
        async for m in ws:
            if m.type != WSMsgType.TEXT:
                continue
            try:
                msg = json.loads(m.data)
            except ValueError:
                continue
            if isinstance(msg, dict) and msg.get("t") == "in":
                PAD.apply(msg)
    finally:
        PAD.reset()
        print("Painel desconectado — controle solto.")
    return ws


async def index(_request):
    raise web.HTTPFound("/host.html")


async def watchdog(_app):
    async def loop():
        while True:
            await asyncio.sleep(0.25)
            if PAD.active and time.monotonic() - PAD.last_input > IDLE_RESET_SECONDS:
                PAD.reset()

    task = asyncio.create_task(loop())
    if "--no-browser" not in sys.argv:
        import webbrowser
        asyncio.get_running_loop().call_later(1.0, webbrowser.open, f"http://{HOST}:{PORT}/host.html")
    yield
    task.cancel()


def main():
    global PAD
    PAD = Pad()
    app = web.Application(middlewares=[guard])
    app.cleanup_ctx.append(watchdog)
    app.router.add_get("/", index)
    app.router.add_get("/ws", ws_handler)
    app.router.add_static("/", WEB_DIR, show_index=False, follow_symlinks=False)
    print("=" * 56)
    print(" Passa o Controle — agente rodando")
    print(f" Abra no Chrome/Edge:  http://{HOST}:{PORT}/host.html")
    print(" Ctrl+C pra desligar.")
    print("=" * 56)
    web.run_app(app, host=HOST, port=PORT, print=None)


if __name__ == "__main__":
    main()
