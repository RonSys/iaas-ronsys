"""
📞 Call-Bridge — Adapter AMI/ARI de la Central Telefónica (Spec 05 F2, §3.4).

Servicio separado (patrón del worker: contenedor Python 3.12-slim, sin API
propia). Conecta a **AMI** (eventos de llamadas) y **ARI** (control/Originate)
de Asterisk — ambos bind 127.0.0.1 (D3, nunca expuestos) — y habla con el
backend por HTTP interno:

  - AMI listener: escucha `Newchannel` / `Newstate` / `Hangup` y reenvía el
    estado a `POST /api/v1/calls/events` (token de servicio + allowlist IP).
    El backend hace el upsert idempotente por `external_call_id` (R8) → el
    bridge es re-arrancable sin duplicar llamadas (CA-F2.1).
  - ARI originate: `originate(target, extension)` → `POST /ari/channels`
    (click-to-call desde el backend, CA-F2.8).
  - Reconexión con backoff, logging estructurado.

Configuración (env, defaults SOLO desarrollo — nunca credenciales reales):
  AMI_HOST=127.0.0.1  AMI_PORT=5038  AMI_USER=ami_user  AMI_PASS=ami_secret
  ARI_HOST=127.0.0.1  ARI_PORT=8088  ARI_USER=ari_user  ARI_PASS=ari_secret
  BACKEND_INTERNAL_URL=http://127.0.0.1:8000
  SERVICE_TOKEN=<token del backend — generado con: openssl rand -hex 32>
  CALL_BRIDGE_POLL_SECONDS=1   (intervalo de lectura AMI)

Entrypoint: python -m app.services.call_bridge
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
from datetime import datetime, timezone

import httpx

logger = logging.getLogger("call_bridge")

# ─── Config (env) ───────────────────────────────────────────────

AMI_HOST = os.getenv("AMI_HOST", "127.0.0.1")
AMI_PORT = int(os.getenv("AMI_PORT", "5038"))
AMI_USER = os.getenv("AMI_USER", "ami_user")
AMI_PASS = os.getenv("AMI_PASS", "ami_secret")

ARI_HOST = os.getenv("ARI_HOST", "127.0.0.1")
ARI_PORT = int(os.getenv("ARI_PORT", "8088"))
ARI_USER = os.getenv("ARI_USER", "ari_user")
ARI_PASS = os.getenv("ARI_PASS", "ari_secret")

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://127.0.0.1:8000").rstrip("/")
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "")

POLL_SECONDS = float(os.getenv("CALL_BRIDGE_POLL_SECONDS", "1.0"))
RECONNECT_BACKOFF = (1, 5, 15, 30, 60)  # segundos entre reintentos de conexión


# ─── Utilidades ─────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ami_response(data: bytes) -> dict:
    """Parsea una respuesta/evento AMI (pares `Key: Value` separados por CRLF).

    AMI es texto plano: cada línea `Key: Value`, terminador línea vacía.
    Devuelve dict con las claves; `Event` presente en eventos, `Response`
    presente en respuestas a acciones.
    """
    result: dict[str, str] = {}
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


# ─── AMI client (socket TCP, sin dependencias externas) ────────

class AmiClient:
    """Cliente AMI mínimo: login + lectura de eventos con timeout.

    El protocolo AMI (manager.conf) es texto sobre TCP:
      Action: Login / Username: ... / Secret: ...  →  Response: Success
    Luego Asterisk empuja eventos (Newchannel, Newstate, Hangup, ...).
    """

    def __init__(self, host: str, port: int, user: str, secret: str):
        self.host = host
        self.port = port
        self.user = user
        self.secret = secret
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Abre el socket y hace Login. Levanta excepción si falla."""
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        await self._send_action({
            "Action": "Login",
            "Username": self.user,
            "Secret": self.secret,
            "Events": "on",
        })
        # Leer la respuesta de login (con timeout para no colgarse)
        resp = await self._read_message(timeout=5.0)
        if resp.get("Response") != "Success":
            raise ConnectionError(f"AMI login falló: {resp}")
        logger.info("AMI login OK (%s:%s)", self.host, self.port)

    async def _send_action(self, action: dict) -> None:
        if self._writer is None:
            raise ConnectionError("AMI no conectado")
        body = "".join(f"{k}: {v}\r\n" for k, v in action.items())
        self._writer.write((body + "\r\n").encode())
        await self._writer.drain()

    async def _read_message(self, timeout: float | None = None) -> dict:
        """Lee UN mensaje AMI completo (pares Key: Value hasta línea vacía)."""
        if self._reader is None:
            raise ConnectionError("AMI no conectado")
        lines: list[bytes] = []
        while True:
            raw = await asyncio.wait_for(self._reader.readline(), timeout=timeout)
            if not raw:
                raise ConnectionError("AMI cerró la conexión")
            if raw in (b"\r\n", b"\n", b""):
                break
            lines.append(raw)
            if len(lines) > 200:  # defensivo: mensaje anormalmente largo
                break
        return _parse_ami_response(b"".join(lines))

    async def read_event(self) -> dict:
        """Lee el siguiente evento/response AMI (bloqueante con poll timeout)."""
        return await self._read_message(timeout=POLL_SECONDS)

    async def close(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
            self._writer = None
            self._reader = None


# ─── ARI originate (control) ────────────────────────────────────

async def originate(target: str, extension: str) -> dict:
    """Originate vía ARI (CA-F2.8): llama al destino por el trunk del proveedor.

    POST /ari/channels?endpoint=PJSIP/<target>@provider-trunk
         &extension=<ext>&context=from-internal&app=call-bridge
    Devuelve el JSON de la respuesta ARI (channel creado) o levanta excepción.
    """
    url = f"http://{ARI_HOST}:{ARI_PORT}/ari/channels"
    params = {
        "endpoint": f"PJSIP/{target}@provider-trunk",
        "extension": extension,
        "context": "from-internal",
        "app": "call-bridge",
        "timeout": "30",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, params=params, auth=(ARI_USER, ARI_PASS))
        resp.raise_for_status()
        return resp.json()


# ─── Eventos AMI → backend ──────────────────────────────────────

def _build_event_payload(event: dict) -> dict | None:
    """Traduce un evento AMI al payload de POST /api/v1/calls/events (§3.5.2).

    Mapeo:
      Newchannel  → status=ringing     (inicio: caller/callee/direction)
      Newstate    → status=in_progress (si ChannelState=Up) o answered
      Hangup      → status=completed/missed/failed + duration + hangup_cause
    El upsert idempotente (external_call_id = Uniqueid) lo hace el backend.
    """
    event_name = event.get("Event")
    uniqueid = event.get("Uniqueid") or event.get("ChannelUniqueid")
    if not event_name or not uniqueid:
        return None

    # Dirección: en inbound el que llama es CallerIDNum y el destino el DID
    # (Context=from-pstn); en outbound (click-to-call) el Context=from-internal
    # y el que llama es la extensión del operador.
    caller = event.get("CallerIDNum") or event.get("CallerID") or ""
    callee = event.get("Exten") or event.get("ConnectedLineNum") or ""
    channel = event.get("Channel") or ""
    context = (event.get("Context") or "").lower()

    direction = "inbound" if "from-pstn" in context else "outbound"
    started_at = _now_iso()

    if event_name == "Newchannel":
        return {
            "external_call_id": uniqueid,
            "caller": caller,
            "callee": callee or channel,
            "direction": direction,
            "status": "ringing",
            "started_at": started_at,
            "metadata": {"channel": channel, "context": context},
        }

    if event_name == "Newstate":
        state = (event.get("ChannelState") or "").lower()
        status = "in_progress" if state == "up" else "ringing"
        return {
            "external_call_id": uniqueid,
            "caller": caller,
            "callee": callee or channel,
            "direction": direction,
            "status": status,
            "started_at": started_at,
            "answered_at": started_at if status == "in_progress" else None,
            "metadata": {"channel": channel, "context": context},
        }

    if event_name == "Hangup":
        cause = event.get("Cause") or event.get("HangupCause") or ""
        cause_txt = event.get("CauseTxt") or ""
        # 16=Normal Clearing (completada), 17=User Busy, 19=No Answer,
        # 21=Rejected, 27=Destination Out of Order, 28=Address incomplete...
        if cause in ("16",) or cause_txt.lower() in ("normal clearing",):
            status = "completed"
        elif cause in ("19", "20") or "no answer" in cause_txt.lower():
            status = "missed"
        else:
            status = "failed"
        duration = 0
        try:
            duration = max(0, int(float(event.get("CallDuration") or 0)))
        except (TypeError, ValueError):
            pass
        return {
            "external_call_id": uniqueid,
            "caller": caller,
            "callee": callee or channel,
            "direction": direction,
            "status": status,
            "started_at": started_at,
            "ended_at": started_at,
            "duration": duration,
            "metadata": {"channel": channel, "context": context, "hangup_cause": cause_txt or cause},
        }

    return None


async def _post_to_backend(payload: dict) -> None:
    """POST fire-and-forget al backend; fallo → warning (R3: nunca rompe nada)."""
    if not SERVICE_TOKEN:
        logger.warning("SERVICE_TOKEN vacío — evento no enviado: %s", payload.get("external_call_id"))
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{BACKEND_INTERNAL_URL}/api/v1/calls/events",
                json=payload,
                headers={"X-Service-Token": SERVICE_TOKEN},
            )
            if resp.status_code >= 300:
                logger.warning(
                    "backend rechazó evento call (external=%s): %s %s",
                    payload.get("external_call_id"), resp.status_code, resp.text[:200],
                )
    except Exception as exc:  # noqa: BLE001 — R3
        logger.warning(
            "backend no disponible para evento call (external=%s): %s",
            payload.get("external_call_id"), exc,
        )


