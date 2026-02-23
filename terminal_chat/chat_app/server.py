from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import ssl
from dataclasses import dataclass
from pathlib import Path

from .common import Envelope, ProtocolError, now_utc_iso, parse_line
from .security import hash_password, verify_password


@dataclass(slots=True)
class Session:
    username: str
    writer: asyncio.StreamWriter


class ChatServer:
    def __init__(self, users_file: Path) -> None:
        self.users_file = users_file
        self.credentials = self._load_users(users_file)
        self.sessions: dict[str, Session] = {}
        self.lock = asyncio.Lock()

    @staticmethod
    def _load_users(path: Path) -> dict[str, str]:
        if not path.exists():
            raise FileNotFoundError(
                f"Users file not found: {path}. Create it with: python -m chat_app.server --create-user <name>"
            )

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Users file must be a JSON object: {\"username\": \"password_hash\"}")
        return {str(username): str(password_hash) for username, password_hash in data.items()}

    async def send(self, writer: asyncio.StreamWriter, message_type: str, payload: dict) -> None:
        writer.write(Envelope(message_type, payload).to_json_line())
        await writer.drain()

    async def send_system(self, writer: asyncio.StreamWriter, text: str) -> None:
        await self.send(writer, "system", {"text": text, "timestamp": now_utc_iso()})

    async def broadcast(self, sender: str, text: str) -> None:
        payload = {"from": sender, "text": text, "timestamp": now_utc_iso()}
        packet = Envelope("chat", payload).to_json_line()

        async with self.lock:
            targets = [session.writer for name, session in self.sessions.items() if name != sender]

        for writer in targets:
            writer.write(packet)

        for writer in targets:
            await writer.drain()

    async def direct_message(self, sender: str, target_user: str, text: str) -> bool:
        async with self.lock:
            target = self.sessions.get(target_user)

        if not target:
            return False

        await self.send(
            target.writer,
            "dm",
            {"from": sender, "text": text, "timestamp": now_utc_iso()},
        )
        return True

    async def auth_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> str | None:
        await self.send_system(writer, "Authenticate with username/password to join.")
        line = await reader.readline()
        if not line:
            return None

        try:
            envelope = parse_line(line)
        except ProtocolError:
            await self.send_system(writer, "Invalid auth packet.")
            return None

        if envelope.type != "auth":
            await self.send_system(writer, "First packet must be auth.")
            return None

        username = str(envelope.payload.get("username", "")).strip()
        password = str(envelope.payload.get("password", ""))
        stored_hash = self.credentials.get(username)

        if not username or not stored_hash or not verify_password(password, stored_hash):
            await self.send(writer, "auth_error", {"reason": "Invalid credentials"})
            return None

        async with self.lock:
            if username in self.sessions:
                await self.send(writer, "auth_error", {"reason": "User already connected"})
                return None
            self.sessions[username] = Session(username=username, writer=writer)

        await self.send(writer, "auth_ok", {"username": username})
        return username

    async def remove_session(self, username: str) -> None:
        async with self.lock:
            self.sessions.pop(username, None)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = writer.get_extra_info("peername")
        username: str | None = None

        try:
            username = await self.auth_client(reader, writer)
            if not username:
                return

            await self.broadcast("system", f"{username} joined the chat")
            await self.send_system(writer, "Connected. Use /users to list active users.")

            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    envelope = parse_line(line)
                except ProtocolError as exc:
                    await self.send_system(writer, f"Protocol error: {exc}")
                    continue

                if envelope.type == "chat":
                    text = str(envelope.payload.get("text", "")).strip()
                    if text:
                        await self.broadcast(username, text)

                elif envelope.type == "dm":
                    target_user = str(envelope.payload.get("to", "")).strip()
                    text = str(envelope.payload.get("text", "")).strip()
                    if target_user and text:
                        sent = await self.direct_message(username, target_user, text)
                        if sent:
                            await self.send_system(writer, f"DM sent to {target_user}")
                        else:
                            await self.send_system(writer, f"User '{target_user}' is offline")

                elif envelope.type == "users":
                    async with self.lock:
                        users = sorted(self.sessions.keys())
                    await self.send(writer, "users", {"users": users, "timestamp": now_utc_iso()})

                elif envelope.type == "quit":
                    break

                else:
                    await self.send_system(writer, f"Unknown message type: {envelope.type}")

        except Exception as exc:  # noqa: BLE001
            print(f"[server] error handling {peer}: {exc}")
        finally:
            if username:
                await self.remove_session(username)
                await self.broadcast("system", f"{username} left the chat")
            writer.close()
            await writer.wait_closed()


def build_ssl_context(certfile: Path, keyfile: Path) -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
    return context


async def run_server(host: str, port: int, users_file: Path, tls_cert: Path | None, tls_key: Path | None) -> None:
    server = ChatServer(users_file)
    ssl_context = build_ssl_context(tls_cert, tls_key) if tls_cert and tls_key else None

    async_server = await asyncio.start_server(server.handle_client, host=host, port=port, ssl=ssl_context)
    addrs = ", ".join(str(sock.getsockname()) for sock in (async_server.sockets or []))
    tls_suffix = " with TLS" if ssl_context else ""
    print(f"[server] listening on {addrs}{tls_suffix}")

    async with async_server:
        await async_server.serve_forever()


def create_user(users_file: Path, username: str) -> None:
    if not username.strip():
        raise SystemExit("Username cannot be empty")

    if users_file.exists():
        data = json.loads(users_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit("Users file must be a JSON object")
    else:
        data = {}

    if username in data:
        raise SystemExit(f"User '{username}' already exists in {users_file}")

    password = getpass.getpass("Password for new user: ")
    password_confirm = getpass.getpass("Confirm password: ")

    if not password:
        raise SystemExit("Password cannot be empty")
    if password != password_confirm:
        raise SystemExit("Passwords do not match")

    data[username] = hash_password(password)
    users_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[server] created user '{username}' in {users_file}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Secure terminal chat server")
    parser.add_argument("--host", default="0.0.0.0", help="Server bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=9000, help="Server bind port (default: 9000)")
    parser.add_argument("--users", type=Path, default=Path("users.json"), help="JSON credentials file")
    parser.add_argument("--tls-cert", type=Path, default=None, help="PEM certificate path")
    parser.add_argument("--tls-key", type=Path, default=None, help="PEM private key path")
    parser.add_argument("--create-user", default=None, help="Create a user in credentials file and exit")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.create_user:
        create_user(args.users, args.create_user)
        return

    if bool(args.tls_cert) ^ bool(args.tls_key):
        raise SystemExit("Both --tls-cert and --tls-key are required together")

    try:
        asyncio.run(run_server(args.host, args.port, args.users, args.tls_cert, args.tls_key))
    except KeyboardInterrupt:
        print("\n[server] shutdown")


if __name__ == "__main__":
    main()
