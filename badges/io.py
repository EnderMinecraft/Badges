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
from msvcrt import getch

from datetime import datetime
from colorscript import ColorScript

from typing import Callable, Any, Optional, Dict
from contextlib import redirect_stdout, redirect_stderr

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import ANSI


class IO(object):
    """I/O implementation."""

    @staticmethod
    def set_log(log: str) -> None:
        globals()['log'] = log

    @staticmethod
    def set_history(history: str) -> None:
        globals()['history'] = history

    @staticmethod
    def set_less(less: bool) -> None:
        globals()['less'] = less

    # NEW: global prompt-toolkit config for IO.input()
    @staticmethod
    def set_prompt_config(*, lexer=None, style=None, session_kwargs: Optional[Dict[str, Any]] = None) -> None:
        globals()['ptk_lexer'] = lexer
        globals()['ptk_style'] = style
        globals()['ptk_session_kwargs'] = session_kwargs or {}

        # If a session already exists, try to update it in-place.
        sess = globals().get('prompt_session')
        if sess is not None:
            try:
                if lexer is not None:
                    sess.lexer = lexer
            except Exception:
                pass
            try:
                if style is not None:
                    sess.style = style
            except Exception:
                pass

    def suppress_function(self, target: Callable[..., Any], *args, **kwargs) -> Any:
        with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
            return target(*args, **kwargs)

    def print_function(self, target: Callable[..., Any], *args, **kwargs) -> Any:
        with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
            result = target(*args, **kwargs)
            output = buf.getvalue()

        self.print_less(output)
        return result

    @staticmethod
    def print_less(data: str) -> None:
        try:
            columns, rows = os.get_terminal_size()
        except Exception:
            sys.stdout.write(data)
            sys.stdout.flush()
            return

        lines = data.split('\n')
        num_lines = len(lines)
        start_index = 0
        end_index = rows - 3

        while start_index < num_lines:
            for line in range(start_index, min(end_index + 1, num_lines)):
                if line == num_lines - 1:
                    sys.stdout.write(lines[line])
                    sys.stdout.flush()
                else:
                    sys.stdout.write(lines[line] + '\n')
                    sys.stdout.flush()

            if end_index >= num_lines - 1:
                break

            sys.stdout.write("Press Enter for more, 'a' for all, 'q' to quit:")
            sys.stdout.flush()

            user_input = ''

            while user_input not in ['\n', 'q', ' ', 'a']:
                user_input = getch.getch()

            sys.stdout.write(ColorScript().parse('%remove'))
            sys.stdout.flush()

            if user_input == 'q':
                return

            start_index = end_index + 1

            if user_input == ' ':
                end_index = start_index + 10
                continue

            elif user_input == 'a':
                end_index = num_lines
                continue

            end_index = start_index

    @staticmethod
    def _get_prompt_session() -> PromptSession:
        if 'prompt_session' not in globals():
            history_path = globals().get('history', None)

            # New configurable session kwargs
            session_kwargs = dict(globals().get('ptk_session_kwargs', {}) or {})

            lexer = globals().get('ptk_lexer', None)
            style = globals().get('ptk_style', None)

            if lexer is not None:
                session_kwargs.setdefault('lexer', lexer)
            if style is not None:
                session_kwargs.setdefault('style', style)

            if history_path:
                globals()['prompt_session'] = PromptSession(
                    history=FileHistory(history_path),
                    **session_kwargs
                )
            else:
                globals()['prompt_session'] = PromptSession(**session_kwargs)

        return globals()['prompt_session']

    @staticmethod
    def input(message: str = '', start: str = '%end', end: str = '', *args, **kwargs) -> None:
        session = IO._get_prompt_session()

        line = ColorScript().parse(str(start) + str(message) + str(end))
        use_log = globals().get("log")

        data = session.prompt(ANSI(line), *args, **kwargs)

        if use_log:
            with open(use_log, 'a') as f:
                f.write(line + data + '\n')
                f.flush()

        return data

    def print(self, message: str = '', start: str = '%remove%end', end: str = '%newline',
              time: bool = False, log: Optional[bool] = None,
              less: Optional[bool] = None) -> None:

        if time:
            start = str(start) + datetime.now().strftime('%H:%M:%S - ')

        line = ColorScript().parse(str(start) + str(message) + str(end))

        use_log = log if log is not None else globals().get("log")
        use_less = less if less is not None else globals().get("less", True)

        if use_less:
            self.print_less(line)
        else:
            sys.stdout.write(line)
            sys.stdout.flush()

        if use_log:
            with open(use_log, 'a') as f:
                f.write(line)
                f.flush()