# ─── Bucle principal ────────────────────────────────────────────

async def _ami_loop() -> None:
    """Conexión AMI con reconexión por backoff; reenvía eventos al backend."""
    backoff_idx = 0
    while True:
        client = AmiClient(AMI_HOST, AMI_PORT, AMI_USER, AMI_PASS)
        try:
            await client.connect()
            backoff_idx = 0
            logger.info("call-bridge escuchando AMI %s:%s", AMI_HOST, AMI_PORT)
            while True:
                try:
                    event = await client.read_event()
                except asyncio.TimeoutError:
                    continue  # poll normal: sin evento en el intervalo
                if not event:
                    continue
                payload = _build_event_payload(event)
                if payload is not None:
                    await _post_to_backend(payload)
        except asyncio.CancelledError:
            await client.close()
            raise
        except Exception as exc:  # noqa: BLE001 — reconexión con backoff
            await client.close()
            delay = RECONNECT_BACKOFF[min(backoff_idx, len(RECONNECT_BACKOFF) - 1)]
            backoff_idx += 1
            logger.warning(
                "AMI desconectado (%s) — reconexión en %ss (intento %s)",
                exc, delay, backoff_idx,
            )
            await asyncio.sleep(delay)


async def _ari_originate_http() -> None:
    """Mini-servidor HTTP interno para Originate (contrato con el backend).

    POST /api/v1/bridge/originate
    Body: {external_call_id, tenant_id, target, extension}
    → 202 {accepted: true} | 400 | 502 (si ARI falla)
    El backend ya registró el CallRecord outbound (status=ringing) y publicó
    call.new; aquí SOLO se dispara el Originate ARI (CA-F2.8). Si ARI falla,
    el bridge re-intentará por external_call_id al reiniciar (R8) o el
    operador reintenta desde el panel.
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silenciar access log por defecto
            logger.debug("bridge http: " + fmt, *args)

        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):  # noqa: N802
            if self.path != "/api/v1/bridge/originate":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                self._send(400, {"error": "json inválido"})
                return
            target = body.get("target")
            extension = body.get("extension")
            if not target or not extension:
                self._send(400, {"error": "target y extension requeridos"})
                return
            try:
                asyncio.run_coroutine_threadsafe(
                    originate(target, extension), _loop,
                ).result(timeout=15)
                self._send(202, {"accepted": True, "external_call_id": body.get("external_call_id")})
            except Exception as exc:  # noqa: BLE001
                logger.warning("Originate ARI falló (%s): %s", target, exc)
                self._send(502, {"error": f"ari originate falló: {exc}"})

    server = ThreadingHTTPServer(("127.0.0.1", 8090), Handler)
    logger.info("call-bridge HTTP interno escuchando en 127.0.0.1:8090")
    await asyncio.to_thread(server.serve_forever)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "call-bridge iniciando — AMI %s:%s ARI %s:%s backend %s",
        AMI_HOST, AMI_PORT, ARI_HOST, ARI_PORT, BACKEND_INTERNAL_URL,
    )
    global _loop
    _loop = asyncio.get_running_loop()
    await asyncio.gather(_ami_loop(), _ari_originate_http())


if __name__ == "__main__":
    asyncio.run(main())
