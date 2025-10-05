import os
import asyncio
import json
import logging
from typing import Set

import websockets
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError


logging.basicConfig(level=logging.INFO, format="[WS] %(asctime)s %(levelname)s: %(message)s")

CONNECTED: Set[websockets.WebSocketServerProtocol] = set()


async def handler(ws: websockets.WebSocketServerProtocol, path: str):
    # Enforce single path for clarity and basic routing
    if path != "/ws":
        await ws.close(code=4404, reason="Not Found")
        return

    # Basic Origin allowlist (optional)
    allowed_origins_env = os.getenv("WS_ALLOWED_ORIGINS", "").strip()
    if allowed_origins_env:
        allowed_origins = {o.strip() for o in allowed_origins_env.split(",") if o.strip()}
        origin = ws.request_headers.get("Origin", "")
        if origin and origin not in allowed_origins:
            logging.warning(f"Blocked origin: {origin}")
            await ws.close(code=4403, reason="Origin not allowed")
            return

    # Optional token-based auth
    token_required = os.getenv("WEBSOCKET_TOKEN")
    try:
        if token_required:
            try:
                first_msg = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                await ws.close(code=4401, reason="Auth timeout")
                return

            if isinstance(first_msg, bytes):
                await ws.close(code=4402, reason="Binary not allowed in auth")
                return

            try:
                payload = json.loads(first_msg)
            except json.JSONDecodeError:
                payload = {"token": first_msg}

            if payload.get("token") != token_required:
                await ws.close(code=4403, reason="Invalid token")
                return

        CONNECTED.add(ws)
        logging.info(f"Client connected. Total: {len(CONNECTED)}")
        await ws.send(json.dumps({"type": "welcome", "message": "Connected"}))

        # Heartbeat: we use explicit ping to keep connections alive
        ping_interval = int(os.getenv("WS_PING_INTERVAL", "20"))

        async def heartbeat():
            while True:
                try:
                    await ws.ping()
                    await asyncio.sleep(ping_interval)
                except Exception:
                    break

        hb_task = asyncio.create_task(heartbeat())

        async for message in ws:
            # Binary message support: echo/broadcast raw bytes
            if isinstance(message, bytes):
                # Broadcast binary to all clients (including sender)
                for peer in list(CONNECTED):
                    if peer.open:
                        await peer.send(message)
                continue

            # Text message support: try JSON first
            try:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "broadcast":
                    payload = data.get("payload")
                    for peer in list(CONNECTED):
                        if peer is not ws and peer.open:
                            await peer.send(json.dumps({"type": "broadcast", "payload": payload}))
                elif msg_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))
                else:
                    # Default: echo JSON payload back
                    await ws.send(json.dumps({"type": "echo", "payload": data}))

            except json.JSONDecodeError:
                # Plain text echo
                await ws.send(f"echo: {message}")

        hb_task.cancel()

    except (ConnectionClosedOK, ConnectionClosedError):
        pass
    except Exception as e:
        logging.exception("Unexpected handler error: %s", e)
    finally:
        CONNECTED.discard(ws)
        logging.info(f"Client disconnected. Total: {len(CONNECTED)}")


async def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("WS_PORT", "6789"))
    logging.info(f"Starting WebSocket server at ws://{host}:{port}/ws")
    async with serve(handler, host, port, ping_interval=None, ping_timeout=None, max_size=8 * 1024 * 1024):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())