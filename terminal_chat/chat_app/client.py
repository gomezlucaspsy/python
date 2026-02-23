from __future__ import annotations

import argparse
import asyncio
import getpass
import ssl
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel

from .common import Envelope, ProtocolError, parse_line

console = Console()


@dataclass(slots=True)
class ClientConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    insecure_tls: bool


async def prompt_loop(writer: asyncio.StreamWriter) -> None:
    help_text = (
        "[bold]Commands[/bold]\n"
        "[cyan]/help[/cyan] Show commands\n"
        "[cyan]/users[/cyan] List online users\n"
        "[cyan]/dm <username> <message>[/cyan] Direct message\n"
        "[cyan]/quit[/cyan] Exit"
    )
    console.print(Panel(help_text, title="Terminal Chat", expand=False))

    while True:
        raw = await asyncio.to_thread(input, "You> ")
        text = raw.strip()

        if not text:
            continue

        if text == "/help":
            console.print(Panel(help_text, title="Commands", expand=False))
            continue

        if text == "/users":
            writer.write(Envelope("users", {}).to_json_line())
            await writer.drain()
            continue

        if text == "/quit":
            writer.write(Envelope("quit", {}).to_json_line())
            await writer.drain()
            break

        if text.startswith("/dm "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                console.print("[yellow]Usage:[/yellow] /dm <username> <message>")
                continue
            writer.write(Envelope("dm", {"to": parts[1], "text": parts[2]}).to_json_line())
            await writer.drain()
            continue

        writer.write(Envelope("chat", {"text": text}).to_json_line())
        await writer.drain()


async def reader_loop(reader: asyncio.StreamReader) -> None:
    while True:
        line = await reader.readline()
        if not line:
            console.print("[red]Disconnected from server[/red]")
            break

        try:
            envelope = parse_line(line)
        except ProtocolError as exc:
            console.print(f"[red]Protocol error:[/red] {exc}")
            continue

        payload = envelope.payload

        if envelope.type == "system":
            console.print(f"[dim]{payload.get('text', '')}[/dim]")
        elif envelope.type == "chat":
            console.print(f"[bold cyan]{payload.get('from', 'unknown')}[/bold cyan]: {payload.get('text', '')}")
        elif envelope.type == "dm":
            console.print(f"[bold magenta][DM][/bold magenta] {payload.get('from', 'unknown')}: {payload.get('text', '')}")
        elif envelope.type == "users":
            users = payload.get("users", [])
            console.print(f"[green]Online users:[/green] {', '.join(users)}")
        elif envelope.type == "auth_error":
            console.print(f"[red]Authentication failed:[/red] {payload.get('reason', 'Unknown reason')}")
            break
        elif envelope.type == "auth_ok":
            console.print(f"[green]Authenticated as {payload.get('username')}[/green]")


async def run_client(config: ClientConfig) -> None:
    ssl_context: ssl.SSLContext | None = None
    if config.use_tls:
        ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        if config.insecure_tls:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

    reader, writer = await asyncio.open_connection(config.host, config.port, ssl=ssl_context)

    writer.write(
        Envelope(
            "auth",
            {
                "username": config.username,
                "password": config.password,
            },
        ).to_json_line()
    )
    await writer.drain()

    read_task = asyncio.create_task(reader_loop(reader))
    write_task = asyncio.create_task(prompt_loop(writer))

    done, pending = await asyncio.wait({read_task, write_task}, return_when=asyncio.FIRST_COMPLETED)

    for task in pending:
        task.cancel()

    writer.close()
    await writer.wait_closed()

    for task in done:
        exc = task.exception()
        if exc:
            raise exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Secure terminal chat client")
    parser.add_argument("--host", default="127.0.0.1", help="Chat server host")
    parser.add_argument("--port", type=int, default=9000, help="Chat server port")
    parser.add_argument("--username", required=True, help="Username")
    parser.add_argument("--tls", action="store_true", help="Enable TLS")
    parser.add_argument("--insecure-tls", action="store_true", help="Disable certificate verification")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    password = getpass.getpass("Password: ")

    config = ClientConfig(
        host=args.host,
        port=args.port,
        username=args.username,
        password=password,
        use_tls=args.tls,
        insecure_tls=args.insecure_tls,
    )

    try:
        asyncio.run(run_client(config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Client closed[/yellow]")


if __name__ == "__main__":
    main()
