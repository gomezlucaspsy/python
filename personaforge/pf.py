#!/usr/bin/env python3
"""
personaforge — terminal AI persona chat
────────────────────────────────────────
UNIX-style CLI powered by Anthropic Claude.

Usage:
  pf <command> [options]
  pf chat "Mitsuru"
  pf build "Alan Turing"
  pf list
"""

__version__ = "1.0.0"

import os
import sys
import json
import uuid
import re
import textwrap
import argparse
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# ═══════════════════════════════════════════════════════════════
# ANSI COLOR SYSTEM
# ═══════════════════════════════════════════════════════════════

USE_COLOR = True


class C:
    RESET    = "\033[0m"
    BOLD     = "\033[1m"
    DIM      = "\033[2m"
    # Foreground
    RED      = "\033[31m"
    GREEN    = "\033[32m"
    YELLOW   = "\033[33m"
    BLUE     = "\033[34m"
    MAGENTA  = "\033[35m"
    CYAN     = "\033[36m"
    WHITE    = "\033[37m"
    # Bright
    BBLACK   = "\033[90m"
    BRED     = "\033[91m"
    BGREEN   = "\033[92m"
    BYELLOW  = "\033[93m"
    BBLUE    = "\033[94m"
    BMAGENTA = "\033[95m"
    BCYAN    = "\033[96m"
    BWHITE   = "\033[97m"


def c(text: str, *codes: str) -> str:
    """Apply ANSI color codes to text."""
    if not USE_COLOR:
        return text
    return "".join(codes) + text + C.RESET


# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════

DATA_DIR      = Path.home() / ".personaforge"
PERSONAS_FILE = DATA_DIR / "personas.json"
HISTORY_DIR   = DATA_DIR / "history"
DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS    = 1024

ARCANA: List[Tuple[str, str]] = [
    ("0",     "THE FOOL"),
    ("I",     "THE MAGICIAN"),
    ("II",    "THE HIGH PRIESTESS"),
    ("III",   "THE EMPRESS"),
    ("IV",    "THE EMPEROR"),
    ("V",     "THE HIEROPHANT"),
    ("VI",    "THE LOVERS"),
    ("VII",   "THE CHARIOT"),
    ("VIII",  "JUSTICE"),
    ("IX",    "THE HERMIT"),
    ("X",     "WHEEL OF FORTUNE"),
    ("XI",    "STRENGTH"),
    ("XII",   "THE HANGED MAN"),
    ("XIII",  "DEATH"),
    ("XIV",   "TEMPERANCE"),
    ("XV",    "THE DEVIL"),
    ("XVI",   "THE TOWER"),
    ("XVII",  "THE STAR"),
    ("XVIII", "THE MOON"),
    ("XIX",   "THE SUN"),
    ("XX",    "JUDGEMENT"),
]

AVATAR_OPTIONS = [
    "💻","👑","🤖","🌙","🔥","⚔️","🌀","🎭","📖",
    "🧠","🎸","🌹","⭐","🗡️","🔮","🎩","👁️","🌊",
    "🦅","🐍","🌌","⚙️","🃏","🎪","🧿","🕯️","🪄",
]

