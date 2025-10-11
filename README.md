# Badges

[![Developer](https://img.shields.io/badge/developer-EntySec-blue.svg)](https://entysec.com)
[![Language](https://img.shields.io/badge/language-Python-blue.svg)](https://github.com/EntySec/Badges)
[![Forks](https://img.shields.io/github/forks/EntySec/Badges?style=flat&color=green)](https://github.com/EntySec/Badges/forks)
[![Stars](https://img.shields.io/github/stars/EntySec/Badges?style=flat&color=yellow)](https://github.com/EntySec/Badges/stargazers)
[![CodeFactor](https://www.codefactor.io/repository/github/EntySec/Badges/badge)](https://www.codefactor.io/repository/github/EntySec/Badges)

Tiny, dependency-light helpers for **beautiful terminal output**, **interactive prompts**, a **less-style pager**, **structured tables**, and a cute **ASCII world map**.
Designed to drop straight into scripts and CLIs.

---

## Features

* **Pretty status lines**: `[*]`, `[+]`, `[-]`, `[!]`, `[i]` with color and bold.
* **Interactive input** with history and ANSI prompts (`prompt_toolkit`).
* **Built-in pager** (less-like) for long output (`Enter` / `Space` / `a` / `q`).
* **Logging** of all output and prompts to a file (opt-in).
* **Tables**: quick, readable ASCII tables.
* **ASCII World Map**: plot a dot by latitude/longitude.
* **Command wrapper**: utilities for building interactive shells.

---

## Installation

> **Note:** This project is typically installed from source/git.

```bash
pip install git+https://github.com/EntySec/Badges
```

---

## Quick Start

```python
from badges import Badges

ui = Badges()

# Optional: configure once per process
ui.set_less(True)                      # enable less-like paging
ui.set_log("mytool.log")               # log all prints & prompts
ui.set_history(".mytool_history")      # persistent input history

ui.print_process("Starting...")
ui.print_success("All good.")
ui.print_warning("Heads up.")
ui.print_error("Something went wrong.")
ui.print_information("FYI only.")

answer = ui.input_question("Proceed? [y/N]: ")
if answer.lower() in ("y", "yes"):
    ui.print_process("Continuing...")
else:
    ui.print_warning("Aborted by user.")
```

---

## API Overview

The package exposes four main entry points:

```python
from badges import Badges, Tables, Map
```

### 1) `Badges` (printing & input)

`Badges` extends the `IO` class (see below). It provides convenience prefixed prints and inputs:

#### Printing

* `print_empty(message, *, start='%remove%end', end='%newline', time=False, log=None, less=None)`
* `print_usage(message, start='%remove', ...)` → `Usage: ...`
* `print_process(message, start='%remove', ...)` → `%bold%blue[*]%end ` prefix
* `print_success(message, start='%remove', ...)` → `%bold%green[+]%end `
* `print_error(message, start='%remove', ...)` → `%bold%red[-]%end `
* `print_warning(message, start='%remove', ...)` → `%bold%yellow[!]%end `
* `print_information(message, start='%remove', ...)` → `%bold%white[i]%end `

Where `start`/`end` accept **ColorScript** tokens. Common tokens include:

* `%bold`, `%red`, `%green`, `%blue`, `%yellow`, `%white`
* `%end` (reset styles), `%newline` (append newline), `%remove` (clear line), `%clear` (clear screen), `%line` (underline)

> The underlying render call is `IO.print(message, start, end, time, log, less)`.

#### Input

* `input_empty(message='', start='%end', end='', **ptk_kwargs) -> str`
* `input_question(message, start='%end', ...) -> str` → `%bold%white[?]%end ` prompt
* `input_arrow(message, start='%end', ...) -> str` → `%bold%white[>]%end ` prompt

Input uses a single `PromptSession` with optional history (`set_history(path)`).

#### Global configuration (module-global state)

* `set_log(path: str)` – when set, **every** print and prompt is appended to `path`.
* `set_history(path: str)` – enables `prompt_toolkit.FileHistory(path)` for inputs.
* `set_less(enabled: bool)` – turns the **pager** on/off globally (default: `True` if unset).

You can temporarily override per call via `log=` or `less=` parameters to `print()`.

#### Examples

Timestamped messages:

```python
ui.print_process("Connecting...", time=True)  # [*] 14:32:10 - Connecting...
```

Disable pager for a single long line:

```python
ui.print_information(big_text, less=False)
```

Sensitive input (avoid logging this one):

```python
ui.set_log("app.log")
secret = ui.input_question("Enter API key: ", log=False)
```

---

### 2) `IO` (base class used by `Badges`)

Core lower-level I/O utilities:

* `print(message='', start='%remove%end', end='%newline', time=False, log: Optional[bool]=None, less: Optional[bool]=None) -> None`
  Renders `start + message + end` via `ColorScript` and prints via:

  * **Pager** (`print_less`) when `less` is `True`.
  * Direct `stdout` otherwise.
    If `log` is enabled (globally or via arg), writes the **rendered** string to file.

* `input(message='', start='%end', end='', **kwargs) -> str`
  Builds the prompt (with ANSI) and returns the user’s input. If `log` is enabled, logs the prompt **and** the typed response.

* `set_log(path)`, `set_history(path)`, `set_less(bool)` – global setters described above.

* `print_less(data: str)`
  A simple pager:

  * Shows `(rows - 3)` lines per “screen”.
  * Controls: **Enter** (advance one line), **Space** (+10 lines), **a** (show all), **q** (quit).

* `suppress_function(fn, *a, **kw) -> Any`
  Run a function while **suppressing** its `stdout`/`stderr`.

* `print_function(fn, *a, **kw) -> Any`
  Run a function, **capture** its `stdout`/`stderr`, then print the captured output (through the pager).

**Tip:** In CI/non-TTY environments the pager may wait for a keypress. Disable it with `set_less(False)` or pass `less=False` on prints.

---

### 3) `Tables` (quick ASCII tables)

```python
from badges import Tables

tbl = Tables()
rows = [
    ("111", "Ivan Nikolskiy"),
    ("112", "Jane Doe"),
]
tbl.print_table("Users", ("ID", "Name"), *rows)
```

Sample output:

```
Users:

    ID      Name
    --      ----
    111     Ivan Nikolskiy
    112     Jane Doe
```

**Notes**

* The implementation is deliberately simple and favors readability over speed.
* It handles ANSI sequences by adjusting width so colored cells align.
* Optional `extra_fill=` kwarg sets padding per column (default `4`).

---

### 4) `Map` (ASCII world map)

```python
from badges import Map

m = Map()                       # 'world' map, red dot by default
m.deploy(55.751244, 37.618423)  # Moscow
print(m.get_map())
```

You’ll get a world ASCII map with a colored dot marking the point.
Constructor options:

* `Map(map_name='world', dot='%red*%end')`

Helpers:

* `location(latitude, longitude) -> (x, y)`
* `deploy(latitude, longitude) -> None`
* `get_map() -> str`

---

## Building an Interactive Shell

`badges/cmd.py` provides a higher-level scaffold (`Cmd`) for CLI shells with:

* Intro and customizable prompt (ColorScript aware).
* Command discovery (internal `do_<name>` methods and external command modules).
* Shortcuts (aliases), autocompletion, history, `!` system-command passthrough, etc.

Minimal sketch:

```python
from badges.cmd import Cmd, Command

class Hello(Cmd):
    def do_hello(self, args):
        """Say hello."""
        self.print_success("Hello!")

if __name__ == "__main__":
    shell = Hello(prompt='%green$ %end', intro='%bold%lineDemo%end')
    shell.loop()
```

See `badges/cmd.py` for the full capabilities: external command loading, `verify_command`, argument parsing utilities, and built-ins like `help`, `clear`, `exit`, `source`, `!` (system).

---

## Patterns & Recipes

### Capture noisy function output

```python
ui = Badges()

def noisy():
    print("stdout noise")
    import sys
    print("stderr noise", file=sys.stderr)
    return 42

result = ui.suppress_function(noisy)  # prints nothing, returns 42
ui.print_information("Now showing captured output:")
ui.print_function(noisy)              # prints via pager
```

### Make paging optional (TTY-aware)

```python
import sys
ui = Badges()
ui.set_less(sys.stdout.isatty())
```

### Separate log for audit

```python
ui = Badges()
ui.set_log("audit.log")
ui.print_process("Starting up", time=True)
name = ui.input_question("Name: ")
```

---

## FAQ

**Q: Why do my logs contain escape sequences?**
A: The library writes the **rendered** line (with ANSI codes) to the log file. Some viewers will show them literally; others will colorize. If you need plain text logs, strip ANSI codes yourself.

**Q: Can I disable logging for a specific prompt or print?**
A: Yes. Pass `log=False` into `print()` or `input()` calls.

**Q: The pager is blocking in my CI.**
A: Disable it globally with `set_less(False)` or per call with `less=False`.

**Q: Are `Badges` objects thread-safe?**
A: No. They share module-global state (`log`, `history`, `less`, and a singleton `PromptSession`). Keep I/O on the main thread or add your own synchronization.

---

## Contributing

* Keep APIs small and predictable.
* Mind cross-platform behavior of `getch` and terminal sizes.
* PRs for table formatting and pager ergonomics are welcome.
