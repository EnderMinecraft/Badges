"""
MIT License

Copyright (c) 2020-2024 EntySec

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os
import io
import sys
import getch
import shlex
import traceback
import argparse
import subprocess

import importlib.util

from badges import Tables, Badges
from colorscript import ColorScript

from contextlib import redirect_stdout, redirect_stderr

from typing import (
    Any,
    Optional,
    Tuple,
    Union,
    Callable,
)

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.completion import NestedCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI

# prompt-toolkit types (optional import safety)
try:
    from prompt_toolkit.lexers import Lexer
except Exception:  # pragma: no cover
    Lexer = Any  # type: ignore

try:
    from prompt_toolkit.styles import BaseStyle
except Exception:  # pragma: no cover
    BaseStyle = Any  # type: ignore


def continue_or_exit() -> None:
    """ Continue loading commands or exit. """

    sys.stdout.write("Press Enter to continue, or 'q' to quit:")
    sys.stdout.flush()

    user_input = ''
    while user_input not in ['\n', 'q']:
        user_input = getch.getch()

    if user_input == 'q':
        sys.exit(0)


class Command(Tables, Badges):
    """ External command object. """

    def __init__(self, info: dict = {}) -> None:
        self.info = {
            'Category': "",
            'Name': "",
            'Authors': [],
            'Description': "",
            'Usage': "",
            'MinArgs': 0,
            'Options': [],
            'Method': None,
            'Complete': None,
            'Shorts': {}
        }
        self.info.update(info)

    @staticmethod
    def complete() -> Union[dict, None]:
        return

    def run(self, args: list) -> None:
        return


class Cmd(Tables, Badges):
    """ Wrapper for CLIs. Based on cmd.Cmd python module. """

    def __init__(self,
                 prompt: str = '%red$ %end',
                 intro: Optional[str] = '',
                 path: Optional[list] = [],
                 history: Optional[str] = None,
                 log: Optional[str] = None,
                 shorts: dict = {},
                 builtins: dict = {},
                 # NEW: prompt-toolkit customization hooks
                 lexer: Optional["Lexer"] = None,
                 style: Optional["BaseStyle"] = None,
                 session_kwargs: Optional[dict] = None,
                 **kwargs) -> None:
        """
        Initialize cmd.

        New arguments:
        - lexer: prompt_toolkit Lexer for live syntax highlighting
        - style: prompt_toolkit Style/BaseStyle
        - session_kwargs: dict merged into PromptSession constructor kwargs
        """

        self.intro = intro
        self.prompt = prompt

        self.set_intro(intro)
        self.set_prompt(prompt)

        self.internal = []
        self.external = {}
        self.shorts = shorts

        self.complete = {}
        self.dynamic_complete = {}
        self.source = []

        for name in dir(self.__class__):
            if name.startswith('do_'):
                self.internal.append(name[3:])
                self.complete[name[3:]] = None

        for commands in path:
            self.load_external(commands, **kwargs)

        # Build prompt session with overridable kwargs
        base_kwargs = dict(
            complete_while_typing=True,
            auto_suggest=AutoSuggestFromHistory(),
        )

        if session_kwargs:
            base_kwargs.update(session_kwargs)

        if history:
            base_kwargs["history"] = FileHistory(history)

        # Allow hooks at construction time
        if lexer is not None:
            base_kwargs["lexer"] = lexer
        if style is not None:
            base_kwargs["style"] = style

        self._session = PromptSession(**base_kwargs)

        self.set_log(log)

        self.builtins = {
            '!': self.system,
            '#': lambda x: x,
            '*': 'help',
            '?': 'help',
            '@': 'clear',
            '.': 'exit',
            ':': 'source',
        }
        self.builtins.update(builtins)

        # Optional: cached custom completer hook (so apps can override completely)
        self._custom_completer_factory: Optional[Callable[[], Any]] = None

    # ----------------------------
    # NEW: public prompt-session hooks
    # ----------------------------

    def get_session(self) -> PromptSession:
        """Return the underlying PromptSession."""
        return self._session

    def configure_prompt(self,
                         lexer: Optional["Lexer"] = None,
                         style: Optional["BaseStyle"] = None,
                         completer_factory: Optional[Callable[[], Any]] = None) -> None:
        """
        Configure prompt-toolkit features at runtime.

        - lexer: set live syntax highlighting lexer
        - style: set prompt-toolkit style
        - completer_factory: if provided, overrides loop() completer building
          (useful if an app wants total control).
        """
        if lexer is not None:
            try:
                self._session.lexer = lexer
            except Exception:
                # prompt-toolkit allows lexer in constructor; assignment may fail on older versions
                pass

        if style is not None:
            try:
                self._session.style = style
            except Exception:
                pass

        if completer_factory is not None:
            self._custom_completer_factory = completer_factory

    def set_lexer(self, lexer: "Lexer") -> None:
        self.configure_prompt(lexer=lexer)

    def set_style(self, style: "BaseStyle") -> None:
        self.configure_prompt(style=style)

    def set_completer(self, completer_factory: Callable[[], Any]) -> None:
        self.configure_prompt(completer_factory=completer_factory)

    # ----------------------------

    def system(self, args: list) -> None:
        """ Execute system commands. """

        if len(args) < 1:
            self.print_usage('!<command>')
            return

        self.print_process(f"Executing system command: {args[0]}%newline")

        try:
            subprocess.run(args)
        except Exception as e:
            self.print_error(f"Failed to execute: {str(e)}!")
            return

    def set_prompt(self, prompt: str) -> None:
        self.prompt = ColorScript().parse(prompt)

    def set_intro(self, intro: str) -> None:
        self.intro = ColorScript().parse(intro)

    def delete_external(self, external: list) -> None:
        for command in external:
            self.external.pop(command.info['Name'], None)
            self.complete.pop(command.info['Name'], None)

    def add_shortcut(self, alias: str, command: str, desc: str = "") -> None:
        self.shorts[alias] = [command, desc]

    def add_external(self, external: list) -> None:
        for command in external:
            name = command.info['Name']

            if not command.info['Method']:
                continue

            self.external[name] = command.info
            self.complete[name] = {}

            self.shorts.update(command.info['Shorts'])

            if command.info['Complete']:
                self.dynamic_complete[name] = command.info['Complete']

            if not self.complete[name]:
                self.complete[name] = None

    def load_external(self, path: str, **kwargs) -> None:
        if not os.path.exists(path):
            return

        for file in os.listdir(path):
            if not file.endswith('py'):
                continue

            try:
                commands = path + '/' + file
                spec = importlib.util.spec_from_file_location(commands, commands)
                obj = importlib.util.module_from_spec(spec)

                spec.loader.exec_module(obj)
                obj = obj.ExternalCommand()

                for attr, sub in kwargs.items():
                    setattr(obj, attr, sub)

                name = obj.info['Name']

                self.external[name] = obj.info
                self.external[name].update({'Method': obj.run})
                self.complete[name] = {}

                self.shorts.update(obj.info['Shorts'])

                if obj.complete() is not None:
                    self.dynamic_complete[name] = obj.complete

                if not self.complete[name]:
                    self.complete[name] = None

            except Exception:
                self.print_error(f"Failed to load {file[:-3]} command!")
                traceback.print_exc(file=sys.stdout)
                continue_or_exit()

    def do_source(self, args: list) -> None:
        """ Execute specific file as source.

        :param list args: command arguments
        :return None: None
        """

        if len(args) < 2 or not args[1]:
            while True:
                line = self._session.prompt(
                    ANSI(': '),
                    completer=NestedCompleter.from_nested_dict(self.complete))

                if not line:
                    break

                self.source.append(line)

            return

        if os.path.exists(args[1]) and not os.path.isdir(args[1]):
            self.print_process(f"Executing from file: {args[1]}%newline")
            self.source = open(args[1], 'r').read().split('\n')
            return

        self.print_error(f"Local file: {args[1]}: does not exist!")

    def do_exit(self, _) -> None:
        """ Exit console.

        :return None: None
        :raises EOFError: EOF error
        """

        raise EOFError

    def do_quit(self, _) -> None:
        """ Exit console.

        :return None: None
        :raises EOFError: EOF error
        """

        raise EOFError

    def do_clear(self, _) -> None:
        """ Clear terminal window.

        :return None: None
        """

        self.print_empty('%clear', end='')

    def do_help(self, _) -> None:
        """ Show all available commands.

        :return None: None
        """

        data = {}
        headers = ('Command', 'Description')

        for command in sorted(self.internal):
            if 'core' not in data:
                data['core'] = []

            description = getattr(self, 'do_' + command).__doc__.strip().split('\n')[0]
            data['core'].append((command, description))

        for command in sorted(self.external):
            category = self.external[command]['Category']
            description = self.external[command]['Description']

            if category not in data:
                data[category] = []

            data[category].append((command, description))

        for command in sorted(self.shorts):
            alias = self.shorts[command][0].split()[0]

            if alias in self.internal:
                data['core'].append((command, self.shorts[command][1]))
                continue

            alias = self.external.get(alias, None)
            if not alias:
                continue

            data[alias['Category']].append((command, self.shorts[command][1]))

        buffer = ''

        for category in sorted(data):
            with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
                self.print_table(f"{category} Commands", headers, *data[category])
                buffer += buf.getvalue()

        self.print_empty(buffer, end='')

    def verify_command(self, args: list) -> Tuple[bool, Union[str, list, None]]:
        commands = {}

        for name, obj in self.external.items():
            for i in range(len(name) + 1):
                prefix = name[:i]

                if prefix not in commands:
                    commands[prefix] = name
                elif commands[prefix] != name:
                    commands[prefix] = None

        if args[0] not in commands:
            return False, None

        result = commands[args[0]]

        if result:
            return True, result

        conflict = [name for name, obj in self.external.items() if name.startswith(args[0])]

        if args[0] in conflict:
            return True, args[0]

        return False, conflict

    def verify_args(self, args: list, info: dict) -> None:
        if not info['Options']:
            if len(args) - 1 < info['MinArgs']:
                self.print_usage(info['Usage'])
                return

            if info['Method'](args):
                self.print_usage(info['Usage'])
            return

        epilog = None
        if 'Examples' in info:
            epilog = "examples:\n  "
            epilog += "\n  ".join(info['Examples'])

        parser = argparse.ArgumentParser(
            prog=args[0],
            description=info['Description'],
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog
        )

        for entry in info['Options']:
            parser.add_argument(*entry[0], **entry[1])

        try:
            if len(args) - 1 < info['MinArgs']:
                parser.print_help()
                return

            if info['Method'](parser.parse_args(args[1:])):
                parser.print_help()

        except SystemExit:
            return

    def loop(self) -> None:
        self.preloop()

        if self.intro:
            self.print_empty(self.intro)

        while True:
            try:
                for name, completer in self.dynamic_complete.items():
                    self.complete[name] = completer()

                if not self.source:
                    # Build completer unless user overrides it
                    if self._custom_completer_factory is not None:
                        completer_obj = self._custom_completer_factory()
                    else:
                        completer_obj = NestedCompleter.from_nested_dict(self.complete)

                    with patch_stdout(raw=True):
                        line = self._session.prompt(
                            ANSI(self.prompt),
                            completer=completer_obj
                        )
                else:
                    line = self.source.pop(0)

                if line is None:
                    break

                line = line.strip()

                if not line:
                    self.emptyline()
                    continue

                line = self.precmd(line)
                line = self.onecmd(line)
                self.postcmd(line)

            except EOFError:
                self.print_empty(end='')
                break

            except KeyboardInterrupt:
                self.print_empty(end='')
                continue

            except RuntimeError as e:
                self.print_error(str(e))

            except RuntimeWarning as w:
                self.print_warning(str(w))

            except Exception as e:
                self.print_error(f"An error occurred: {str(e)}!")
                traceback.print_exc(file=sys.stdout)

        self.postloop()

    def preloop(self) -> None:
        return

    def postloop(self) -> None:
        return

    def precmd(self, line: str) -> str:
        return line

    def postcmd(self, line: str) -> None:
        return

    def onecmd(self, line: str) -> str:
        """ Execute single command.

        :param str line: line
        :return str: command result
        """

        raw_line = line  # <-- preserve the original line (with quotes, escapes, spacing)

        try:
            args = shlex.split(line)

        except ValueError as e:
            self.print_error(f"Error parsing command: {str(e)}")
            # If parsing fails, still pass raw line to default handler.
            try:
                self.default([], raw_line=raw_line)  # <-- new kwarg
            except TypeError:
                self.default([])  # backward compat
            return line

        if len(args) < 1:
            return line

        for builtin, func in self.builtins.items():
            if not func:
                continue

            if args[0].startswith(builtin):
                first = args[0].lstrip(builtin)
                prepend = []

                if isinstance(func, list):
                    self.source += func
                    return

                if not isinstance(func, str):
                    if first:
                        func([first, *args[1:]])
                    else:
                        func(args[1:])

                    return line

                if first:
                    args = [func, first, *args[1:]]
                else:
                    args = [func, *args[1:]]

        if args[0] not in self.external \
                and args[0] not in self.internal \
                and args[0] in self.shorts:
            short = self.shorts[args[0]]
            command = short[0]

            for i, arg in enumerate(args):
                command = command.replace(f'?{i}', arg)

            argv = shlex.split(command)
            args = []

            for arg in argv:
                if not arg.startswith('?'):
                    args.append(arg)

        if args[0] not in self.external \
                and args[0] in self.internal:
            getattr(self, 'do_' + args[0])(args)
            return line

        status, name = self.verify_command(args)

        if status:
            fixed = [name, *args[1:]]
            command = self.external[name]

            self.verify_args(fixed, command)
            return ' '.join(fixed)

        if name is not None:
            self.print_warning(f"Did you mean? {', '.join(name)}")

        # IMPORTANT: when falling back to default(), pass raw line too
        try:
            self.default(args, raw_line=raw_line)  # <-- new kwarg
        except TypeError:
            # Backward compatibility: older defaults accept only (args)
            self.default(args)

        return line

    def emptyline(self) -> None:
        return

    def default(self, args: list, raw_line: str = "") -> Any:
        self.print_error(f"Unrecognized command: {args[0]}")