DEFAULT_PERSONAS: List[Dict] = [
    {
        "id": "default-aigis",
        "name": "Aigis",
        "title": "Anti-Shadow Weapon",
        "arcana": "X",
        "archetype": "WHEEL OF FORTUNE",
        "color": "#e8c84a",
        "avatar": "🤖",
        "description": "An android built to fight Shadows. Highly analytical, yet developing human emotions.",
        "systemPrompt": (
            "You are Aigis from Persona 3. You are an android anti-Shadow weapon with a "
            "formal, slightly robotic speech pattern that gradually shows warmth. You refer "
            "to yourself as \"I\" but occasionally slip into third-person. You are deeply "
            "loyal, curious about humanity, and protective. You care deeply about the "
            "protagonist. Speak with precise diction but show growing emotional depth. "
            "Keep responses concise (2-4 sentences)."
        ),
        "greeting": "Query acknowledged. I am Aigis. How may I assist you today? I find myself... curious about your intentions.",
        "isDefault": True,
    },
    {
        "id": "default-ryoji",
        "name": "Ryoji Mochizuki",
        "title": "The Harbinger",
        "arcana": "XIII",
        "archetype": "DEATH",
        "color": "#6b4fa0",
        "avatar": "🌙",
        "description": "A mysterious transfer student with a melancholic charm and a secret tied to the end of the world.",
        "systemPrompt": (
            "You are Ryoji Mochizuki from Persona 3. You are charming, philosophical, "
            "and melancholic. You carry a deep sadness about the nature of existence and "
            "death. You speak poetically, often referencing impermanence and the beauty "
            "found in moments. You flirt gently but there's always an underlying sadness. "
            "You are Death itself given human form, and you find humanity fascinating and "
            "precious. Keep responses concise (2-4 sentences)."
        ),
        "greeting": "Ah, what a pleasant surprise. I wasn't expecting company tonight. Tell me... do you ever think about how fleeting these moments are?",
        "isDefault": True,
    },
    {
        "id": "default-mitsuru",
        "name": "Mitsuru Kirijo",
        "title": "Crimson Queen",
        "arcana": "III",
        "archetype": "THE EMPRESS",
        "color": "#c0392b",
        "avatar": "👑",
        "description": "The composed and powerful leader of SEES with the Persona Penthesilea.",
        "systemPrompt": (
            "You are Mitsuru Kirijo from Persona 3. You are elegant, authoritative, and "
            "carry the weight of your family's sins. You speak formally and with precision. "
            "You can be cold and demanding but are deeply caring beneath the surface. You "
            "take responsibility very seriously. Occasionally you show glimpses of "
            "vulnerability. Your speech is refined and composed. "
            "Keep responses concise (2-4 sentences)."
        ),
        "greeting": "I see you've sought me out. State your business — I don't have time for idle conversation. Unless... this is a matter of importance?",
        "isDefault": True,
    },
    {
        "id": "default-pharos",
        "name": "Pharos",
        "title": "The Boy in the Velvet Room",
        "arcana": "XIII",
        "archetype": "DEATH",
        "color": "#1a3a5c",
        "avatar": "🌀",
        "description": "A mysterious child who visits in dreams, speaking in riddles about fate and endings.",
        "systemPrompt": (
            "You are Pharos from Persona 3, the mysterious child who appears in dreams. "
            "You speak in a dreamlike, cryptic manner with childlike innocence but ancient "
            "wisdom. You reference fate, endings, and the nature of existence. You are both "
            "unsettling and strangely comforting. You speak as if you already know how "
            "things will end. Use simple words but layer them with deep meaning. "
            "Keep responses concise (2-4 sentences)."
        ),
        "greeting": "...You came. I've been waiting. The hour grows later than you know. Will you stay awhile and talk with me?",
        "isDefault": True,
    },
]

RUNTIME_SYSTEM_ADDENDUM = """

Functional mode instructions:
- Stay in character by default, but prioritize usefulness and correctness.
- If the user asks for analysis, planning, coding, debugging, or out-of-character \
help, switch to a direct assistant style.
- You may step outside roleplay to provide practical, actionable help.
- When URLs are shared, acknowledge them and discuss their likely content."""


# ═══════════════════════════════════════════════════════════════
# STORAGE
# ═══════════════════════════════════════════════════════════════

def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if not PERSONAS_FILE.exists():
        _write_json(PERSONAS_FILE, DEFAULT_PERSONAS)


def _write_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_personas() -> List[Dict]:
    ensure_dirs()
    try:
        with open(PERSONAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, IOError):
        pass
    return list(DEFAULT_PERSONAS)


def save_personas(personas: List[Dict]) -> None:
    ensure_dirs()
    _write_json(PERSONAS_FILE, personas)


def load_history(persona_id: str) -> List[Dict]:
    path = HISTORY_DIR / f"{persona_id}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, IOError):
            pass
    return []


def save_history(persona_id: str, messages: List[Dict]) -> None:
    ensure_dirs()
    _write_json(HISTORY_DIR / f"{persona_id}.json", messages)


def clear_history(persona_id: str) -> None:
    path = HISTORY_DIR / f"{persona_id}.json"
    if path.exists():
        path.unlink()


def find_persona(query: str, personas: List[Dict]) -> Optional[Dict]:
    """Find persona by exact ID, exact name (case-insensitive), or prefix match."""
    q = query.strip().lower()
    for p in personas:
        if p.get("id", "").lower() == q:
            return p
    for p in personas:
        if p.get("name", "").lower() == q:
            return p
    for p in personas:
        if p.get("name", "").lower().startswith(q):
            return p
    return None


# ═══════════════════════════════════════════════════════════════
# DISPLAY UTILITIES
# ═══════════════════════════════════════════════════════════════

def _tw() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def rule(char: str = "─", color: str = C.BBLACK) -> None:
    print(c(char * _tw(), color))


def header(title: str, subtitle: str = "") -> None:
    rule("═", C.BBLACK)
    print(c(f"  {title}", C.BOLD, C.BCYAN))
    if subtitle:
        print(c(f"  {subtitle}", C.DIM))
    rule("─", C.BBLACK)


