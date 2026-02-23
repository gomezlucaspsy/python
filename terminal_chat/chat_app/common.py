from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

MAX_MESSAGE_BYTES = 8_192


@dataclass(slots=True)
class Envelope:
    type: str
    payload: dict[str, Any]

    def to_json_line(self) -> bytes:
        return (json.dumps({"type": self.type, "payload": self.payload}) + "\n").encode("utf-8")


class ProtocolError(Exception):
    pass


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_line(line: bytes) -> Envelope:
    if len(line) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message exceeds maximum size")

    try:
        decoded = line.decode("utf-8").strip()
        data = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("Invalid JSON payload") from exc

    if not isinstance(data, dict):
        raise ProtocolError("Protocol payload must be a JSON object")

    message_type = data.get("type")
    payload = data.get("payload", {})

    if not isinstance(message_type, str):
        raise ProtocolError("Missing or invalid message type")
    if not isinstance(payload, dict):
        raise ProtocolError("Payload must be an object")

    return Envelope(type=message_type, payload=payload)
