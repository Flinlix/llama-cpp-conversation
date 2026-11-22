"""The project's prose keeps the writing rules a machine can check: no em dash anywhere, no dash between clauses, outside the decision records no path of one machine, and no file names one program built on the library.

Prose is the Markdown outside code blocks and code spans, and the docstrings
and comments of the Python files.
"""

import ast
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

_ROOT = Path(__file__).parent.parent
# Folders a tool writes, which hold copies of the project's files.
_BUILT = {"mutants", "build", "dist", "site", "__pycache__"}
# Where the machines measurements were taken on are named: the decision records.
_DECISIONS = _ROOT / "docs" / "decisions"

_EM_DASH = re.compile("\u2014")
_CLAUSE_DASH = re.compile(r"\w\s(?:-|--|–)\s\w")
_MACHINE_PATH = re.compile(r"(?:/home/|/tmp/|/Users/|[A-Z]:\\\\)")
_CODE_SPAN = re.compile(r"``?[^`]*``?")
# A caller is named by its kind, such as a server; a determiner or an owner before the word
# makes it one program, and an owner before its settings one deployment.
_OWNER = r"(?:user|owner)s?['\u2019]s?"
_ONE_PROGRAM = re.compile(rf"\b(?:(?:the|that|this|our|my|{_OWNER})\s+(?:server|service)\b"
                          rf"|{_OWNER}\s+(?:production|own)\s+(?:settings|server|machines?)\b"
                          r"|the\s+user\s+runs\b|in\s+production\b)",
                          re.IGNORECASE)
# A line break and the comment mark that opens the next line, which a name may span.
_COMMENT_BREAK = re.compile(r"(?<=\n)[ \t]*#[ \t]*")


def _prose_files():
    for path in sorted(_ROOT.rglob("*")):
        parts = path.relative_to(_ROOT).parts
        if path.is_file() and path.suffix in (".py", ".md") \
                and not any(part.startswith(".") or part in _BUILT for part in parts):
            yield path


def _python_prose(text: str):
    """The lines of ``text``'s comments and docstrings, with their numbers."""
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type == tokenize.COMMENT:
            yield token.start[0], token.string
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(node, clean=False)
            if docstring:
                for offset, line in enumerate(docstring.splitlines()):
                    yield node.body[0].lineno + offset, line


def _markdown_prose(text: str):
    """The lines of ``text`` outside its code blocks, with their numbers."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced:
            yield number, line


def _breaks(path: Path) -> list[str]:
    text = path.read_text()
    lines = _python_prose(text) if path.suffix == ".py" else _markdown_prose(text)
    # Nowhere, not even in code.
    found = [f"{path.relative_to(_ROOT)}:{number}: an em dash"
             for number, line in enumerate(text.splitlines(), 1) if _EM_DASH.search(line)]
    for number, line in lines:
        prose = _CODE_SPAN.sub("", line)
        where = f"{path.relative_to(_ROOT)}:{number}"
        if _CLAUSE_DASH.search(prose):
            found.append(f"{where}: a dash between clauses")
        if _DECISIONS not in path.parents:
            if _MACHINE_PATH.search(prose):
                found.append(f"{where}: a path of one machine")
    return found


@pytest.mark.parametrize("path", list(_prose_files()),
                         ids=[str(p.relative_to(_ROOT)) for p in _prose_files()])
def test_the_prose_keeps_the_writing_rules(path):
    assert _breaks(path) == []


def _tracked_files() -> list[Path]:
    """Every file git tracks in the project, hidden and suffixless ones included."""
    listed = subprocess.run(["git", "-C", str(_ROOT), "ls-files", "-z"], capture_output=True)
    if listed.returncode != 0:
        pytest.skip("the project is not a git checkout, so its tracked files are not known")
    return [_ROOT / name for name in listed.stdout.decode().split("\0") if name]


def _programs_named(path: Path) -> list[str]:
    """Where ``path`` names one program built on the library instead of a kind of caller, a line break inside the name included."""
    try:
        text = path.read_text()
    except (UnicodeDecodeError, FileNotFoundError):
        return []                       # not text, or deleted and not yet committed
    text = _COMMENT_BREAK.sub("", text)  # the lines stay where they were
    return [f"{path.relative_to(_ROOT)}:{text.count(chr(10), 0, match.start()) + 1}: one program named"
            for match in _ONE_PROGRAM.finditer(text)]


def test_no_file_names_a_program_built_on_the_library():
    assert [line for path in _tracked_files() for line in _programs_named(path)] == []


def test_a_program_named_is_found_and_a_kind_of_caller_is_not(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "_ROOT", tmp_path)
    server, owners, production = "ser" + "ver", "own" + "er\u2019s", "produc" + "tion"
    named = [f"Measured at the {server}'s settings.", f"Through the {owners}\n{server}.",
             f"That {server} injects.", f"The user's {server} starts empty.",
             f"Tried on the user's {production} settings.", f"As the {'ser' + 'vice'} does.",
             f"# as the model the user {'ru' + 'ns'} does,", f"  # as one does in {production}.",
             f"# kept by the\n    # {server}."]
    kinds = [f"A {server} keeps its ids.", "A client sends it.", "The stack of a thread.",
             "A service the process runs in."]
    sample = tmp_path / "pre-push"
    sample.write_text("\n".join(kinds + named) + "\n")
    found = [int(line.split(":")[1]) for line in _programs_named(sample)]
    assert found == [5, 6, 8, 9, 10, 11, 12, 13, 14]


def test_each_break_of_the_writing_rules_is_found(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "_ROOT", tmp_path)
    sample = tmp_path / "notes.md"
    sample.write_text("One clause \u2014 another.\nOne - two.\nAt /home/someone it ran.\n"
                      "```\nx = a - b  # code, left alone\n```\nIn `a - b` too.\n")
    found = _breaks(sample)
    assert [line.split(": ", 1)[1] for line in found] == [
        "an em dash", "a dash between clauses", "a path of one machine"]