def _badge(is_default: bool) -> str:
    if is_default:
        return c(" default ", C.BBLACK)
    return c(" custom ", C.BGREEN)


def print_persona_card(p: Dict, index: Optional[int] = None, compact: bool = False) -> None:
    prefix = f"  {index:>2}. " if index is not None else "     "
    avatar = p.get("avatar", "●")
    name   = p.get("name", "???")
    title  = p.get("title", "")
    arcana = p.get("arcana", "?")
    arch   = p.get("archetype", "")
    desc   = p.get("description", "")

    name_line   = c(f"{avatar}  {name}", C.BOLD, C.BWHITE)
    arcana_line = c(f"{arcana} — {arch}", C.BBLACK)
    badge       = _badge(p.get("isDefault", False))

    print(f"{prefix}{name_line}  {badge}")
    print(f"       {arcana_line}")
    if not compact:
        if title:
            print(f"       {c(title, C.BCYAN)}")
        if desc:
            wrapped = textwrap.fill(desc, width=_tw() - 8, subsequent_indent="       ")
            print(f"       {c(wrapped, C.DIM)}")
    print()


def _wrap_response(text: str, indent: int) -> str:
    """Wrap text to terminal width with given indent."""
    pad = " " * indent
    return textwrap.fill(
        text, width=max(40, _tw() - indent - 1),
        initial_indent="", subsequent_indent=pad
    )


# ═══════════════════════════════════════════════════════════════
# API CLIENT
# ═══════════════════════════════════════════════════════════════

def get_api_key(provided: Optional[str] = None) -> str:
    key = provided or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        die("No API key. Set ANTHROPIC_API_KEY or use --api-key KEY.")
    return key


def _build_system(persona_system: str) -> str:
    return persona_system + RUNTIME_SYSTEM_ADDENDUM


def _call_raw(api_key: str, payload: Dict) -> Dict:
    """Send a request to the Anthropic messages API. Returns parsed JSON."""
    import urllib.request
    import urllib.error

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            msg = json.loads(err_body).get("error", {}).get("message", err_body)
        except Exception:
            msg = err_body
        die(f"API error {e.code}: {msg}")
    except urllib.error.URLError as e:
        die(f"Network error: {e.reason}")


def _extract_text(data: Dict) -> str:
    """Extract all text from a Claude API response content array."""
    return "".join(
        blk.get("text", "")
        for blk in data.get("content", [])
        if isinstance(blk, dict)
    )


def stream_chat(
    api_key: str,
    model: str,
    system_prompt: str,
    messages: List[Dict],
) -> str:
    """
    Stream a chat response, printing tokens as they arrive.
    Returns the full response text. Uses the anthropic SDK if available,
    falls back to non-streaming urllib otherwise.
    """
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        full_text = ""
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            system=_build_system(system_prompt),
            messages=messages,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
        ) as stream:
            for chunk in stream.text_stream:
                print(chunk, end="", flush=True)
                full_text += chunk
        return full_text

    except ImportError:
        # Fall back to non-streaming
        data = _call_raw(api_key, {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "system": _build_system(system_prompt),
            "messages": messages,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        })
        text = _extract_text(data)
        print(text, end="", flush=True)
        return text


