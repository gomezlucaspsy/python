# personaforge

Terminal-based AI persona chat. UNIX-style CLI powered by Anthropic Claude.

```
  ██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ █████╗ ███████╗
  ██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔══██╗██╔════╝
  ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║███████║█████╗  
  ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║██╔══██║██╔══╝  
  ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║██║  ██║██║     
  ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝    
```

---

## Installation

```bash
cd personaforge
pip install -r requirements.txt
```

Set your API key:

```bash
# Windows PowerShell
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Or Linux/macOS
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Usage

```
pf <command> [options]
```

### Commands

| Command | Description |
|---|---|
| `pf list` | List all personas |
| `pf show <name>` | Show persona details |
| `pf build <query>` | Auto-build a persona from web research |
| `pf create` | Create a new persona interactively |
| `pf edit <name>` | Edit an existing persona |
| `pf rm <name>` | Remove a custom persona |
| `pf chat <name>` | Start an interactive chat session |
| `pf history` | List all personas with saved history |
| `pf history show <name>` | Print full chat history |
| `pf history clear <name>` | Wipe history for a persona |

### Options

```
-k, --api-key KEY    Anthropic API key (env: ANTHROPIC_API_KEY)
--model MODEL        Claude model (default: claude-sonnet-4-20250514)
--no-color           Disable ANSI color output
--version            Show version
```

---

## Examples

```bash
# List built-in personas
pf list

# Auto-build a persona (uses Claude + web search)
pf build "Alan Turing"
pf build "Makoto Niijima"
pf build "Ernest Hemingway"

# Chat
pf chat "Aigis"
pf chat "Alan Turing"   # after building

# Create manually
pf create

# Edit
pf edit "Aigis"

# History
pf history
pf history show "Mitsuru"
pf history clear "Aigis"
```

---

## Chat session commands

Once inside a chat session:

```
/back  /exit  /quit    — end session and return to shell
/clear                 — wipe history, restart conversation
/history               — show message count
/help                  — print session help
```

---

## Data storage

All persona definitions and chat histories are stored in:

```
~/.personaforge/
  personas.json        # all persona definitions
  history/
    <persona-id>.json  # one file per persona
```

---

## Built-in personas

Comes with four default Persona 3 characters:

- **Aigis** — Anti-Shadow Weapon  (Arcana X)
- **Ryoji Mochizuki** — The Harbinger  (Arcana XIII)
- **Mitsuru Kirijo** — Crimson Queen  (Arcana III)
- **Pharos** — The Boy in the Velvet Room  (Arcana XIII)

Default personas cannot be removed, but can be edited into custom copies.

---

## Running directly

```bash
python pf.py list
python pf.py chat "Mitsuru"
python pf.py build "Nikola Tesla"
```

Or make it executable (Linux/macOS):

```bash
chmod +x pf.py
./pf.py chat "Aigis"
```