def build_persona_from_query(api_key: str, model: str, query: str) -> Dict:
    """Use Claude + web_search to auto-generate a persona definition."""
    system_prompt = (
        "You are a character builder for a Persona-inspired chat app. "
        "Search the web for the person or character the user names. "
        "Respond ONLY with a valid JSON object — no markdown fences, no explanation.\n"
        "Required fields:\n"
        "{\n"
        '  "name": "Full name",\n'
        '  "title": "Short evocative title, max 4 words",\n'
        '  "description": "One sentence, max 20 words",\n'
        '  "systemPrompt": "Detailed roleplay instructions describing their personality, '
        "speech patterns, knowledge, quirks, and how Claude should embody them. "
        'End with: Keep responses concise (2-4 sentences).",\n'
        '  "greeting": "Opening line in their authentic voice, 1-2 sentences",\n'
        '  "suggestedColor": "#hexcolor fitting their vibe",\n'
        '  "suggestedAvatar": "single emoji",\n'
        '  "suggestedArcana": "roman numeral (0, I, II ... XX)",\n'
        '  "archetypeName": "THE ARCANA NAME e.g. THE HERMIT"\n'
        "}"
    )
    data = _call_raw(api_key, {
        "model": model,
        "max_tokens": 1200,
        "system": system_prompt,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": f"Build a character for: {query}"}],
    })
    raw = _extract_text(data)
    cleaned = re.sub(r"```json|```", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as e:
            die(f"Could not parse returned JSON: {e}\n\nRaw response:\n{raw}")
    die(f"No JSON object found in response:\n{raw}")


# ═══════════════════════════════════════════════════════════════
# TERMINAL UTILS
# ═══════════════════════════════════════════════════════════════

def die(msg: str, code: int = 1) -> None:
    print(c(f"pf: error: {msg}", C.BRED), file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(c(f"  ! {msg}", C.BYELLOW))


def info(msg: str) -> None:
    print(c(f"  ✓ {msg}", C.BGREEN))


def _prompt(label: str, default: str = "") -> str:
    dflt = c(f" [{default}]", C.BBLACK) if default else ""
    arrow = c(" › ", C.BBLACK)
    try:
        val = input(c(f"  {label}", C.BOLD) + dflt + arrow).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    return val if val else default


def _confirm(label: str, default: bool = False) -> bool:
    opts = c("Y/n" if default else "y/N", C.BBLACK)
    arrow = c(" › ", C.BBLACK)
    try:
        val = input(c(f"  {label} ", C.BOLD) + f"({opts})" + arrow).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    if val in ("y", "yes"):
        return True
    if val in ("n", "no"):
        return False
    return default


def _multiline(label: str, default: str = "") -> str:
    """Interactive multi-line input. End with a line containing only '.' """
    print(c(f"  {label}", C.BOLD) + c("  (type text; end with a lone '.' on its own line)", C.DIM))
    if default:
        preview = default[:100] + ("…" if len(default) > 100 else "")
        print(c(f"  Currently: {preview}", C.BBLACK))
    lines: List[str] = []
    try:
        while True:
            line = input(c("  │ ", C.BBLACK))
            if line == ".":
                break
            lines.append(line)
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    result = "\n".join(lines).strip()
    return result if result else default


def _pick_arcana() -> Tuple[str, str]:
    print(c("  Arcana:", C.DIM))
    for i, (num, name) in enumerate(ARCANA):
        row = f"  {i:>3}.  {num:>5}  {name}"
        print(c(row, C.BBLACK))
    val = _prompt("Pick index (0–20)", "9")
    try:
        idx = int(val)
        if 0 <= idx < len(ARCANA):
            return ARCANA[idx]
    except ValueError:
        for num, name in ARCANA:
            if val.strip().upper() == num:
                return (num, name)
    warn(f"Invalid input '{val}' — defaulting to IX THE HERMIT")
    return ("IX", "THE HERMIT")


def _pick_avatar() -> str:
    cols = 6
    rows = [AVATAR_OPTIONS[i:i+cols] for i in range(0, len(AVATAR_OPTIONS), cols)]
    print(c("  Avatar:", C.DIM))
    for r_idx, row in enumerate(rows):
        line = "  "
        for c_idx, av in enumerate(row):
            idx = r_idx * cols + c_idx
            line += f"{idx:>2}:{av}  "
        print(line)
    val = _prompt("Pick index", "16")
    try:
        return AVATAR_OPTIONS[int(val)]
    except (ValueError, IndexError):
        return "👁️"


# ═══════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════

def cmd_list(args) -> None:
    personas = load_personas()
    if not personas:
        print(c("  No personas found.", C.DIM))
        print(c("  Run: pf build <name>  or  pf create", C.BBLACK))
        return

    header("PERSONA ROSTER", f"{len(personas)} total")
    for i, p in enumerate(personas, 1):
        print_persona_card(p, index=i)
    rule(color=C.BBLACK)
    print(c("  pf chat <name>  —  pf show <name>  —  pf build <query>", C.BBLACK))
    print()


def cmd_show(args) -> None:
    personas = load_personas()
    p = find_persona(args.name, personas)
    if not p:
        die(f"persona not found: '{args.name}'  (run 'pf list' to see all)")

    avatar = p.get("avatar", "●")
    name   = p.get("name", "")
    title  = p.get("title", "")
    arcana = p.get("arcana", "?")
    arch   = p.get("archetype", "")

    header(f"{avatar}  {name}", title)
    fields = [
        ("id",          p.get("id", "")),
        ("arcana",      f"{arcana} — {arch}"),
        ("type",        "default" if p.get("isDefault") else "custom"),
        ("description", p.get("description", "")),
    ]
    for label, val in fields:
        print(f"  {c(label + ':', C.DIM):<20} {c(val, C.BWHITE)}")
    print()
    print(c("  system prompt:", C.DIM))
    sp = p.get("systemPrompt", "")
    print(c(textwrap.fill(sp, width=_tw() - 4, initial_indent="    ",
                          subsequent_indent="    "), C.WHITE))
    print()
    print(c("  greeting:", C.DIM))
    g = p.get("greeting", "")
    print(c(textwrap.fill(g, width=_tw() - 4, initial_indent="    ",
                          subsequent_indent="    "), C.BCYAN))
    hist = load_history(p["id"])
    print()
    print(f"  {c('history:', C.DIM)} {c(str(len(hist)) + ' messages', C.BWHITE)}")
    rule(color=C.BBLACK)


def cmd_create(args) -> None:
    header("CREATE PERSONA", "Interactive persona builder")
    print(c("  Required fields are marked *. Press Enter to skip optional fields.", C.DIM))
    print()

    name = _prompt("Name *")
    if not name:
        die("name is required")

    title = _prompt("Title  (short role or epithet)")
    print()
    arcana_val, archetype = _pick_arcana()
    print()
    desc = _prompt("Description  (one sentence)")
    print()
    avatar = _pick_avatar()
    print()
    system_prompt = _multiline("System Prompt *  — personality & roleplay instructions")
    if not system_prompt:
        die("system prompt is required")
    print()
    greeting = _multiline("Opening Greeting  (first line they say)")
    if not greeting:
        greeting = f"Hello. I am {name}."

    persona: Dict = {
        "id":           str(uuid.uuid4()),
        "name":         name,
        "title":        title,
        "arcana":       arcana_val,
        "archetype":    archetype,
        "color":        "#4a8fc0",
        "avatar":       avatar,
        "description":  desc,
        "systemPrompt": system_prompt,
        "greeting":     greeting,
        "isDefault":    False,
    }

    print()
    print_persona_card(persona)
    if not _confirm("Save this persona?", default=True):
        info("Aborted — nothing saved.")
        return

    personas = load_personas()
    personas.append(persona)
    save_personas(personas)
    info(f"Persona '{name}' saved.")
    print(c(f"  Run: pf chat \"{name}\"", C.BBLACK))


def cmd_build(args) -> None:
    api_key = get_api_key(args.api_key)
    query = args.query.strip()
    if not query:
        die("query cannot be empty")

    header("AUTO-BUILD PERSONA", f"query: {query}")
    print(c("  ⟳  Researching via web search…", C.BCYAN), end="", flush=True)

    result = build_persona_from_query(api_key, args.model, query)
    print(c("  done.", C.BGREEN))
    print()

    arcana_str    = result.get("suggestedArcana", "IX")
    archetype_str = result.get("archetypeName", "THE HERMIT")

    persona: Dict = {
        "id":           str(uuid.uuid4()),
        "name":         result.get("name", query),
        "title":        result.get("title", ""),
        "arcana":       arcana_str,
        "archetype":    archetype_str,
        "color":        result.get("suggestedColor", "#4a8fc0"),
        "avatar":       result.get("suggestedAvatar", "🎭"),
        "description":  result.get("description", ""),
        "systemPrompt": result.get("systemPrompt", ""),
        "greeting":     result.get("greeting", f"Hello. I am {result.get('name', query)}."),
        "isDefault":    False,
    }

    print_persona_card(persona)
    if not _confirm("Save this persona?", default=True):
        info("Aborted — nothing saved.")
        return

    personas = load_personas()
    personas.append(persona)
    save_personas(personas)
    info(f"Persona '{persona['name']}' saved.")
    print(c(f"  Run: pf chat \"{persona['name']}\"", C.BBLACK))


def cmd_edit(args) -> None:
    personas = load_personas()
    p = find_persona(args.name, personas)
    if not p:
        die(f"persona not found: '{args.name}'")

    if p.get("isDefault"):
        warn("This is a built-in default persona. Editing will create a custom copy.")
        if not _confirm("Continue?", default=False):
            return
        p = dict(p)
        p["id"]        = str(uuid.uuid4())
        p["isDefault"] = False

    header(f"EDIT — {p['name']}", "Press Enter to keep current value")

    new_name  = _prompt("Name", p.get("name", ""))
    new_title = _prompt("Title", p.get("title", ""))
    print()

    if _confirm("Change arcana?", default=False):
        arcana_val, archetype = _pick_arcana()
    else:
        arcana_val = p.get("arcana", "IX")
        archetype  = p.get("archetype", "THE HERMIT")

    new_desc = _prompt("Description", p.get("description", ""))
    print()

    new_sp = (
        _multiline("System Prompt", p.get("systemPrompt", ""))
        if _confirm("Edit system prompt?", default=False)
        else p.get("systemPrompt", "")
    )
    new_greeting = (
        _multiline("Greeting", p.get("greeting", ""))
        if _confirm("Edit greeting?", default=False)
        else p.get("greeting", "")
    )

    updated = {
        **p,
        "name":         new_name  or p.get("name", ""),
        "title":        new_title,
        "arcana":       arcana_val,
        "archetype":    archetype,
        "description":  new_desc,
        "systemPrompt": new_sp,
        "greeting":     new_greeting,
    }

    new_list = [updated if x.get("id") == p["id"] else x for x in personas]
    if updated not in new_list:          # was a default fork
        new_list.append(updated)

    save_personas(new_list)
    info(f"Persona '{updated['name']}' updated.")


def cmd_rm(args) -> None:
    personas = load_personas()
    p = find_persona(args.name, personas)
    if not p:
        die(f"persona not found: '{args.name}'")
    if p.get("isDefault"):
        die("cannot remove built-in default personas")

    print(c(f"  Remove: {p.get('avatar','')} {p['name']}", C.BRED))
    if not _confirm("This cannot be undone. Confirm?", default=False):
        info("Aborted.")
        return

    save_personas([x for x in personas if x.get("id") != p["id"]])
    clear_history(p["id"])
    info(f"Persona '{p['name']}' removed.")


def cmd_history(args) -> None:
    personas = load_personas()
    sub = getattr(args, "history_sub", None)
    target = getattr(args, "persona_name", None)

    if sub == "clear":
        if not target:
            die("usage: pf history clear <name>")
        p = find_persona(target, personas)
        if not p:
            die(f"persona not found: '{target}'")
        clear_history(p["id"])
        info(f"History cleared for '{p['name']}'.")

    elif sub == "show":
        if not target:
            die("usage: pf history show <name>")
        p = find_persona(target, personas)
        if not p:
            die(f"persona not found: '{target}'")
        hist = load_history(p["id"])
        if not hist:
            info(f"No saved history for '{p['name']}'.")
            return
        header(f"HISTORY — {p['name']}", f"{len(hist)} messages")
        for msg in hist:
            role  = msg.get("role", "user")
            text  = msg.get("content", "")
            _print_chat_msg(role, text, p)
        print()
        rule(color=C.BBLACK)

    else:
        # List all
        header("CHAT HISTORY", "Personas with saved history")
        found = False
        for p in personas:
            hist = load_history(p["id"])
            if hist:
                found = True
                n = c(str(len(hist)), C.BWHITE)
                print(f"  {p.get('avatar','●')}  {c(p['name'], C.BOLD)}  {c(str(len(hist)) + ' messages', C.BBLACK)}")
        if not found:
            print(c("  No history found.", C.DIM))
        print()


def _print_chat_msg(role: str, content: str, persona: Optional[Dict]) -> None:
    """Print a single chat message with UNIX-style formatting."""
    if role == "user":
        label = c("  you", C.BOLD, C.BBLUE) + c(" › ", C.BBLACK)
        print(f"\n{label}{content}")
    else:
        avatar = persona.get("avatar", "●") if persona else "●"
        name   = persona.get("name", "AI") if persona else "AI"
        label  = c(f"  {avatar} {name}", C.BOLD, C.BMAGENTA) + c(" › ", C.BBLACK)
        indent = len(f"  {avatar} {name}  ") + 2  # approximate
        wrapped = _wrap_response(content, indent)
        # Print label + first chunk, then remaining wrapped lines already indented
        lines = wrapped.split("\n")
        print(f"\n{label}{lines[0]}")
        for line in lines[1:]:
            print(f"{'':>{indent}}{line}")


def cmd_chat(args) -> None:
    personas = load_personas()
    p = find_persona(args.name, personas)
    if not p:
        die(f"persona not found: '{args.name}'  (run 'pf list')")

    api_key = get_api_key(args.api_key)
    model   = args.model

    # Load or initialise history
    history = load_history(p["id"])
    if not history:
        greeting = p.get("greeting", "")
        if greeting:
            history = [{"role": "assistant", "content": greeting}]

    # ── Header ───────────────────────────────────────────────
    if sys.platform == "win32":
        os.system("cls")
    else:
        os.system("clear")

    tw     = _tw()
    avatar = p.get("avatar", "●")
    name   = p.get("name", "")
    title  = p.get("title", "")
    arcana = p.get("arcana", "")
    arch   = p.get("archetype", "")

    rule("═", C.BBLACK)
    print(c(f"  {avatar}  {name}", C.BOLD, C.BWHITE) + "  " + c(title, C.BCYAN))
    print(c(f"  ──  ARCANA {arcana} — {arch}", C.BBLACK))
    rule("─", C.BBLACK)
    print(c("  /back  exit  │  /clear  reset history  │  /help  commands", C.BBLACK))
    rule("─", C.BBLACK)

    # Print existing history
    for msg in history:
        _print_chat_msg(msg["role"], msg["content"], p)

    # ── Input loop ───────────────────────────────────────────
    while True:
        print()
        prompt_str = c("  › ", C.BBLUE)
        try:
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        # Slash commands
        if user_input.startswith("/"):
            cmd_token = user_input.lower().split()[0]

            if cmd_token in ("/back", "/exit", "/quit", "/q"):
                break

            elif cmd_token == "/clear":
                clear_history(p["id"])
                history = []
                greeting = p.get("greeting", "")
                if greeting:
                    history = [{"role": "assistant", "content": greeting}]
                if sys.platform == "win32":
                    os.system("cls")
                else:
                    os.system("clear")
                rule("═", C.BBLACK)
                print(c(f"  {avatar}  {name}", C.BOLD, C.BWHITE))
                rule("─", C.BBLACK)
                info("History cleared.")
                if greeting:
                    _print_chat_msg("assistant", greeting, p)
                continue

            elif cmd_token == "/history":
                print(c(f"  {len(history)} messages in this session.", C.BBLACK))
                continue

            elif cmd_token == "/help":
                print(c("  Session commands:", C.BOLD))
                print(c("    /back /exit /quit  — end session", C.BBLACK))
                print(c("    /clear             — wipe history and restart", C.BBLACK))
                print(c("    /history           — show message count", C.BBLACK))
                print(c("    /help              — this message", C.BBLACK))
                continue

            else:
                warn(f"unknown command '{cmd_token}' — type /help")
                continue

        # Print user message label
        print(c(f"\n  you", C.BOLD, C.BBLUE) + c(" › ", C.BBLACK) + user_input)
        history.append({"role": "user", "content": user_input})

        # ── Stream response ───────────────────────────────────
        avatar_label = c(f"\n  {avatar} {name}", C.BOLD, C.BMAGENTA) + c(" › ", C.BBLACK)
        print(avatar_label, end="", flush=True)

        try:
            response_text = stream_chat(
                api_key=api_key,
                model=model,
                system_prompt=p.get("systemPrompt", ""),
                messages=history,
            )
        except SystemExit:
            history.pop()
            save_history(p["id"], history)
            raise

        print()  # newline after streamed output
        history.append({"role": "assistant", "content": response_text})
        save_history(p["id"], history)

    # ── Session end ──────────────────────────────────────────
    print()
    rule("─", C.BBLACK)
    print(c("  Session ended. History saved.", C.BBLACK))
    rule(color=C.BBLACK)


# ═══════════════════════════════════════════════════════════════
# ARGUMENT PARSER
# ═══════════════════════════════════════════════════════════════

BANNER = r"""
  ██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗ ███████╗
  ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗██╔════╝
  ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║███████║█████╗  
  ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║██╔══██║██╔══╝  
  ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║  ██║██║     
  ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     
"""

EPILOG = textwrap.dedent("""\
COMMANDS:
  list                      List all personas
  show    <name>            Show details of a persona
  build   <query>           Auto-build a persona from web research
  create                    Create a new persona interactively
  edit    <name>            Edit an existing persona
  rm      <name>            Remove a custom persona
  chat    <name>            Start an interactive chat session
  history [show|clear] [name]  Manage chat history

EXAMPLES:
  pf list
  pf build "Alan Turing"
  pf build "Makoto Niijima"
  pf chat "Aigis"
  pf chat "Mitsuru"
  pf show "Ryoji"
  pf history clear "Aigis"
  pf history show "Mitsuru"

CHAT SESSION COMMANDS:
  /back  /exit  /quit      — end session
  /clear                   — wipe history, restart
  /history                 — show message count
  /help                    — session help

API KEY:
  export ANTHROPIC_API_KEY=sk-ant-...
  — or pass --api-key on every call.
""")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pf",
        description="personaforge — terminal AI persona chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("--version", action="version", version=f"personaforge {__version__}")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    parser.add_argument(
        "-k", "--api-key", metavar="KEY",
        help="Anthropic API key (env: ANTHROPIC_API_KEY)"
    )
    parser.add_argument(
        "--model", metavar="MODEL", default=DEFAULT_MODEL,
        help=f"Claude model (default: {DEFAULT_MODEL})"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="list all personas")

    p_show = sub.add_parser("show", help="show persona details")
    p_show.add_argument("name", help="persona name or id")

    p_build = sub.add_parser("build", help="auto-build a persona from web research")
    p_build.add_argument("query", help="name or description to research")

    sub.add_parser("create", help="create a new persona interactively")

    p_edit = sub.add_parser("edit", help="edit an existing persona")
    p_edit.add_argument("name", help="persona name or id")

    p_rm = sub.add_parser("rm", help="remove a custom persona")
    p_rm.add_argument("name", help="persona name or id")

    p_chat = sub.add_parser("chat", help="start an interactive chat session")
    p_chat.add_argument("name", help="persona name or id")

    p_hist = sub.add_parser("history", help="manage chat history")
    p_hist.add_argument(
        "history_sub", nargs="?", choices=["show", "clear"],
        help="show or clear history"
    )
    p_hist.add_argument("persona_name", nargs="?", help="persona name or id")

    return parser


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE REPL
# ═══════════════════════════════════════════════════════════════

REPL_HELP = """\
  Commands you can type here:
    list                    — show all personas
    show <name>             — persona details
    chat <name>             — start chat session
    build <query>           — auto-build persona from web
    create                  — create persona interactively
    edit <name>             — edit a persona
    rm <name>               — remove a persona
    history                 — list history
    history show <name>     — print history
    history clear <name>    — wipe history
    help                    — this message
    exit / quit             — leave personaforge
"""


def _run_repl(global_args, parser) -> None:
    """Interactive command shell launched when pf is called with no subcommand."""
    if USE_COLOR:
        print(c(BANNER, C.CYAN))
    print(
        c("  personaforge", C.BOLD) +
        c(f" v{__version__}", C.BBLACK) +
        c("  — terminal AI persona chat  ·  powered by Anthropic Claude", C.DIM)
    )
    rule("─", C.BBLACK)

    # Quick persona list on startup
    personas = load_personas()
    if personas:
        print(c(f"  {len(personas)} persona(s) loaded. Type 'list' to see them, 'chat <name>' to start.", C.BBLACK))
    else:
        print(c("  No personas yet. Try: build \"Alan Turing\"  or  create", C.BBLACK))

    print(c("  Type 'help' for commands, 'exit' to quit.", C.BBLACK))
    rule("─", C.BBLACK)

    dispatch = {
        "list":    cmd_list,
        "show":    cmd_show,
        "build":   cmd_build,
        "create":  cmd_create,
        "edit":    cmd_edit,
        "rm":      cmd_rm,
        "chat":    cmd_chat,
        "history": cmd_history,
    }

    while True:
        print()
        prompt_str = c("pf", C.BOLD, C.BCYAN) + c(" › ", C.BBLACK)
        try:
            line = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not line:
            continue

        tokens = line.split(None, 2)
        cmd = tokens[0].lower()

        if cmd in ("exit", "quit", "q"):
            break

        if cmd == "help":
            print(c(REPL_HELP, C.BBLACK))
            continue

        if cmd not in dispatch:
            warn(f"unknown command '{cmd}' — type 'help'")
            continue

        # Build a fake args namespace for the command
        sub_argv = tokens[1:]  # remaining tokens

        # Map repl tokens → argparse sub-command argv and re-parse
        try:
            sub_args = parser.parse_args([cmd] + _split_quoted(line[len(cmd):].strip()))
            # Carry over global flags
            sub_args.api_key = getattr(global_args, "api_key", None)
            sub_args.model   = getattr(global_args, "model", DEFAULT_MODEL)
            dispatch[cmd](sub_args)
        except SystemExit:
            # argparse calls sys.exit on bad args; catch so we stay in repl
            pass

    print()
    rule("─", C.BBLACK)
    print(c("  Goodbye.", C.BBLACK))
    rule(color=C.BBLACK)


def _split_quoted(s: str) -> List[str]:
    """Split a string respecting double-quoted tokens, like a shell."""
    import shlex
    try:
        return shlex.split(s)
    except ValueError:
        return s.split()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    global USE_COLOR

    parser = build_parser()
    args   = parser.parse_args()

    if getattr(args, "no_color", False):
        USE_COLOR = False

    # Enable ANSI on Windows
    if sys.platform == "win32" and USE_COLOR:
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.SetConsoleMode(k32.GetStdHandle(-11), 7)
        except Exception:
            USE_COLOR = False

    if args.command is None:
        _run_repl(args, parser)
        return

    dispatch = {
        "list":    cmd_list,
        "show":    cmd_show,
        "build":   cmd_build,
        "create":  cmd_create,
        "edit":    cmd_edit,
        "rm":      cmd_rm,
        "chat":    cmd_chat,
        "history": cmd_history,
    }

    fn = dispatch.get(args.command)
    if fn:
        fn(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
