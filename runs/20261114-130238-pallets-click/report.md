# Repository report: pallets/click

- URL: https://github.com/pallets/click.git
- Requested ref: 8.5.1
- Commit: `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`
- Run: `20261114-130238-pallets-click` · model `claude-sonnet-5-5`
- Verification: 159 of 159 claimed interfaces confirmed in the source; 0 claims dropped

## Purpose
Click is a Python library for building command-line interfaces. It is composable: commands, groups, options and arguments are built from decorators or classes. It handles parsing, help generation, prompts, shell completion and testing.

## Intended users
Python developers writing CLI applications. Maintainers and contributors working on Pallets/Click itself.

## Languages, frameworks, dependencies
- Languages: Python (>=3.10)
- Frameworks: Flit (flit_core build backend), pytest, tox with tox-uv and uv, mypy and pyright, ruff and pre-commit, Sphinx (docs)
- Dependencies: Runtime: no dependencies are declared in pyproject.toml. The [project] table has no dependencies key. I did not check for a Windows-only dependency such as colorama., dev group: ruff, tox, tox-uv, tests group: pytest, tests-random group: pytest, pytest-randomly, pytest-xdist, typing group: mypy, pyright, pytest, docs group: sphinx, myst-parser, pallets-sphinx-themes, sphinx-tabs, sphinxcontrib-log-cabinet

## Entry points
- `src/click/core.py:1483`: Command.main() runs a CLI: it reads args, handles shell completion, builds the context, invokes the command and maps exceptions to exit codes. Command.__call__ is an alias for it (line 1651).
- `src/click/__init__.py:10`: The public API surface: it re-exports names from core, decorators, exceptions, formatting, globals, termui, types and utils.
- `src/click/testing.py:1`: CliRunner, the public testing entry point. Its contents were not read; tests use it via the `runner` fixture.

## Key modules (most feature-relevant first)
- `src/click/core.py`: Context, Command, Group, CommandCollection, Parameter, Option and Argument, plus ParameterSource. It holds main(), make_context, parse_args, invoke, resolve_command and the parameter value pipeline (consume_value, type_cast_value, process_value, handle_parse_result). *Feature relevance:* Most new behaviour goes here: new Option/Argument/Command/Group parameters, value handling, help specs, and the info dict (to_info_dict).
- `src/click/decorators.py`: Decorators: command, group, option, argument, pass_context, pass_obj, make_pass_decorator, version_option, help_option, confirmation_option, password_option, custom_version_option. *Feature relevance:* A new core parameter usually needs a matching decorator keyword or a new decorator. Typing tests exercise these.
- `src/click/types.py`: ParamType and its implementations: Choice, File, Path, IntRange, FloatRange, DateTime, UUID, Tuple, BOOL, INT, FLOAT, STRING and UNPROCESSED, plus the convert_type function. *Feature relevance:* Add new parameter types or change conversion.
- `src/click/parser.py`: Internal option parser, now private as _OptionParser, _Option, _Argument and _ParsingState. The old public names go through deprecation shims. *Feature relevance:* Changes to how option tokens are parsed.
- `src/click/termui.py`: Interactive and terminal helpers: prompt, confirm, style, secho, progressbar, edit, launch, pause, getchar, echo_via_pager and clear. The implementation is in _termui_impl.py. *Feature relevance:* Add or modify terminal UI features.
- `src/click/shell_completion.py`: Shell completion: CompletionItem, shell_complete and split_arg_string. Command.main calls it when the _PROG_COMPLETE environment variable is set. *Feature relevance:* Add shells or completion behaviour.
- `src/click/formatting.py`: HelpFormatter and wrap_text, used for help output. *Feature relevance:* Changes to help layout.
- `src/click/exceptions.py`: ClickException hierarchy: UsageError, BadParameter, MissingParameter, NoSuchOption, NoSuchCommand, BadArgumentUsage, BadOptionUsage, FileError, Abort, plus Exit (used in core.py but not re-exported in __init__.py). *Feature relevance:* New error types or error message changes.
- `src/click/utils.py`: echo, open_file, format_filename, get_app_dir, and private helpers such as _LazyFile and _KeepOpenFile. Several old public names are now deprecated aliases. *Feature relevance:* Shared utilities.
- `src/click/testing.py`: CliRunner for invoking commands in tests. *Feature relevance:* Test-support features. Its contents were not read.
- `src/click/_compat.py`: Platform and stream compatibility helpers. Not read. *Feature relevance:* Cross-platform behaviour.
- `src/click/globals.py`: get_current_context and the context stack. Not read. *Feature relevance:* Context access.

## Execution flow
Command.main (core.py:1483) takes args from sys.argv[1:], expanding globs on Windows via _expand_args, or from the args you pass. It detects the program name and calls _main_shell_completion (line 1619). If the _<PROG>_COMPLETE env var is set, that function runs shell_complete and exits. Otherwise main opens `with self.make_context(prog_name, args, **extra) as ctx` and calls self.invoke(ctx). make_context calls parse_args. For each parameter, parse_args calls Parameter.handle_parse_result (core.py:2763), which does the following: consume_value picks a value and a ParameterSource; a deprecation warning is echoed to stderr if the value was set explicitly; process_value runs type conversion and callbacks; then the value is stored in ctx.params, with arbitration when several parameters share one name. Group.invoke dispatches to subcommands through resolve_command (core.py:2088). In standalone mode main then calls ctx.exit(). Exit, Abort, KeyboardInterrupt/EOFError, ClickException and EPIPE OSError are caught and turned into exit codes and messages. With standalone_mode=False, the return value is returned and exceptions propagate.

## Tests (runner: pytest. pyproject.toml sets testpaths=tests and filterwarnings=error. addopts is `-m 'not stress'`. tox runs it across Python 3.10–3.14 plus 3.14t and pypy3.11 (both listed in the tox env_list).)
- `tests/test_options.py` covers `src/click/core.py`, `src/click/decorators.py`
- `tests/test_arguments.py` covers `src/click/core.py`
- `tests/test_basic.py` covers `src/click/core.py`, `src/click/decorators.py`
- `tests/test_commands.py` covers `src/click/core.py`
- `tests/test_command_decorators.py` covers `src/click/decorators.py`
- `tests/test_context.py` covers `src/click/core.py`, `src/click/globals.py`
- `tests/test_chain.py` covers `src/click/core.py`
- `tests/test_defaults.py` covers `src/click/core.py`
- `tests/test_info_dict.py` covers `src/click/core.py`, `src/click/types.py`
- `tests/test_parser.py` covers `src/click/parser.py`
- `tests/test_shell_completion.py` covers `src/click/shell_completion.py`
- `tests/test_formatting.py` covers `src/click/formatting.py`
- `tests/test_termui.py` covers `src/click/termui.py`, `src/click/_termui_impl.py`
- `tests/test_testing.py` covers `src/click/testing.py`
- `tests/test_exceptions/test_FileError.py` covers `src/click/exceptions.py`
- `tests/test_deprecations.py` covers `src/click/__init__.py`, `src/click/core.py`, `src/click/parser.py`, `src/click/utils.py`, `src/click/testing.py`
- `tests/test_imports.py` covers `src/click/__init__.py`
- `tests/test_compat.py` covers `src/click/_compat.py`
- `tests/test_types/test_Choice.py` covers `src/click/types.py`
- `tests/test_types/test_Path.py` covers `src/click/types.py`
- `tests/test_utils/test_echo.py` covers `src/click/utils.py`
- `tests/test_utils/test_prompt.py` covers `src/click/termui.py`
- `tests/typing/typing_options.py` covers `src/click/decorators.py`, `src/click/core.py`

### Test conventions
- tests/conftest.py provides a function-scoped `runner` fixture that returns CliRunner().
- Plain pytest functions with bare asserts. Parametrization is used heavily, for example `ids=lambda ...` in test_deprecations.py.
- Warnings are errors (filterwarnings=error), so a test that triggers a warning on purpose must wrap it in pytest.warns(...). For example, `pytest.warns(DeprecationWarning, match=name)`.
- Test files are grouped by source module. Subpackages tests/test_types/, tests/test_utils/ and tests/test_exceptions/ hold one file per class or function, named test_<Name>.py.
- tests/typing/*.py are example files checked by mypy and pyright (the `typing` tox env). They are not run by pytest.
- Stress tests carry `@pytest.mark.stress` and are excluded by default.

## Compatibility rules
- Supported Python is >=3.10, and the package is typed (Typing :: Typed classifier, py.typed file in src/click). (`pyproject.toml:14-16`)
- The public API is whatever src/click/__init__.py re-exports using the `X as X` form. Names beginning with an underscore are private. Old names are kept as lazy module `__getattr__` shims that emit DeprecationWarning. (`src/click/__init__.py:10-144`)
- Deprecation practice: the message says 'is deprecated and will be removed in Click 9.0' (or 9.1 for __version__), uses DeprecationWarning with stacklevel=2, and names the replacement. The old name still resolves to the private implementation. (`src/click/__init__.py:76-144`)
- core.py also has a module-level __getattr__ shim for BaseCommand and MultiCommand. (`src/click/core.py:3804-3825`)
- Each deprecated alias must have a test in test_deprecations.py (parametrized case plus an AttributeError check for unknown names). (`tests/test_deprecations.py:12-60`)
- Warning policy: pytest runs with filterwarnings=error, and the docs build uses -W. (`pyproject.toml:85-87`)
- Typing policy: mypy runs in strict mode over src and tests/typing, and pyright runs with --verifytypes click. (`pyproject.toml:107-117`)
- The code uses `from __future__ import annotations`. ruff enforces isort with force-single-line imports and the `typing as t` alias. (`pyproject.toml:126-143`)
- Changes are recorded in CHANGES.md using {pr}/{issue} roles. Docstrings use `.. versionchanged::` / `.. versionadded::` directives. (`CHANGES.md:1-30`)
- User-facing strings go through the gettext `_()` function. The deprecated-parameter message in handle_parse_result is one example. (`src/click/core.py:2799-2806`)

## Setup and test commands
- `uv sync`: Install the default dependency groups (dev, pre-commit, tests, typing). The command itself is not in the file; it is inferred from [tool.uv] default-groups. (source: pyproject.toml; discovered, not executed)
- `pytest`: Run the tests (testpaths=tests; stress tests are excluded). (source: pyproject.toml; discovered, not executed)
- `tox`: Run the full matrix: Python 3.10–3.14, 3.14t, pypy3.11, style, typing, docs and the stress environments. (source: pyproject.toml; discovered, not executed)
- `tox run -e typing`: Run mypy and `pyright --ignoreexternal --verifytypes click`. (source: pyproject.toml; discovered, not executed)
- `tox run -e style`: Run `pre-commit run --all-files`. (source: pyproject.toml; discovered, not executed)
- `tox run -e docs`: Run `sphinx-build -E -W -b dirhtml docs docs/_build/dirhtml`. (source: pyproject.toml; discovered, not executed)
- `tox run -e stress-py3.14`: Run the stress tests only (`pytest -m stress`). (source: pyproject.toml; discovered, not executed)

## Evidence
- Project metadata: name click, version 8.5.1, BSD-3-Clause, flit_core build backend. (`pyproject.toml:1-16`)
- The tox env_list covers Python 3.10–3.14, 3.14t, pypy3.11, stress, style, typing and docs. (`pyproject.toml:145-154`)
- Command.main is the CLI runner and handles standalone_mode and exception mapping. (`src/click/core.py:1483-1617`)
- Shell completion is triggered through an environment variable. (`src/click/core.py:1619-1649`)
- The parameter value pipeline and the arbitration of parameters that share a name. (`src/click/core.py:2763-2849`)
- Changelog: 8.5.1 released 2026-11-09. It adds Parameter help, Option.get_help_spec and a change to Argument.get_help_record's return value. (`CHANGES.md:1-30`)
- core.py classes: Context 213, Command 960, Group 1671, CommandCollection 2141, Parameter 2209, Option 2891, Argument 3698. (`src/click/core.py:213-3698`)
- Test fixture: a `runner` that returns CliRunner. (`tests/conftest.py:6-8`)

## Module card: `src/click/core.py`
src/click/core.py holds Click's runtime model. Context carries per-invocation state: params, parameter sources, resources and cleanup. Command parses args and invokes the callback. Group, plus its CommandCollection subclass, dispatches to subcommands, including chain mode. Parameter, Option and Argument implement the value pipeline: parser value, then consume_value (env var, default_map, default, prompt), then type_cast_value, then process_value (required check, callback), then handle_parse_result. handle_parse_result also arbitrates when several params share one name. An internal UNSET sentinel is used throughout and is converted to None before the user sees it. ParameterSource is an IntEnum ordered from most to least explicit. Command.main wraps everything with exception-to-exit-code handling.

### Interfaces
- **`ParameterSource`** (`src/click/core.py:174-210`)
  - Signature: `class ParameterSource(enum.IntEnum)`
  - Behavior: IntEnum with members PROMPT, COMMANDLINE, ENVIRONMENT, DEFAULT_MAP, DEFAULT (enum.auto, so values 1..5). Lower means more explicit, so comparisons such as `source < ParameterSource.DEFAULT_MAP` mean 'explicitly provided'. handle_parse_result uses this ordering for deprecation warnings and for arbitration.
  - Edge case: Ordering was changed in 8.3.3 (IntEnum, reordered)
- **`Context.__init__`** (`src/click/core.py:345-518`)
  - Signature: `def __init__(self, command: Command, parent: Context | None=None, info_name: str | None=None, obj: t.Any | None=None, auto_envvar_prefix: str | None=None, default_map: cabc.MutableMapping[str, t.Any] | None=None, terminal_width: int | None=None, max_content_width: int | None=None, resilient_parsing: bool=False, allow_extra_args: bool | None=None, allow_interspersed_args: bool | None=None, ignore_unknown_options: bool | None=None, help_option_names: list[str] | None=None, token_normalize_func: t.Callable[[str], str] | None=None, color: bool | None=None, show_default: bool | None=None) -> None`
  - Behavior: Builds a context for a command. Stores parent, command, info_name, params={}, args=[] and further settings. Key args: obj, auto_envvar_prefix, default_map, terminal_width, max_content_width, resilient_parsing, allow_extra_args, allow_interspersed_args, ignore_unknown_options, help_option_names, token_normalize_func, color, show_default. Several of these are None by default so they can be inherited from the parent or from the command (not re-read in full).
  - Edge case: Settings default to None and are inherited from parent where applicable
- **`Context.scope`** (`src/click/core.py:573-608`)
  - Signature: `def scope(self, cleanup: bool=True) -> cabc.Generator[Context]`
  - Behavior: Context manager that pushes the context onto the thread-local stack. With cleanup=False the context is not closed on exit. make_context uses it for parsing.
  - Edge case: cleanup=False skips close()
- **`Context.with_resource`** (`src/click/core.py:652-679`)
  - Signature: `def with_resource(self, context_manager: AbstractContextManager[V]) -> V`
  - Behavior: Enters the given context manager, registers its exit to run on ctx.close(), and returns the entered value.
- **`Context.call_on_close`** (`src/click/core.py:681-691`)
  - Signature: `def call_on_close(self, f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]`
  - Behavior: Registers a callback to run when the context closes. Returns the callback, so it can be used as a decorator.
- **`Context.lookup_default`** (`src/click/core.py:789-809`)
  - Signature: `def lookup_default(self, name: str, call: bool=True) -> t.Any | None`
  - Behavior: Looks up name in default_map. If call=True and the value is callable, it is called. Returns None if the name is absent.
  - Edge case: Callable defaults are invoked when call=True
- **`Context.find_object`** (`src/click/core.py:744-754`)
  - Signature: `def find_object(self, object_type: type[V]) -> V | None`
  - Behavior: Walks up the parent chain and returns the first ctx.obj that is an instance of object_type, or None if there is none.
  - Edge case: Returns None when absent
- **`Context.ensure_object`** (`src/click/core.py:756-763`)
  - Signature: `def ensure_object(self, object_type: type[V]) -> V`
  - Behavior: Calls find_object. If it returns None, creates object_type(), stores it in ctx.obj and returns it.
- **`Context.fail`** (`src/click/core.py:811-817`)
  - Signature: `def fail(self, message: str) -> t.NoReturn`
  - Behavior: Raises UsageError(message, ctx).
  - Raises: `UsageError`
- **`Context.exit`** (`src/click/core.py:823-831`)
  - Signature: `def exit(self, code: int=0) -> t.NoReturn`
  - Behavior: Raises Exit(code), default 0. Context.abort raises Abort.
  - Raises: `Exit`
- **`Context.invoke`** (`src/click/core.py:861-911`)
  - Signature: `def invoke(self, callback: Command | t.Callable[..., V], /, *args: t.Any, **kwargs: t.Any) -> t.Any | V`
  - Behavior: If the first argument is a Command, a sub-context is created. Every exposed param not in kwargs is filled from param.get_default (UNSET becomes None) and passed through type_cast_value. Then kwargs are recorded in ctx.params and the command's callback is called. If the first argument is a plain callable, it is called with the given args and kwargs. The call runs inside augment_usage_errors and the context.
  - Edge case: A command without a callback raises TypeError
  - Edge case: Defaults are type-cast but required is not enforced
  - Raises: `TypeError`
- **`Context.forward`** (`src/click/core.py:913-930`)
  - Signature: `def forward(self, cmd: Command, /, *args: t.Any, **kwargs: t.Any) -> t.Any`
  - Behavior: Like invoke, but first copies all of the current ctx.params into kwargs for keys not already given. Only accepts Command objects.
  - Edge case: A non-Command argument raises TypeError
  - Raises: `TypeError`
- **`Context.get_parameter_source`** (`src/click/core.py:941-957`)
  - Signature: `def get_parameter_source(self, name: str) -> ParameterSource | None`
  - Behavior: Returns the ParameterSource for a parameter name, or None if no source was recorded. Context.set_parameter_source sets it.
  - Edge case: Returns None when unrecorded
- **`Command.make_context`** (`src/click/core.py:1330-1365`)
  - Signature: `def make_context(self, info_name: str | None, args: list[str], parent: Context | None=None, **extra: t.Any) -> Context`
  - Behavior: Copies context_settings into extra without overriding explicit keys. Builds self.context_class(self, info_name=..., parent=..., **extra). Then runs self.parse_args(ctx, args) inside ctx.scope(cleanup=False) and returns the context without invoking the callback.
  - Edge case: Explicit **extra wins over context_settings
- **`Command.parse_args`** (`src/click/core.py:1367-1398`)
  - Signature: `def parse_args(self, ctx: Context, args: list[str]) -> list[str]`
  - Behavior: Raises NoArgsIsHelpError if there are no args, no_args_is_help is set and parsing is not resilient. Builds the parser and parses. For each param in iter_params_for_processing (eager params first, then in the order they were given on the command line) it calls handle_parse_result. Afterwards UNSET in ctx.params is converted to None. Leftover args cause ctx.fail('Got unexpected extra argument(s) (...)') unless allow_extra_args or resilient_parsing is set. Finally it sets ctx.args.
  - Edge case: resilient_parsing suppresses errors
  - Edge case: UNSET is converted to None only after all params are processed
  - Raises: `NoArgsIsHelpError`
  - Raises (unconfirmed, likely via a helper): `UsageError`
- **`Command.invoke`** (`src/click/core.py:1400-1414`)
  - Signature: `def invoke(self, ctx: Context) -> t.Any`
  - Behavior: If the command is deprecated, echoes a red 'DeprecationWarning: The command ... is deprecated.' message to stderr. Then, if a callback exists, returns ctx.invoke(callback, **ctx.params). Returns None otherwise.
  - Edge case: No callback means None is returned
- **`Command.main`** (`src/click/core.py:1483-1617`)
  - Signature: `def main(self, args: cabc.Sequence[str] | None=None, prog_name: str | None=None, complete_var: str | None=None, standalone_mode: bool=True, windows_expand_args: bool=True, **extra: t.Any) -> t.Any`
  - Behavior: Uses sys.argv[1:] when args is None, with Windows glob expansion when windows_expand_args is true. Otherwise uses list(args). Detects prog_name, handles shell completion via the _PROG_COMPLETE env var and exits early. Runs make_context and invoke inside the context. With standalone_mode=True it calls ctx.exit() and ends with sys.exit. Exit sets the exit code. Abort prints 'Aborted!' and exits 1. EOFError/KeyboardInterrupt also lead to 'Aborted!'. ClickException is shown via e.show with e.exit_code. OSError with errno EPIPE is silenced, anything else is re-raised. With standalone_mode=False it returns rv, or e.exit_code for Exit, and re-raises Abort and ClickException. EOFError/KeyboardInterrupt are re-raised as Abort. Command.__call__ is an alias.
  - Edge case: Exit in non-standalone mode returns the exit code, which is ambiguous with a return value
  - Edge case: Chained commands can return [None, ...]
  - Raises: `Abort`, `ClickException`
- **`Group.add_command`** (`src/click/core.py:1803-1811`)
  - Signature: `def add_command(self, cmd: Command, name: str | None=None) -> None`
  - Behavior: Registers cmd under name or cmd.name. Runs _check_nested_chain(register=True) and stores it in self.commands.
  - Edge case: No name raises TypeError
  - Raises: `TypeError`
- **`Group.command`** (`src/click/core.py:1821-1860`)
  - Signature: `def command(self, *args: t.Any, **kwargs: t.Any) -> t.Callable[[t.Callable[..., t.Any]], Command] | Command`
  - Behavior: Decorator that creates a command via decorators.command and registers it with add_command. Works with or without parentheses. Uses command_class when cls is not passed.
  - Edge case: A bare callable together with kwargs triggers an AssertionError
  - Raises (unconfirmed, likely via a helper): `AssertionError`
- **`Group.result_callback`** (`src/click/core.py:1914-1957`)
  - Signature: `def result_callback(self, replace: bool=False) -> t.Callable[[F], F]`
  - Behavior: Decorator that registers a result callback. It is called with (result, **ctx.params) after the subcommand runs. In chain mode the result is a list. replace=True allows replacing an existing callback.
  - Edge case: Not read in full; replace semantics inferred from the signature
- **`Group.invoke`** (`src/click/core.py:2020-2086`)
  - Signature: `def invoke(self, ctx: Context) -> t.Any`
  - Behavior: Without a subcommand: if invoke_without_command is set, runs the group callback and passes its return value to the result callback (an empty list in chain mode). Otherwise fails with 'Missing command.'. In non-chain mode it resolves the command, sets ctx.invoked_subcommand, runs the group callback, builds the sub-context and invokes it, then runs the result callback. In chain mode it sets invoked_subcommand to '*' (or None), runs the group callback, creates all sub-contexts (allow_extra_args=True, allow_interspersed_args=False) and then invokes them in order. The result callback receives the list of results.
  - Edge case: Group callback runs before the subcommand context is made
  - Edge case: Chain contexts are all built before any runs
  - Raises (unconfirmed, likely via a helper): `UsageError`
- **`Group.resolve_command`** (`src/click/core.py:2088-2112`)
  - Signature: `def resolve_command(self, ctx: Context, args: list[str]) -> tuple[str | None, Command | None, list[str]]`
  - Behavior: Calls get_command(ctx, name of args[0]). If not found and token_normalize_func is set, retries with the normalized name. If still not found and parsing is not resilient: when the token looks like an option it re-runs self.parse_args(ctx, args) so that --help and similar are handled by the group. Then it raises NoSuchCommand with command-name possibilities. Returns (name, cmd, args[1:]). Under resilient_parsing it returns (None, None, rest).
  - Edge case: Resilient parsing yields (None, None, ...)
  - Raises: `NoSuchCommand`
- **`CommandCollection.get_command`** (`src/click/core.py:2173-2188`)
  - Signature: `def get_command(self, ctx: Context, cmd_name: str) -> Command | None`
  - Behavior: Checks the group's own commands first, then each of the sources in order. In chain mode it validates nested chains. list_commands returns the sorted union of names. add_source appends a Group to sources.
  - Edge case: Source params and callbacks are not used
  - Edge case: Own commands take precedence over sources
- **`Parameter.consume_value`** (`src/click/core.py:2518-2564`)
  - Signature: `def consume_value(self, ctx: Context, opts: cabc.Mapping[str, t.Any]) -> tuple[t.Any, ParameterSource]`
  - Behavior: Value precedence: parser opts (COMMANDLINE), then envvar via value_from_envvar (ENVIRONMENT), then ctx.default_map via lookup_default (DEFAULT_MAP, including explicit None keys). A str from the default map is split via type.split_envvar_value when nargs != 1. Then get_default (DEFAULT). Returns (value, source), where value may be UNSET.
  - Edge case: An empty envvar string is treated as unset
  - Edge case: A key explicitly present in default_map with a None value counts as set
- **`Parameter.type_cast_value`** (`src/click/core.py:2566-2620`)
  - Signature: `def type_cast_value(self, ctx: Context, value: t.Any) -> t.Any`
  - Behavior: None becomes () for multiple or nargs=-1, otherwise None passes through. nargs==1 or a composite type: calls self.type(value, param, ctx). nargs=-1: converts each item into a tuple. nargs>1: requires exactly nargs items and returns a tuple. multiple: wraps the above in a tuple over the items.
  - Edge case: A non-iterable raises 'Value must be an iterable.'
  - Edge case: A wrong item count raises 'Takes N values but M were given.'
  - Raises: `BadParameter`
- **`Parameter.process_value`** (`src/click/core.py:2640-2700`)
  - Signature: `def process_value(self, ctx: Context, value: t.Any) -> t.Any`
  - Behavior: UNSET becomes () for multiple or nargs=-1, otherwise it skips the cast. Otherwise calls type_cast_value. Then, if required and value_is_missing, raises MissingParameter. Then, if a callback is set, calls callback(ctx, param, value). UNSET is shown to the callback as None, and other UNSET params in ctx.params are temporarily masked as None.
  - Edge case: The callback return value replaces the value
  - Edge case: Option.process_value gives an unset non-required bool flag the value False, without type-casting (callback still called)
  - Raises: `MissingParameter`
- **`Parameter.handle_parse_result`** (`src/click/core.py:2763-2849`)
  - Signature: `def handle_parse_result(self, ctx: Context, opts: cabc.Mapping[str, t.Any], args: list[str]) -> tuple[t.Any, list[str]]`
  - Behavior: Inside augment_usage_errors it calls consume_value, records the source, emits a deprecation warning to stderr if deprecated and explicitly set (source < DEFAULT_MAP), and calls process_value. In resilient_parsing mode, exceptions from process_value are swallowed and the value is reset to UNSET. When several params share a name, arbitration decides the winner: the more explicit source wins; on a tie the later one wins unless it would downgrade an explicit default. The winner writes ctx.params[name] if expose_value is true. Returns (value, args).
  - Edge case: expose_value=False params are not stored in ctx.params
  - Edge case: Losers restore the previous source
  - Raises (unconfirmed, likely via a helper): `MissingParameter`, `BadParameter`
- **`Option.__init__`** (`src/click/core.py:2983-3058`)
  - Signature: `def __init__(self, param_decls: cabc.Sequence[str] | None=None, show_default: bool | str | None=None, prompt: bool | str=False, confirmation_prompt: bool | str=False, prompt_required: bool=True, hide_input: bool=False, is_flag: bool | None=None, flag_value: t.Any=UNSET, multiple: bool=False, count: bool=False, allow_from_autoenv: bool=True, type: types.ParamType[t.Any] | t.Any | None=None, help: str | None=None, hidden: bool=False, show_choices: bool=True, show_envvar: bool=False, deprecated: bool | str=False, **attrs: t.Any) -> None`
  - Behavior: Declares an option. It handles prompt (prompt=True derives text from the name), confirmation_prompt, prompt_required, hide_input, is_flag, flag_value (default UNSET), multiple, count (default 0 if unset), allow_from_autoenv, type, help, hidden, show_choices, show_envvar, show_default and deprecated. Flag kind is inferred in _infer_flag_kind and the type in _pick_type. It ends with a _validate step that raises on illegal combinations.
  - Edge case: prompt=True without a name raises TypeError
  - Edge case: Setting flag_value implies is_flag
  - Raises: `TypeError`
- **`Option.consume_value`** (`src/click/core.py:3627-3681`)
  - Signature: `def consume_value(self, ctx: Context, opts: cabc.Mapping[str, Parameter]) -> tuple[t.Any, ParameterSource]`
  - Behavior: Calls Parameter.consume_value. If the parser yields FLAG_NEEDS_VALUE, it prompts (source PROMPT) when prompt is set and parsing is not resilient. Otherwise it uses flag_activation_value with source COMMANDLINE. For multiple options it replaces FLAG_NEEDS_VALUE items with the activation value. If the value is unset (or from default/default_map) and prompt is set and (required or prompt_required), it prompts.
  - Edge case: Prompting is skipped under resilient_parsing
- **`Argument.__init__`** (`src/click/core.py:3713-3733`)
  - Signature: `def __init__(self, param_decls: cabc.Sequence[str], required: bool | None=None, help: str | None=None, **attrs: t.Any) -> None`
  - Behavior: Positional parameter. If required is None, it is True when there is no default and nargs > 0 (default nargs is 1), and False when a default is given. A multiple kwarg raises TypeError. Exactly one decl is allowed, and the name is lowercased with '-' replaced by '_'. The metavar is upper-case, wrapped in [] if optional, and gets '...' when nargs != 1.
  - Edge case: Zero decls with expose_value=True raises TypeError
  - Edge case: More than one decl raises TypeError
  - Raises: `TypeError`

### Error conventions
Runtime user errors use the ClickException family. Context.fail raises UsageError. Missing values raise MissingParameter. Bad conversion or a wrong nargs count raises BadParameter. An unknown subcommand raises NoSuchCommand. Control flow uses Exit and Abort. NoArgsIsHelpError is raised when there are no args and no_args_is_help is set. Programmer errors (a bad param declaration, a missing callback, forward given a non-Command, a missing command name) raise TypeError with plain messages. Messages are wrapped in gettext `_()` / ngettext, with sentences ending in a period, such as 'Value must be an iterable.' and 'Takes {nargs} values but {len} were given.'. Some messages are not terminated, such as 'Got unexpected extra argument (x)'. Deprecation is reported as red text on stderr, 'DeprecationWarning: The ... is deprecated.', and does not use warnings.warn.

### Examples
ParameterSource comparison pattern from the docstring (`src/click/core.py:186-188`)
```
source = ctx.get_parameter_source("port")
if source < click.ParameterSource.DEFAULT_MAP:
    ...  # value was explicitly set
```
Group.command decorator registers a subcommand via add_command (not a test snippet; the implementation shows the usage) (`src/click/core.py:1852-1855`)
```
def decorator(f):
    cmd = command(*args, **kwargs)(f)
    self.add_command(cmd)
    return cmd
```
Group.invoke non-chain dispatch: resolve, then group callback, then sub-context (`src/click/core.py:2048-2052`)
```
cmd_name, cmd, args = self.resolve_command(ctx, args)
ctx.invoked_subcommand = cmd_name
super().invoke(ctx)
sub_ctx = cmd.make_context(cmd_name, args, parent=ctx)
```

### Tests
- `tests/test_context.py`: Uses the runner fixture or direct Context objects. Checks ensure_object/find_object, ctx.meta, multiple enter, the global context, make_pass_meta_decorator, and that UNSET is hidden from callbacks. Plain asserts. I only listed its test names and did not read the other listed test files.

### Extension points
- **Command.context_class / context_settings** (`src/click/core.py:1357`): Subclass Context and set context_class, or set the context_settings dict. make_context applies both.
- **Parameter.callback** (`src/click/core.py:2677`): Per-parameter callback(ctx, param, value) for validation or transformation. The returned value replaces the parameter's value.
- **Parameter.consume_value / type_cast_value / value_is_missing** (`src/click/core.py:2518`): Subclass Option or Argument to add new value sources (a config file, for example) or custom casting. The public override points are type_cast_value and consume_value.
- **Group.get_command / list_commands** (`src/click/core.py:1959`): Override for lazy or plugin-loaded subcommands. CommandCollection already uses this at line 2173.
- **Group.result_callback** (`src/click/core.py:1914`): Post-processing of subcommand results, including chained pipelines.
- **Command.get_help_option / format_* methods** (`src/click/core.py:1193`): Customize help rendering or the help option.
- **Command.shell_complete / Parameter.shell_complete** (`src/click/core.py:1416`): Custom completions.

### Gaps (model's judgment, not verifiable from code)
- There is no built-in config-file value source between the environment and default_map. Users must populate default_map by hand. Why plausible: The precedence chain in consume_value already has a clear slot for it, and ParameterSource could gain a member. Nearest: `Parameter.consume_value`
- Deprecation output uses echo to stderr rather than warnings.warn, so it cannot be filtered or turned into an error. Why plausible: The deprecation logic is centralized in Command.invoke and Parameter.handle_parse_result. Nearest: `Parameter.handle_parse_result`
- There is no declarative cross-parameter validation, such as mutually exclusive or required-together options. Why plausible: handle_parse_result already arbitrates between same-name params, so a similar hook could validate groups. Nearest: `Parameter.handle_parse_result`
- Group.resolve_command does only exact matching and token normalization. It has no abbreviation or 'did you mean' resolution of its own beyond the possibilities passed to NoSuchCommand. Why plausible: get_command and resolve_command are the natural override points. Nearest: `Group.resolve_command`

## Module card: `src/click/decorators.py`
src/click/decorators.py (626 lines) holds the decorator layer. It has context-passing decorators (pass_context, pass_obj, make_pass_decorator, pass_meta_key). It has command/group factories, which turn a function into a Command or Group. It has the param-attaching decorators option and argument. It has preconfigured eager or flag options: confirmation_option, password_option, version_option, custom_version_option and help_option. Params are stashed on `f.__click_params__` until command() consumes them in reversed order, which gives top-to-bottom declaration order. Preconfigured options use kwargs.setdefault, so callers can override most defaults. version_option and custom_version_option force their own callback.

### Interfaces
- **`pass_context`** (`src/click/decorators.py:28-36`)
  - Signature: `def pass_context(f: t.Callable[te.Concatenate[Context, P], R]) -> t.Callable[P, R]`
  - Behavior: Wraps f so that get_current_context() is passed as first positional arg; uses update_wrapper. Does not use ctx.invoke.
  - Edge case: Outside a context, get_current_context() raises RuntimeError at call time, not decoration time
- **`pass_obj`** (`src/click/decorators.py:39-48`)
  - Signature: `def pass_obj(f: t.Callable[te.Concatenate[T, P], R]) -> t.Callable[P, R]`
  - Behavior: Wraps f, passing get_current_context().obj as first arg; update_wrapper preserves metadata.
  - Edge case: Passes None if ctx.obj was never set
  - Edge case: Does not use ctx.invoke
- **`make_pass_decorator`** (`src/click/decorators.py:51-97`)
  - Signature: `def make_pass_decorator(object_type: type[T], ensure: bool=False) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]`
  - Behavior: Returns a decorator factory. Wrapper gets the current context, then ctx.ensure_object(object_type) if ensure=True, else ctx.find_object(object_type) (innermost matching ctx.obj walking parents). Calls ctx.invoke(f, obj, *args, **kwargs).
  - Edge case: ensure=False and no object found: obj is None, raises RuntimeError
  - Edge case: ensure=True creates object_type() and stores it on ctx.obj
  - Raises: `RuntimeError`
- **`pass_meta_key`** (`src/click/decorators.py:100-130`)
  - Signature: `def pass_meta_key(key: str, *, doc_description: str | None=None) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]`
  - Behavior: Returns a decorator that passes ctx.meta[key] as first arg via ctx.invoke. The decorator's __doc__ is generated from doc_description, defaulting to "the 'key' key from :attr:`click.Context.meta`". doc_description is keyword-only. Added in 8.0.
  - Edge case: Missing key raises KeyError at call time (direct dict index)
- **`command`** (`src/click/decorators.py:168-255`)
  - Signature: `def command(name: str | _AnyCallable | None=None, cls: type[CmdType] | None=None, **attrs: t.Any) -> Command | t.Callable[[_AnyCallable], Command | CmdType]`
  - Behavior: Creates a Command (or cls) from a function. Four typing overloads cover bare use (@command), name plus cls, cls only as keyword, and name only. If name is callable it is treated as the function, and asserts that cls is None and attrs is empty. Name defaults to f.__name__.lower() with _ replaced by -, then one trailing suffix (command, cmd, group, grp) stripped. Pops params from attrs (a given list is mutated in place) and extends it with reversed(f.__click_params__), then deletes that attribute. help defaults to f.__doc__ when attrs['help'] is None. Instantiates cls(name=..., callback=f, params=params, **attrs) and sets cmd.__doc__ = f.__doc__.
  - Edge case: Applying to an existing Command raises TypeError
  - Edge case: Bare use with cls or kwargs fails an assert, not a TypeError
  - Edge case: Suffix stripping only happens on the derived name, not an explicit name
  - Edge case: A function named only 'command' is not stripped, because rpartition gives no separator
  - Edge case: attrs.pop('params') on the shared attrs dict means reusing one decorator object on a second function loses the explicit params
  - Raises: `TypeError`
  - Raises (unconfirmed, likely via a helper): `AssertionError`
- **`group`** (`src/click/decorators.py:293-311`)
  - Signature: `def group(name: str | _AnyCallable | None=None, cls: type[GrpType] | None=None, **attrs: t.Any) -> Group | t.Callable[[_AnyCallable], Group | GrpType]`
  - Behavior: Same as command with cls defaulting to Group. If name is callable it calls command(cls=cls, **attrs)(name); otherwise command(name, cls, **attrs).
  - Edge case: Bare use with extra attrs is impossible because the callable is the name
  - Raises (unconfirmed, likely via a helper): `TypeError`
- **`argument`** (`src/click/decorators.py:324-349`)
  - Signature: `def argument(*param_decls: str, cls: type[Argument] | None=None, **attrs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Returns a decorator that builds cls(param_decls, **attrs), with cls defaulting to Argument. It attaches the param via _param_memo and returns f unchanged.
  - Edge case: If f is already a Command the param is appended to f.params (at end, not reversed)
  - Edge case: The Argument is built when the decorator is applied, not when argument() is called
- **`option`** (`src/click/decorators.py:352-377`)
  - Signature: `def option(*param_decls: str, cls: type[Option] | None=None, **attrs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Same as argument but builds an Option (cls defaults to Option). Stacked option decorators append to f.__click_params__ bottom-up, and command() reverses the list so the top decorator comes first.
  - Edge case: Applied over an existing Command it appends directly to cmd.params
  - Edge case: Each application creates a new Option instance
- **`confirmation_option`** (`src/click/decorators.py:380-401`)
  - Signature: `def confirmation_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Wraps option(). Default decl is --yes. Uses setdefault for is_flag=True, callback (ctx.abort() if value is falsy), expose_value=False, prompt=_('Do you want to continue?') and help=_('Confirm the action without prompting.').
  - Edge case: Any default can be overridden through kwargs
  - Edge case: Declining the prompt calls ctx.abort(), which raises Abort
- **`password_option`** (`src/click/decorators.py:404-418`)
  - Signature: `def password_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Wraps option(). Default decl is --password. Uses setdefault for prompt=True, confirmation_prompt=True and hide_input=True. The value is exposed to the function.
  - Edge case: Overridable through kwargs
- **`version_option`** (`src/click/decorators.py:421-556`)
  - Signature: `def version_option(version: str | None=None, *param_decls: str, package_name: str | None=None, prog_name: str | None=None, message: str | None=None, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Eager --version flag with expose_value=False. If version and package_name are both None, it inspects the caller's frame globals for __name__ (using __package__ if '__main__') and takes the top-level segment as package_name. The callback is forced, so a user-supplied callback is overwritten. The callback returns early if the value is falsy or ctx.resilient_parsing is set. prog_name defaults to ctx.find_root().info_name. The version is resolved lazily at invocation via importlib.metadata.version(package_name). If that fails it tries packages_distributions() for a unique distribution. Output is message % {prog, package, version} through echo(color=ctx.color), then ctx.exit(). Default message is _('%(prog)s, version %(version)s'). The signature is version, *param_decls, then keyword-only package_name, prog_name and message.
  - Edge case: Several distributions for one import name raise RuntimeError telling the user to pass package_name
  - Edge case: Zero matches raise RuntimeError saying the package is not installed
  - Edge case: version still None raises RuntimeError saying it could not be determined
  - Edge case: Decl default is --version
  - Edge case: The docstring says the message slots are frozen
  - Raises: `RuntimeError`
- **`custom_version_option`** (`src/click/decorators.py:559-598`)
  - Signature: `def custom_version_option(callback: t.Callable[[Context], str], *param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Added in 8.5.0. Eager --version flag. Takes callback(ctx) -> str, whose return value is echoed (color=ctx.color) before ctx.exit(). The internal show_version callback is forced over any kwargs callback. It is a no-op when the value is falsy or ctx.resilient_parsing is set. Defaults are setdefault is_flag=True, expose_value=False, is_eager=True and help=_('Show the version and exit.'). Default decl is --version.
  - Edge case: The callback return value is not type-checked; a non-str goes straight to echo
  - Edge case: Any exception from the callback propagates
- **`help_option`** (`src/click/decorators.py:601-625`)
  - Signature: `def help_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Eager --help flag. Callback show_help echoes ctx.get_help() (color=ctx.color) and calls ctx.exit(), unless the value is falsy or ctx.resilient_parsing is set. Defaults via setdefault are is_flag=True, expose_value=False, is_eager=True, help=_('Show this message and exit.') and callback=show_help. Default decl is --help.
  - Edge case: A custom callback in kwargs replaces show_help
  - Edge case: Names are customizable (see test_help_option_custom_names_and_class)
- **`_param_memo`** (`src/click/decorators.py:314-321`)
  - Signature: `def _param_memo(f: t.Callable[..., t.Any], param: Parameter) -> None`
  - Behavior: Private. Appends param to f.params if f is a Command. Otherwise it creates f.__click_params__ = [] if missing and appends. This is the point where decorators and command() communicate.
  - Edge case: Sets an attribute on f, so it fails on objects that reject attributes, such as builtins or slotted callables
  - Raises (unconfirmed, likely via a helper): `AttributeError`

### Error conventions
TypeError is raised when a callback is converted to a command twice (command, line 219). AssertionError (bare `assert` with a message) is used for misuse of the bare-decorator form (lines 211-212). RuntimeError is used for runtime resolution failures: no context object in make_pass_decorator, and version detection in version_option. Messages are lowercase-style sentences, quote names with !r, and end with a hint such as "Pass 'package_name' to disambiguate." or "Try passing 'package_name' instead." User-facing default strings are wrapped in gettext `_()`. Aborting goes through ctx.abort(), and early exit through ctx.exit(). Neither is raised directly here.

### Examples
custom_version_option with extra names (`tests/test_basic.py:936-939`)
```
@click.command()
@click.custom_version_option(lambda ctx: "custom 9.9.9", "-V", "--version")
def cli():
    pass
```
custom_version_option callback receives the Context (`tests/test_basic.py:946-954`)
```
@click.custom_version_option(lambda ctx: f"{ctx.info_name} 1.0")
# runner.invoke(cli, ["--version"], prog_name="mytool") -> "mytool 1.0\n"
```
Command and group decorators work without parentheses, including a custom cls via the group's command_class (`tests/test_command_decorators.py:23-29`)
```
@click.group(cls=CustomGroup)
def grp():
    pass

@grp.command
def cli():
    click.echo("hello custom command class")
```

### Tests
- `tests/test_basic.py`: Uses the runner fixture, with monkeypatch for the importlib.metadata cases. Asserts exit_code, result.output equality, and str(result.exception) for the version_option and custom_version_option RuntimeErrors. Parametrized over ['--version'] and ['-V'].
- `tests/test_command_decorators.py`: Uses runner.invoke and checks result.exception is None and result.output equals the expected text, for the paren-less command and group forms and for custom classes.
- `tests/test_options.py`: Parametrized checks of help_option with custom names and classes (line 1234), asserting on the invoke result and help output.
- `tests/test_context.py`: Covers pass_meta_key (lines 162-177, including its generated docstring) and make_pass_decorator (line 661). Asserts on the invoke output.
- `tests/typing/typing_options.py`: Not run by pytest. It is a typing example checked by mypy and pyright, with assert_type-style checks on option decorators.

### Extension points
- **option(cls=...)** (`src/click/decorators.py:352`): A custom Option subclass is instantiated with cls(param_decls, **attrs), so new option types or behaviors plug in here.
- **argument(cls=...)** (`src/click/decorators.py:324`): A custom Argument subclass.
- **command(cls=...)** (`src/click/decorators.py:168`): A custom Command or Group subclass. attrs are forwarded to its constructor.
- **_param_memo** (`src/click/decorators.py:314`): The shared param-attachment point. New decorators that add params (option or argument variants) can reuse it.
- **make_pass_decorator / pass_meta_key** (`src/click/decorators.py:51`): Factories for new pass_* decorators that inject typed context state.
- **preconfigured option wrappers (confirmation_option, password_option, help_option)** (`src/click/decorators.py:380`): New canned options can follow the setdefault-then-option() pattern, such as a --verbose counter or a --quiet flag.
- **custom_version_option callback** (`src/click/decorators.py:559`): A callback(ctx) -> str lets you render arbitrary version output.

### Gaps (model's judgment, not verifiable from code)
- No decorator for a --verbose/-v counter or a --quiet/--debug flag, which are common canned options Why plausible: Every canned option here is a thin setdefault wrapper around option(); a counting verbosity option would be the same size. Nearest: `confirmation_option`
- pass_context and pass_obj do not use ctx.invoke, while make_pass_decorator and pass_meta_key do. pass_meta_key has no ensure/default behavior. Why plausible: A default or ensure parameter on pass_meta_key would mirror make_pass_decorator(ensure=True). Nearest: `pass_meta_key`
- command() raises a bare AssertionError for misuse of the bare form, and the name of a Command object cannot be set from a decorator when it is applied twice Why plausible: Converting the asserts to TypeError, matching the double-conversion check, would be a small consistency fix. Nearest: `command`
- custom_version_option and version_option force their callback (kwargs['callback'] is overwritten), unlike help_option and confirmation_option, which use setdefault Why plausible: The inconsistency means a user-supplied callback is silently ignored. Nearest: `version_option`

## Module card: `src/click/types.py`
src/click/types.py defines ParamType (generic ABC: convert/fail/get_metavar/shell_complete/to_info_dict/split_envvar_value) and concrete types: FuncParamType, UNPROCESSED, STRING, Choice, DateTime, INT/IntRange, FLOAT/FloatRange, BOOL, UUID, File, Path, Tuple (composite). convert_type maps Python types/defaults/ParamType instances to ParamType singletons. Singletons are module-level t.Final instances at the end of the file. Failures go through ParamType.fail -> BadParameter.

### Interfaces
- **`ParamType`** (`src/click/types.py:65-239`)
  - Signature: `class ParamType(t.Generic[_ValueT_co, _InputT_contra], abc.ABC)`
  - Behavior: Generic ABC (line 65), class attrs is_composite=False, arity=1, name (must be set by subclass), envvar_list_splitter=None (whitespace). __call__ returns None for None, else self.convert(value,param,ctx). Base convert returns value unchanged. get_metavar and get_missing_message return None by default; shell_complete returns []. split_envvar_value does (rv or '').split(envvar_list_splitter). On Python<3.13 __class_getitem__ fills the 2nd type param with Any.
  - Edge case: to_info_dict derives param_type from class name stripped of 'ParamType'/'ParameterType' suffix; falls back to that when subclass has no `name`
  - Edge case: convert must tolerate param=None and ctx=None (prompts)
  - Edge case: split_envvar_value on None-like falsy rv gives [] when splitter is None, [''] otherwise
  - Raises: `BadParameter`
- **`ParamType.to_info_dict`** (`src/click/types.py:122-141`)
  - Signature: `def to_info_dict(self) -> ParamTypeInfoDict`
  - Behavior: Returns {'param_type': str, 'name': str}; subclasses extend with **super().to_info_dict().
  - Edge case: missing name attr uses derived class name
- **`ParamType.fail`** (`src/click/types.py:215-222`)
  - Signature: `def fail(self, message: str, param: Parameter | None=None, ctx: Context | None=None) -> t.NoReturn`
  - Behavior: Raises BadParameter(message, ctx=ctx, param=param); typed NoReturn.
  - Edge case: param and ctx optional
  - Raises: `BadParameter`
- **`ParamType.convert`** (`src/click/types.py:179-203`)
  - Signature: `def convert(self, value: _InputT_contra, param: Parameter | None, ctx: Context | None) -> _ValueT_co`
  - Behavior: Override point; identity by default (line 179).
  - Edge case: not called for None
- **`ParamType.shell_complete`** (`src/click/types.py:224-239`)
  - Signature: `def shell_complete(self, ctx: Context, param: Parameter, incomplete: str) -> list[CompletionItem]`
  - Behavior: Returns list of CompletionItem; default empty list.
- **`CompositeParamType`** (`src/click/types.py:242-247`)
  - Signature: `class CompositeParamType(ParamType[_ValueT_co])`
  - Behavior: ParamType subclass with is_composite=True and abstract arity property; base for Tuple.
- **`FuncParamType`** (`src/click/types.py:264-289`)
  - Signature: `class FuncParamType(ParamType[_ValueT_co], t.Generic[_ValueT_contra, _ValueT_co])  # __init__(self, func: t.Callable[[_ValueT_contra], _ValueT_co])`
  - Behavior: Wraps a callable; name=func.__name__. convert calls func(value); on ValueError fails with str(exc), or str(value) if message empty (bytes decoded utf-8 'replace' on UnicodeError). to_info_dict adds 'func'.
  - Edge case: only ValueError is caught; other exceptions propagate
  - Edge case: empty ValueError message falls back to the value
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Choice`** (`src/click/types.py:342-515`)
  - Signature: `class Choice(ParamType[_ValueT_co], t.Generic[_ValueT_co])  # __init__(self, choices: cabc.Iterable[_ValueT_co], case_sensitive: bool=True)`
  - Behavior: Choice(choices, case_sensitive=True); choices stored as tuple (iterable consumed once). convert normalizes value via normalize_choice, builds {original: normalized} mapping each call, returns first original whose normalized equals. Enum members normalize to .name, others to str(). normalize_choice applies ctx.token_normalize_func then casefold if not case_sensitive. get_metavar: for options with show_choices False uses upper-cased type names of choices; else 'a|b|c'; wrapped in {} for required argument, [] otherwise. shell_complete prefix matches normalized choices.
  - Edge case: value not in choices -> fail with get_invalid_choice_message (ngettext singular 'X is not Y.' when 1 choice)
  - Edge case: non-str values (ints, enums) are compared via normalized str
  - Edge case: duplicate normalized values: first match wins (no check despite docstring)
  - Edge case: ctx may be None
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Choice.normalize_choice`** (`src/click/types.py:406-424`)
  - Signature: `def normalize_choice(self, choice: object, ctx: Context | None) -> str`
  - Behavior: (choice, ctx)->str normalization hook; overridable (versionadded 8.2).
  - Edge case: Enum uses .name
- **`Choice.get_invalid_choice_message`** (`src/click/types.py:478-490`)
  - Signature: `def get_invalid_choice_message(self, value: t.Any, ctx: Context | None) -> str`
  - Behavior: Returns "'d' is not one of 'a', 'b', 'c'." using repr of normalized values; singular form for single choice.
  - Edge case: value repr uses raw value
- **`DateTime`** (`src/click/types.py:522-590`)
  - Signature: `class DateTime(ParamType[datetime])  # __init__(self, formats: cabc.Sequence[str] | None=None)`
  - Behavior: DateTime(formats=None); default formats '%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%Y-%m-%d %H:%M:%S' (used when formats falsy). convert returns datetime instances as-is, else tries strptime for each format in order.
  - Edge case: empty formats list falls back to defaults
  - Edge case: non-string non-datetime value: strptime raises TypeError (only ValueError caught)
  - Edge case: metavar '[fmt1|fmt2]'
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`IntRange`** (`src/click/types.py:744-765`)
  - Signature: `class IntRange(_NumberRangeBase[int, int], IntParamType)`
  - Behavior: IntRange(min=None,max=None,min_open=False,max_open=False,clamp=False); converts via int() then range-checks. With clamp, out-of-range returns bound (bound±1 if open).
  - Edge case: clamp checks min before max
  - Edge case: failure message '{value} is not in the range {range}.' e.g. '0<=x<=10'
  - Edge case: non-int string -> '... is not a valid integer.'
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`FloatRange`** (`src/click/types.py:776-816`)
  - Signature: `class FloatRange(_NumberRangeBase[float, float], FloatParamType)  # __init__(self, min: float | None=None, max: float | None=None, min_open: bool=False, max_open: bool=False, clamp: bool=False)`
  - Behavior: Like IntRange over float(); __init__ raises TypeError if clamp with min_open/max_open; _clamp on open bound raises RuntimeError.
  - Edge case: clamp with open bounds rejected at construction
  - Raises: `TypeError`, `RuntimeError`
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`BoolParamType`** (`src/click/types.py:819-885`)
  - Signature: `class BoolParamType(ParamType[bool])`
  - Behavior: BOOL singleton. convert uses str_to_bool: bools pass through, strings stripped/lowercased and looked up in class dict bool_states (1/0/yes/no/true/false/on/off/t/f/y/n/'' ).
  - Edge case: empty string -> False
  - Edge case: non-str non-bool value raises AttributeError on .strip
  - Edge case: unknown -> failure listing sorted recognized states
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`BoolParamType.str_to_bool`** (`src/click/types.py:856-868`)
  - Signature: `def str_to_bool(value: str | bool) -> bool | None`
  - Behavior: Static; returns bool or None if unknown.
- **`StringParamType`** (`src/click/types.py:304-326`)
  - Signature: `class StringParamType(ParamType[str])`
  - Behavior: STRING; bytes decoded with argv encoding, then filesystem encoding, then utf-8 replace; anything else str(value).
  - Edge case: never fails
- **`UnprocessedParamType`** (`src/click/types.py:292-301`)
  - Signature: `class UnprocessedParamType(ParamType[t.Any])`
  - Behavior: UNPROCESSED; returns value unchanged, name 'text'.
- **`UUIDParameterType`** (`src/click/types.py:888-907`)
  - Signature: `class UUIDParameterType(ParamType[uuid.UUID])`
  - Behavior: UUID singleton; returns uuid.UUID as-is, else strips string and uuid.UUID(value).
  - Edge case: only ValueError caught
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`File`** (`src/click/types.py:915-1043`)
  - Signature: `class File(ParamType[t.IO[t.Any]])  # __init__(self, mode: str='r', encoding: str | None=None, errors: str | None='strict', lazy: bool | None=None, atomic: bool=False)`
  - Behavior: File(mode='r',encoding=None,errors='strict',lazy=None,atomic=False); name 'filename'; envvar splitter os.path.pathsep. convert returns file-like objects (has read or write) unchanged. resolve_lazy_flag: explicit lazy wins; '-' -> not lazy; 'w' in mode -> lazy; else not lazy. Lazy uses _LazyFile registered with ctx.call_on_close(close_intelligently); otherwise open_stream and ctx.call_on_close closes (or flushes for std streams).
  - Edge case: ctx None: caller must close
  - Edge case: OSError -> '<filename>': strerror
  - Edge case: to_info_dict only mode and encoding
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Path`** (`src/click/types.py:1059-1251`)
  - Signature: `class Path(ParamType[_PathT_co, str | os.PathLike[str]], t.Generic[_PathT_co])  # __init__(self, exists: bool=False, file_okay: bool=True, dir_okay: bool=True, writable: bool=False, readable: bool=True, resolve_path: bool=False, allow_dash: bool=False, path_type: type[_PathT_co] | None=None, executable: bool=False)`
  - Behavior: Path(exists=False,file_okay=True,dir_okay=True,writable=False,readable=True,resolve_path=False,allow_dash=False,path_type=None,executable=False). Generic over converted type. name is 'file'/'directory'/'path' by flags. convert: skip checks for allowed dash; realpath if resolve_path; os.stat; missing -> returns value if not exists else fail; then file/dir check, readable, writable, executable checks; result via coerce_path_result.
  - Edge case: nonexistent path with exists=False skips all further checks
  - Edge case: executable check uses original value not resolved rv
  - Edge case: bytes dash handled
  - Edge case: path_type str/bytes use fsdecode/fsencode, else path_type(value)
  - Edge case: to_info_dict omits executable, resolve_path
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Path.coerce_path_result`** (`src/click/types.py:1147-1159`)
  - Signature: `def coerce_path_result(self, value: str | os.PathLike[str]) -> _PathT_co`
  - Behavior: Converts to self.type if not already instance.
  - Edge case: None keeps value
- **`Tuple`** (`src/click/types.py:1258-1308`)
  - Signature: `class Tuple(CompositeParamType[tuple[t.Any, ...]])  # __init__(self, types: cabc.Sequence[type[t.Any] | ParamType[t.Any]])`
  - Behavior: Tuple(types) composite; each element passed through convert_type; name '<int text>'; arity=len(types). convert checks len(value) equals arity then converts each element.
  - Edge case: length mismatch fail with ngettext message
  - Edge case: len(value) on non-sized raises TypeError
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`convert_type`** (`src/click/types.py:1356-1397`)
  - Signature: `def convert_type(ty: t.Any | None=None, default: t.Any | None=None) -> ParamType[t.Any]`
  - Behavior: convert_type(ty=None, default=None): _guess_type first (default type / first item of list/tuple default; nested sequences become tuple of types), then tuple->Tuple, ParamType instance as is, str/None->STRING, int->INT, float->FLOAT, bool->BOOL; guessed-but-unknown types -> STRING; otherwise FuncParamType(ty).
  - Edge case: ParamType subclass (uninstantiated) raises AssertionError under __debug__
  - Edge case: empty list default -> STRING
  - Edge case: explicit non-recognized class e.g. pathlib.Path becomes FuncParamType
  - Raises: `AssertionError`

### Error conventions
Validation failures call ParamType.fail which raises click.exceptions.BadParameter(message, ctx, param). Messages are gettext-wrapped (_ / ngettext), use {value!r} reprs, end with a period (e.g. "'d' is not one of 'a', 'b'."; "{value!r} is not a valid integer."; "{name} {filename!r} does not exist."). Programmer errors use TypeError (FloatRange open+clamp), RuntimeError (open float clamp), AssertionError (uninstantiated ParamType class in convert_type). Non-ValueError exceptions from conversion propagate.

### Examples
Choice invalid message (`tests/test_types/test_Choice.py:5-7`)
```
choice = click.Choice(["a", "b", "c"])
message = choice.get_invalid_choice_message("d", ctx=None)
assert message == "'d' is not one of 'a', 'b', 'c'."
```
Path with path_type in a command (`tests/test_types/test_Path.py:179-184`)
```
cli = click.Command(
    "cli",
    params=[click.Argument(["p"], type=click.Path(path_type=cls))],
    callback=lambda p: p,
)
result = runner.invoke(cli, ["a/b/c.txt"], standalone_mode=False)
```
info dict for DateTime (`tests/test_info_dict.py:120-121`)
```
click.DateTime(["%Y-%m-%d"]),
{"param_type": "DateTime", "name": "datetime", "formats": ["%Y-%m-%d"]},
```
Path error message includes escaped newline (`tests/test_types/test_Path.py:162-166`)
```
with pytest.raises(click.BadParameter) as exc_info:
    click.Path(dir_okay=False).convert(tempdir, None, None)
assert "my\\ndir" in exc_info.value.message
```

### Tests
- `tests/test_info_dict.py`: Parametrized with pytest.param(..., id=...) comparing to_info_dict() output dicts of each type (Choice, DateTime, IntRange, Path, Tuple, etc.) to expected dicts.
- `tests/test_types/test_Choice.py`: Single plain test calling get_invalid_choice_message directly with ctx=None and asserting the exact string.
- `tests/test_types/test_Path.py`: Plain functions using pytest.raises(click.BadParameter), tmp_path/monkeypatch, runner.invoke on a Command with standalone_mode=False and checking result.return_value, parametrized path_type; also t.get_args(click.Path[pathlib.Path]).

### Extension points
- **ParamType subclassing (convert/get_metavar/shell_complete/to_info_dict)** (`src/click/types.py:65`): Custom types subclass ParamType, set name, override convert and call self.fail.
- **Choice.normalize_choice** (`src/click/types.py:406`): Override for custom normalization (aliases, prefix matching).
- **Choice.get_invalid_choice_message** (`src/click/types.py:478`): Override for custom error text, e.g. did-you-mean suggestions.
- **BoolParamType.bool_states** (`src/click/types.py:822`): Class-level dict mapping that could be extended or made configurable.
- **_NumberRangeBase._clamp** (`src/click/types.py:700`): Abstract hook for new numeric range types.
- **convert_type** (`src/click/types.py:1356`): Dispatch chain on Python type; a place to register new type mappings (e.g. UUID, datetime, enum, Path).
- **Path.coerce_path_result** (`src/click/types.py:1147`): Override for custom result coercion.
- **File.resolve_lazy_flag** (`src/click/types.py:975`): Override lazy-open policy.

### Gaps (model's judgment, not verifiable from code)
- No Enum-based type; Choice accepts enums but the dispatch in convert_type doesn't map enum classes to Choice Why plausible: Choice already supports enum members via normalize_choice using .name Nearest: `convert_type`
- BOOL true/false strings are not user-configurable Why plausible: The docstring on bool_states explicitly mentions future work for configurability Nearest: `BoolParamType.bool_states`
- DateTime has no timezone-aware default formats or fromisoformat support Why plausible: Docstring says defaults are non-timezone-aware; formats list is the only knob Nearest: `DateTime`
- Path lacks a check for file extension / suffix or max size Why plausible: Path validations are a flat list of checks in convert; one more fits the pattern Nearest: `Path.convert`
- Path.to_info_dict omits executable, resolve_path and path_type Why plausible: Info dict is meant for documentation tools and other flags are included Nearest: `Path.to_info_dict`
- Open float ranges cannot be clamped (RuntimeError); math.nextafter could implement it Why plausible: Source comment mentions nextafter as an option Nearest: `FloatRange._clamp`

## Module card: `src/click/parser.py`
src/click/parser.py is Click's private argv parser, adapted from optparse. Core.Command.make_parser (core.py:1227) builds an _OptionParser(ctx), and each Parameter's add_to_parser registers itself. Command.parse_args (core.py:1371-1372) then calls parser.parse_args. The parser does no type conversion or defaults. It returns raw values in a dict keyed by dest, the leftover args, and a list of parameter objects in command-line order. Unset values are the UNSET sentinel, and FLAG_NEEDS_VALUE marks an option whose value was omitted. The old public names (OptionParser, Argument, Option, split_opt, normalize_opt, ParsingState, split_arg_string) are served by a module `__getattr__` that emits DeprecationWarning.

### Interfaces
- **`_OptionParser`** (`src/click/parser.py:224-500`)
  - Signature: `class _OptionParser  # __init__(self, ctx: Context | None=None)`
  - Behavior: Internal parser class. __init__(ctx=None) stores ctx and defaults allow_interspersed_args=True and ignore_unknown_options=False. If ctx is given, both flags are copied from ctx. It starts with _opt_prefixes={'-','--'}, plus empty _short_opt, _long_opt and _args. The docstring carries a '.. deprecated:: 8.2' note.
  - Edge case: ctx=None disables token normalization and resilient parsing
  - Edge case: Flags are copied once at construction, so later changes to ctx are not seen
- **`_OptionParser.add_option`** (`src/click/parser.py:265-288`)
  - Signature: `def add_option(self, obj: CoreOption, opts: cabc.Sequence[str], dest: str | None, action: str | None=None, nargs: int=1, const: t.Any | None=None) -> None`
  - Behavior: Normalizes each opt string with _normalize_opt (which applies ctx.token_normalize_func). It builds an _Option, adds its prefixes to _opt_prefixes, and registers its short opts in _short_opt and its long opts in _long_opt. The dest is passed in explicitly and never inferred. action defaults to 'store' and nargs to 1. Valid actions are store, store_const, append, append_const and count.
  - Edge case: An opt with no prefix (starts alnum) raises ValueError from _Option
  - Edge case: An unknown action is not checked here; it fails later in _Option.process
  - Edge case: Re-registering an opt string silently overwrites the earlier one
  - Raises (unconfirmed, likely via a helper): `ValueError`
- **`_OptionParser.add_argument`** (`src/click/parser.py:290-296`)
  - Signature: `def add_argument(self, obj: CoreArgument, dest: str | None, nargs: int=1) -> None`
  - Behavior: Appends an _Argument(obj, dest, nargs) to _args. Positional order is the order of calls.
  - Edge case: Two arguments with nargs<0 cause a TypeError later, in _unpack_args
- **`_OptionParser.parse_args`** (`src/click/parser.py:298-314`)
  - Signature: `def parse_args(self, args: list[str]) -> tuple[dict[str, t.Any], list[str], list[CoreParameter]]`
  - Behavior: Builds a _ParsingState(args), runs _process_args_for_options and then _process_args_for_args. It returns (state.opts, state.largs, state.order). The input list is consumed (popped) in place.
  - Edge case: UsageError is swallowed when ctx.resilient_parsing is true, and the partial results are returned
  - Edge case: With ctx=None the error always propagates
  - Raises: `UsageError`
  - Raises (unconfirmed, likely via a helper): `NoSuchOption`, `BadOptionUsage`, `BadArgumentUsage`
- **`_OptionParser._process_args_for_options`** (`src/click/parser.py:327-341`)
  - Signature: `def _process_args_for_options(self, state: _ParsingState) -> None`
  - Behavior: Pops from rargs one arg at a time. A bare '--' stops processing and is dropped. An arg whose first character is in _opt_prefixes and whose length is >1 goes to _process_opts. Any other arg is appended to largs if interspersed args are allowed. Otherwise it is pushed back onto rargs and parsing stops.
  - Edge case: A lone '-' is treated as positional
  - Edge case: The '--' check uses `return`, so the remaining args stay in rargs
- **`_OptionParser._process_args_for_args`** (`src/click/parser.py:316-325`)
  - Signature: `def _process_args_for_args(self, state: _ParsingState) -> None`
  - Behavior: Calls _unpack_args(largs+rargs, [nargs of each arg]) and then each _Argument.process. The leftovers become largs and rargs is cleared.
  - Edge case: Extra positionals are returned as leftover args
  - Edge case: Missing positionals are UNSET
  - Raises (unconfirmed, likely via a helper): `BadArgumentUsage`, `TypeError`
- **`_OptionParser._process_opts`** (`src/click/parser.py:470-500`)
  - Signature: `def _process_opts(self, arg: str, state: _ParsingState) -> None`
  - Behavior: Splits the arg on the first '=' to get an explicit value and normalizes the name. It tries _match_long_opt first, so single-dash long options like -foo match. On NoSuchOption it falls back to _match_short_opt if the arg's first two characters are not a registered prefix. For a '--x' arg it re-raises, unless ignore_unknown_options is set, in which case it appends the arg to largs.
  - Edge case: An explicit '=value' on a short option is treated as part of the arg string
  - Raises: `NoSuchOption`
- **`_OptionParser._match_long_opt`** (`src/click/parser.py:363-388`)
  - Signature: `def _match_long_opt(self, opt: str, explicit_value: str | None, state: _ParsingState) -> None`
  - Behavior: Looks the name up in _long_opt. A value-taking option has the explicit value inserted at rargs[0] and then reads its value through _get_value_from_state. A flag with an explicit value raises BadOptionUsage; otherwise its value is UNSET. It finishes with option.process.
  - Edge case: Unknown opt raises NoSuchOption with possibilities=_long_opt for suggestions
  - Raises: `NoSuchOption`, `BadOptionUsage`
- **`_OptionParser._match_short_opt`** (`src/click/parser.py:390-428`)
  - Signature: `def _match_short_opt(self, arg: str, state: _ParsingState) -> None`
  - Behavior: Walks the characters of a clustered arg such as -abc. A value-taking option consumes the rest of the arg as its value. With ignore_unknown_options, unknown characters are collected and re-appended to largs as prefix+chars.
  - Edge case: Each char is normalized individually
  - Edge case: The prefix is arg[0]
  - Raises: `NoSuchOption`
- **`_OptionParser._get_value_from_state`** (`src/click/parser.py:430-468`)
  - Signature: `def _get_value_from_state(self, option_name: str, option: _Option, state: _ParsingState) -> str | cabc.Sequence[str] | T_UNSET | T_FLAG_NEEDS_VALUE`
  - Behavior: Takes nargs values from rargs. If fewer than nargs remain, it returns FLAG_NEEDS_VALUE when obj._flag_needs_value is set, and otherwise raises BadOptionUsage. For nargs==1, if the option allows an omitted value and the next arg looks like an option, it returns FLAG_NEEDS_VALUE instead of consuming it. For nargs>1 it returns a tuple.
  - Edge case: The message is pluralized with ngettext
  - Raises: `BadOptionUsage`
- **`_Option`** (`src/click/parser.py:127-182`)
  - Signature: `class _Option  # __init__(self, obj: CoreOption, opts: cabc.Sequence[str], dest: str | None, action: str | None=None, nargs: int=1, const: t.Any | None=None)`
  - Behavior: Holds obj, dest, action, nargs, const, prefixes, _short_opts and _long_opts. An opt is short if it has a 1-character prefix and a 1-character name; everything else is long. takes_value is true for the store and append actions. process(value, state) applies the action to state.opts and appends obj to state.order.
  - Edge case: An opt with no prefix raises ValueError 'Invalid start character for option (x)'
  - Edge case: An unknown action raises ValueError("unknown action '...'") at process time
  - Edge case: count adds 1 starting from 0
  - Edge case: append and append_const use setdefault(dest, [])
  - Raises: `ValueError`
- **`_Argument`** (`src/click/parser.py:185-213`)
  - Signature: `class _Argument  # __init__(self, obj: CoreArgument, dest: str | None, nargs: int=1)`
  - Behavior: Holds dest, nargs and obj. process(value, state) sets state.opts[dest]=value and appends obj to state.order. For nargs>1, a partial tuple (some UNSET) raises BadArgumentUsage, and an all-UNSET tuple becomes UNSET. An empty tuple (from nargs=-1 with nothing left) becomes UNSET.
  - Edge case: Partial nargs>1 values raise
  - Edge case: Empty variadic values are UNSET, not ()
  - Raises: `BadArgumentUsage`
- **`_ParsingState`** (`src/click/parser.py:216-221`)
  - Signature: `class _ParsingState  # __init__(self, rargs: list[str])`
  - Behavior: Mutable state with opts (dict), largs (list), rargs (the input list) and order (list of params).
- **`_unpack_args`** (`src/click/parser.py:51-108`)
  - Signature: `def _unpack_args(args: cabc.Sequence[str], nargs_spec: cabc.Sequence[int]) -> tuple[cabc.Sequence[str | cabc.Sequence[str | T_UNSET] | T_UNSET], list[str]]`
  - Behavior: Distributes args across nargs_spec. A positive nargs takes that many, with UNSET fill for missing items (a tuple when nargs>1). A negative nargs takes all the remainder, and specs after it are filled from the right. It returns (tuple of values, leftover list).
  - Edge case: Missing items are UNSET
  - Edge case: The wildcard slot is a tuple, possibly empty
  - Raises: `TypeError`
- **`_split_opt`** (`src/click/parser.py:111-117`)
  - Signature: `def _split_opt(opt: str) -> tuple[str, str]`
  - Behavior: Returns (prefix, rest). An alnum first character gives ('', opt). A doubled first character gives (opt[:2], opt[2:]). Otherwise it returns (first, opt[1:]).
  - Edge case: An empty string yields first='' and ('', '')
- **`_normalize_opt`** (`src/click/parser.py:120-124`)
  - Signature: `def _normalize_opt(opt: str, ctx: Context | None) -> str`
  - Behavior: Applies ctx.token_normalize_func to the name part and keeps the prefix. It returns opt unchanged if ctx is None or no func is set.
  - Edge case: ctx=None returns opt unchanged
- **`__getattr__`** (`src/click/parser.py:503-533`)
  - Signature: `def __getattr__(name: str) -> object`
  - Behavior: Module-level shim. For OptionParser, Argument, Option, split_opt, normalize_opt and ParsingState, it emits a DeprecationWarning (stacklevel=2) and returns globals()['_'+name]. split_arg_string is lazily imported from click.shell_completion with its own warning.
  - Edge case: Unknown names raise AttributeError(name)
  - Raises: `AttributeError`

### Error conventions
Usage problems raise click.exceptions subclasses. NoSuchOption is raised for unknown options and is given possibilities for suggestions. BadOptionUsage(option_name, msg) covers a missing value or a value attached to a flag. BadArgumentUsage covers a partial nargs on an argument. Messages are gettext-wrapped and formatted with {name!r}, for example "Option '--x' requires an argument." and "Option {name!r} requires {nargs} arguments." (pluralized with ngettext). Programmer errors use ValueError (invalid option prefix, unknown action) and TypeError (two variadic arguments). The module `__getattr__` raises AttributeError for unknown names and warns with DeprecationWarning.

### Examples
Default prefixes of a fresh parser (`tests/test_parser.py:22-24`)
```
parser = _OptionParser()
assert parser._opt_prefixes == {"-", "--"}
```
Custom prefixes are collected through Option.add_to_parser (`tests/test_parser.py:27-32`)
```
ctx = click.Context(click.Command("test"))
parser = _OptionParser(ctx)
click.Option("+p", is_flag=True).add_to_parser(parser, ctx)
click.Option("!e", is_flag=True).add_to_parser(parser, ctx)
assert parser._opt_prefixes == {"-", "--", "+", "!"}
```
Deprecated attribute access must be wrapped in pytest.warns (`tests/test_deprecations.py:46-50`)
```
with pytest.warns(DeprecationWarning, match=name):
    value = getattr(module, name)
assert value == target
```

### Tests
- `tests/test_parser.py`: Plain functions with bare asserts. They check the _opt_prefixes set on _OptionParser directly, with and without custom-prefix options added via Option.add_to_parser. Parsing behavior itself is mostly covered indirectly by tests/test_options.py and tests/test_arguments.py (not read here).
- `tests/test_deprecations.py`: test_attr_deprecated is parametrized over (module, name, target). It uses pytest.warns(DeprecationWarning, match=name) around getattr and asserts equality with the _-prefixed target. test_unknown_attribute_raises expects AttributeError for click, click.core, click.parser and click.utils.

### Extension points
- **Parameter.add_to_parser** (`src/click/core.py:2516`): The abstract hook (core.py:2516) that each Parameter subclass implements to register itself with the parser. Option's version is at core.py:3325 and Argument's at core.py:3800. A custom Parameter can call parser.add_option or add_argument with its own action and const.
- **Command.make_parser** (`src/click/core.py:1227`): Subclasses can override it to return a customized _OptionParser subclass or to add extra options.
- **_Option.process** (`src/click/parser.py:169`): The action dispatch if/elif chain. A new action such as 'extend' or 'store_true_once' would be added here, with takes_value updated to match.
- **_OptionParser._opt_prefixes** (`src/click/parser.py:262`): The set of recognized option prefixes. It is extended automatically when options with new prefixes are added.
- **_normalize_opt** (`src/click/parser.py:120`): Hooks into Context.token_normalize_func, for example for case-insensitive or alias normalization of option names.

### Gaps (model's judgment, not verifiable from code)
- Unknown-action validation at add_option time, so a bad action fails when registered rather than at parse time Why plausible: _Option.__init__ already validates prefixes eagerly, but the action is only checked in process() (parser.py:181). Nearest: `_Option.__init__`
- Detection of duplicate or conflicting option registrations Why plausible: add_option silently overwrites entries in _short_opt and _long_opt (parser.py:285-288). Nearest: `_OptionParser.add_option`
- Unique-prefix abbreviation matching of long options (as argparse does) Why plausible: _match_long_opt requires an exact match and only offers 'possibilities' for suggestions (parser.py:366-367). Nearest: `_OptionParser._match_long_opt`
- Explicit '=value' support for short options, such as -o=value Why plausible: The '=' split in _process_opts feeds only the long-option path. Short options fall back to _match_short_opt with the '=' as part of the value. Nearest: `_OptionParser._process_opts`
- Direct unit tests of parse_args, _unpack_args and the error paths Why plausible: tests/test_parser.py covers only the prefix sets, so direct parser-level tests are thin. Nearest: `_OptionParser.parse_args`

## Module card: `src/click/termui.py`
termui.py is the public front-end for interactive terminal helpers. prompt/confirm loop over a module-level input function (visible_prompt_func = input, or hidden_prompt_func = getpass). style/unstyle/secho build and strip ANSI codes. progressbar, edit, launch, getchar, raw_terminal and get_pager_file lazily import their implementations from _termui_impl. echo_via_pager, clear and pause are implemented here, on top of get_pager_file, echo, getchar and isatty.

### Interfaces
- **`prompt`** (`src/click/termui.py:168-286`)
  - Signature: `def prompt(text: str, default: V | str | None=None, hide_input: bool=False, confirmation_prompt: bool | str=False, type: ParamType[V, str] | type[V] | None=None, value_proc: t.Callable[[str], V] | None=None, prompt_suffix: str=': ', show_default: bool | str=True, err: bool=False, show_choices: bool=True) -> V`
  - Behavior: Prompts until valid input (termui.py:168-286). value_proc defaults to convert_type(type, default). Prompt text comes from _build_prompt: it appends Choice choices if show_choices, and ' [default]' if show_default is true and default is not None. A str show_default is shown instead of the default. Empty input returns the default if default is not None, otherwise it re-prompts. The default goes through value_proc like typed input. Uses hidden_prompt_func if hide_input, else visible_prompt_func, via _readline_prompt. confirmation_prompt=True uses 'Repeat for confirmation'; a str customizes it. A mismatch echoes 'Error: The two entered values do not match.' and restarts. A UsageError from value_proc is echoed as 'Error: {message}', and the message is masked with '***' if hide_input. KeyboardInterrupt and EOFError become Abort, with an extra newline echoed if hide_input.
  - Edge case: default=None with empty input loops forever until input or abort
  - Edge case: empty first value and empty confirmation value are treated as matching
  - Edge case: a non-str default is cast to str only for typing; it still goes through value_proc
  - Edge case: err=True redirects stdout to stderr during input()
  - Raises: `Abort`
- **`confirm`** (`src/click/termui.py:289-345`)
  - Signature: `def confirm(text: str, default: bool | None=False, abort: bool=False, prompt_suffix: str=': ', show_default: bool=True, err: bool=False) -> bool`
  - Behavior: Yes/no prompt (289-345). Accepts y/yes/n/no, case-insensitive and stripped. Empty input returns default unless default is None. Anything else echoes 'Error: invalid input' and repeats. The suffix shows y/n, Y/n or y/N via _build_prompt. abort=True raises Abort on a negative answer. KeyboardInterrupt and EOFError become Abort.
  - Edge case: default=None requires an explicit answer
  - Edge case: show_default=False hides the [Y/n] hint
  - Raises: `Abort`
- **`get_pager_file`** (`src/click/termui.py:348-364`)
  - Signature: `def get_pager_file(color: bool | None=None) -> t.ContextManager[t.TextIO]`
  - Behavior: Returns a context manager yielding a writable text file for pager output (348-364). Resolves color via resolve_color_default, then delegates to _termui_impl.get_pager_file(color=...). Added in 8.4.0.
  - Edge case: color=None means autodetect
- **`echo_via_pager`** (`src/click/termui.py:367-399`)
  - Signature: `def echo_via_pager(text_or_generator: cabc.Iterable[str] | t.Callable[[], cabc.Iterable[str]] | str, color: bool | None=None) -> None`
  - Behavior: Pages text (367-399). Accepts a str, an iterable, or a generator function; a generator function is called. Non-str elements are converted with str(). Writes each element to get_pager_file and flushes after every write, then writes a trailing newline (chained '\n').
  - Edge case: a plain str becomes a one-element list
  - Edge case: a generator object (not a function) is handled as a general iterable
- **`progressbar`** (`src/click/termui.py:443-599`)
  - Signature: `def progressbar(iterable: cabc.Iterable[V] | None=None, length: int | None=None, label: str | None=None, hidden: bool=False, show_eta: bool=True, show_percent: bool | None=None, show_pos: bool=False, item_show_func: t.Callable[[V | None], str | None] | None=None, fill_char: str='#', empty_char: str='-', bar_template: str='%(label)s  [%(bar)s]  %(info)s', info_sep: str='  ', width: int=36, file: t.TextIO | None=None, color: bool | None=None, update_min_steps: int=1) -> ProgressBar[V]`
  - Behavior: Builds a _termui_impl.ProgressBar (443-599) after resolving color. Defaults: show_eta=True, fill_char '#', empty_char '-', bar_template '%(label)s  [%(bar)s]  %(info)s', info_sep two spaces, width 36 (0 means full terminal width), update_min_steps=1. The length-only overload has no iterable or item_show_func. hidden=True suppresses all output; with no tty and hidden=False, only the label is printed.
  - Edge case: neither iterable nor length is rejected by ProgressBar (see test_progressbar_init_exceptions)
  - Edge case: show_percent defaults to True only if a length is known
- **`clear`** (`src/click/termui.py:602-613`)
  - Signature: `def clear() -> None`
  - Behavior: Clears the screen (602-613). Does nothing if stdout is not a tty. Otherwise echoes '\033[2J\033[1;1H' with nl=False.
  - Edge case: no-op when piped
- **`style`** (`src/click/termui.py:641-765`)
  - Signature: `def style(text: t.Any, fg: int | tuple[int, int, int] | str | None=None, bg: int | tuple[int, int, int] | str | None=None, bold: bool | None=None, dim: bool | None=None, underline: bool | None=None, overline: bool | None=None, italic: bool | None=None, blink: bool | None=None, reverse: bool | None=None, strikethrough: bool | None=None, reset: bool=True) -> str`
  - Behavior: Returns text wrapped in ANSI codes (641-765). A non-str text is converted with str(). Codes are emitted in a fixed order: fg, bg (offset 10), bold, dim, underline, overline, italic, blink, reverse, strikethrough. A flag set to None emits nothing; False emits the off code (22 for bold and dim, 24, 55, 23, 25, 27, 29). reset=True appends \033[0m. Colors can be a name, an int 0-255, or an RGB 3-tuple/list.
  - Edge case: True/False are rejected as colors
  - Edge case: index 0 is valid as of 8.5.0
  - Edge case: unknown name, out-of-range int or bad tuple raises ValueError
  - Raises: `ValueError`
- **`unstyle`** (`src/click/termui.py:768-777`)
  - Signature: `def unstyle(text: str) -> str`
  - Behavior: Strips ANSI codes from text by delegating to _compat.strip_ansi (768-777).
- **`secho`** (`src/click/termui.py:780-811`)
  - Signature: `def secho(message: t.Any | None=None, file: t.IO[t.AnyStr] | None=None, nl: bool=True, err: bool=False, color: bool | None=None, **styles: t.Any) -> None`
  - Behavior: echo(style(message, **styles), file, nl, err, color) (780-811). A None message is passed straight to echo. bytes and bytearray messages skip styling.
  - Edge case: message=None prints only a newline, or nothing with nl=False
  - Edge case: unknown style kwargs raise TypeError from style()
  - Raises (unconfirmed, likely via a helper): `TypeError`, `ValueError`
- **`edit`** (`src/click/termui.py:848-920`)
  - Signature: `def edit(text: str | bytes | bytearray | None=None, editor: str | None=None, env: cabc.Mapping[str, str] | None=None, require_save: bool=True, extension: str='.txt', filename: str | os.PathLike[str] | cabc.Iterable[str | os.PathLike[str]] | None=None) -> str | bytes | bytearray | None`
  - Behavior: Opens an editor (848-920). It builds _termui_impl.Editor(editor, env, require_save, extension). With filename=None it returns ed.edit(text), which is None if the editor saved nothing and require_save is true. With filename (a str or PathLike is wrapped in a tuple) it calls ed.edit_files and returns None. The require_save default is False in the bytes overload and True otherwise.
  - Edge case: when filename is given, require_save and extension are ignored
  - Edge case: filename accepts an iterable of paths for editors that handle several files
  - Raises: `UsageError`
- **`launch`** (`src/click/termui.py:923-949`)
  - Signature: `def launch(url: str, wait: bool=False, locate: bool=False) -> int`
  - Behavior: Calls _termui_impl.open_url(url, wait, locate) and returns the exit code (923-949). locate=True opens a file manager instead. wait=True only works if the launched program blocks.
  - Edge case: xdg-open does not block
- **`getchar`** (`src/click/termui.py:957-984`)
  - Signature: `def getchar(echo: bool=False) -> str`
  - Behavior: Reads one character (957-984). On first call it caches _termui_impl.getchar in the module global _getchar. If _getchar is already set it uses that, so tests can override it by setting click.termui._getchar. The echo flag shows the typed character.
  - Edge case: may return more than one character
  - Edge case: always reads from the terminal rather than piped stdin
- **`raw_terminal`** (`src/click/termui.py:987-990`)
  - Signature: `def raw_terminal() -> AbstractContextManager[int]`
  - Behavior: Returns the _termui_impl.raw_terminal() context manager, which yields an int (987-990). It has no docstring and is not in the documented API.
- **`pause`** (`src/click/termui.py:993-1024`)
  - Signature: `def pause(info: str | None=None, err: bool=False) -> None`
  - Behavior: Waits for a keypress (993-1024). Returns immediately if stdin or stdout is not a tty. info defaults to 'Press any key to continue...'; an empty string prints nothing. Calls getchar(), swallowing KeyboardInterrupt and EOFError. A trailing newline is echoed in a finally block if info is truthy.
  - Edge case: info='' suppresses the message and the newline
- **`hidden_prompt_func`** (`src/click/termui.py:79-82`)
  - Signature: `def hidden_prompt_func(prompt: str) -> str`
  - Behavior: Calls getpass.getpass(prompt) (79-82). It is a module-level hook used when hide_input is true.
- **`visible_prompt_func`** (`src/click/termui.py:34-34`)
  - Signature: `visible_prompt_func: t.Callable[[str], str] = input`
  - Behavior: Module-level hook, default builtin input (34). It is used by prompt and confirm, and tests monkeypatch it. It is looked up at call time.
- **`_build_prompt`** (`src/click/termui.py:108-125`)
  - Signature: `def _build_prompt(text: str, suffix: str, show_default: bool | str=False, default: object | None=None, show_choices: bool=True, type: object | None=None) -> str`
  - Behavior: Builds the prompt string (108-125): text, then the optional Choice list, then the default preview, then the suffix. A str show_default renders as ' [(str)]'. File defaults are rendered by their name via _format_default.
  - Edge case: default None shows no preview unless show_default is a str
- **`_interpret_color`** (`src/click/termui.py:616-638`)
  - Signature: `def _interpret_color(color: int | tuple[int, int, int] | str, offset: int=0) -> str`
  - Behavior: Converts a color to an SGR parameter string (616-638). Names map through the _ansi_colors dict. An int 0-255 becomes '38;5;N' (48 with offset 10). A 3-int tuple or list becomes '38;2;r;g;b'.
  - Edge case: bool is rejected
  - Raises: `ValueError`

### Error conventions
Abort is raised for user interrupt (KeyboardInterrupt, EOFError) and for a declined confirm(abort=True). Validation errors (UsageError) inside prompt are not raised; they are echoed as 'Error: <message>' and the prompt repeats. confirm echoes 'Error: invalid input'. style raises ValueError('Unknown color ...'). edit raises UsageError, from _termui_impl, when the editor cannot be started. Messages are wrapped in gettext `_()`, are capitalized, and prefixed 'Error: '.

### Examples
prompt default cast through type (`tests/test_utils/test_prompt.py:11-12`)
```
monkeypatch.setattr(sys, "stdin", StringIO("\n"))
value = click.prompt("value", default="100", type=int)
```
secho with color forced and bg style, output asserted via runner.isolation (`tests/test_termui.py:307-310`)
```
with runner.isolation() as (out, _, _):
    click.secho(value, nl=False, color=True, bg="magenta")
    result = out.getvalue()
```
Docstring usage of progressbar (`src/click/termui.py:486-488`)
```
with progressbar(items) as bar:
    for item in bar:
        do_something_with(item)
```
style examples (`src/click/termui.py:665-665`)
```
click.echo(click.style('More colors', fg=(255, 12, 128), bg=117))
```

### Tests
- `tests/test_termui.py`: Uses the runner fixture and monkeypatch. Progressbar tests check rendered output and the private ProgressBar methods (format_eta, format_pos, format_bar, format_progress_line). Other tests cover secho bytes via runner.isolation(), the Choice prompt text, getchar on Windows (patching click.termui._getchar to None), editor command and path normalization, pager shlex splitting and less detection, and echo_via_pager flushing per write. Asserts are bare asserts. Platform skips use skipif(WIN).
- `tests/test_utils/test_prompt.py`: Replaces sys.stdin with StringIO, or monkeypatches click.termui.visible_prompt_func and hidden_prompt_func. Checks the returned type and value, that Abort is raised on interrupt or EOF, and that the full prompt string is passed to the readline function. Uses capfd and capsys, and runner for EOF.

### Extension points
- **visible_prompt_func** (`src/click/termui.py:34`): Replace the input function for prompt and confirm, for example with a custom readline or a scripted input.
- **hidden_prompt_func** (`src/click/termui.py:79`): Replace the hidden-input implementation, for example to show asterisks.
- **prompt (value_proc / type parameters)** (`src/click/termui.py:168`): Pass a custom ParamType or value_proc callable to add validation or conversion. Raise UsageError to re-prompt.
- **_getchar** (`src/click/termui.py:954`): Override the single-char reader for testing or alternative input backends.
- **_ansi_colors** (`src/click/termui.py:36`): Add named colors by extending this dict.
- **progressbar (item_show_func, bar_template)** (`src/click/termui.py:443`): Callbacks and templates that customize bar rendering.
- **echo_via_pager** (`src/click/termui.py:367`): Generator or callable sources for streaming paged output; get_pager_file allows custom writing.

### Gaps (model's judgment, not verifiable from code)
- confirm has no way to customize the accepted yes/no tokens (localized answers) or the invalid-input message, and has no type or choices equivalent. Why plausible: prompt already supports custom value_proc, and the messages are hard-coded literals. Nearest: `confirm`
- There is no max-retry limit or non-interactive fallback in prompt, which loops forever on invalid input. It only stops on EOF or interrupt. Why plausible: A small attempts parameter in the existing while loop would add it. Nearest: `prompt`
- style cannot take a combined style spec or reusable Style object. Colors are limited to a fixed dict and there is no theme registry. Why plausible: _ansi_colors and style are the natural place for a style registry. Nearest: `style`
- raw_terminal is undocumented and has no docstring. There is also no multi-line prompt and no select-from-list helper. Why plausible: getchar and raw_terminal already provide the primitives for key-driven menus. Nearest: `getchar`

## Module card: `src/click/shell_completion.py`
src/click/shell_completion.py implements Click's tab completion. shell_complete() parses the `<shell>_<instruction>` value of the env var. It looks up a ShellComplete subclass in the `_available_shells` registry and either prints the shell script (`source`) or prints completions (`complete`). Command._main_shell_completion (core.py:1619-1649) calls it and then calls sys.exit with its return value. ShellComplete.get_completions resolves a Context chain (`_resolve_context`), picks the object that should complete (`_resolve_incomplete`), and calls that object's `.shell_complete(ctx, incomplete)`. That returns a list of CompletionItem. Each shell subclass reads COMP_WORDS and COMP_CWORD from os.environ and formats items in its own wire format. Bash, Zsh, Fish and PowerShell are built in. Other shells can be added with add_completion_class.

### Interfaces
- **`shell_complete`** (`src/click/shell_completion.py:19-55`)
  - Signature: `def shell_complete(cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, complete_var: str, instruction: str) -> t.Literal[0, 1]`
  - Behavior: Does `shell, _, instruction = instruction.partition('_')`, then looks up the class with get_completion_class(shell). It builds `comp_cls(cli, ctx_args, prog_name, complete_var)`. For 'source' it writes `comp.source().encode()` with echo(nl=False) and returns 0. For 'complete' it writes `comp.complete().encode()` with echo (newline appended) and returns 0. Output is written as bytes so Windows does not turn LF into CRLF.
  - Edge case: Unknown shell returns 1
  - Edge case: Unknown instruction returns 1
  - Edge case: A value with no underscore gives shell=whole string and instruction='', so it returns 1 unless the shell name is unregistered, which also returns 1
- **`CompletionItem`** (`src/click/shell_completion.py:67-101`)
  - Signature: `class CompletionItem(t.Generic[_ValueT_co])  # __init__(self, value: _ValueT_co, type: str='plain', help: str | None=None, **kwargs: t.Any)`
  - Behavior: Generic class with __slots__ ('value','type','help','_info'). `type` defaults to 'plain'. Click uses 'dir' and 'file' for special shell handling. `help` defaults to None. Extra kwargs go into `_info`.
  - Edge case: __getattr__ returns None for any unknown attribute instead of raising AttributeError (`_info.get(name)`)
  - Edge case: Extra kwargs are not used by built-in shells
- **`CompletionItem.__init__`** (`src/click/shell_completion.py:88-98`)
  - Signature: `def __init__(self, value: _ValueT_co, type: str='plain', help: str | None=None, **kwargs: t.Any) -> None`
  - Behavior: Sets value, type, help and `_info=kwargs`.
  - Edge case: Arbitrary kwargs accepted
- **`CompletionItem.__getattr__`** (`src/click/shell_completion.py:100-101`)
  - Signature: `def __getattr__(self, name: str) -> t.Any`
  - Behavior: Returns `self._info.get(name)`. It is only called when normal attribute lookup fails.
  - Edge case: Missing keys give None
- **`ShellComplete`** (`src/click/shell_completion.py:277-385`)
  - Signature: `class ShellComplete  # __init__(self, cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, complete_var: str)`
  - Behavior: Base class. Takes cli, ctx_args, prog_name and complete_var. Subclasses set the class attributes `name` and `source_template`, and implement get_completion_args and format_completion. complete() runs get_completion_args, then get_completions, then format_completion per item, and joins with '\n'.
  - Edge case: The base class has no `name` or `source_template` defaults, so using it directly for source() fails
  - Edge case: The tests use the base class directly for get_completions
- **`ShellComplete.func_name`** (`src/click/shell_completion.py:319-324`)
  - Signature: `def func_name(self) -> str`
  - Behavior: Property. Replaces '-' with '_' in prog_name, strips non-word ASCII characters, and returns `_{safe}_completion`.
  - Edge case: Dots and other punctuation are removed (not turned into underscores)
- **`ShellComplete.source_vars`** (`src/click/shell_completion.py:326-336`)
  - Signature: `def source_vars(self) -> _SourceVarsDict`
  - Behavior: Returns a dict with complete_func, complete_var and prog_name for formatting the template.
  - Edge case: Subclasses can override this to add template variables
- **`ShellComplete.source`** (`src/click/shell_completion.py:338-344`)
  - Signature: `def source(self) -> str`
  - Behavior: Returns `self.source_template % self.source_vars()`, a %-style format.
  - Edge case: Literal % in a custom template must be escaped as %%
  - Raises (unconfirmed, likely via a helper): `KeyError`
- **`ShellComplete.get_completion_args`** (`src/click/shell_completion.py:346-351`)
  - Signature: `def get_completion_args(self) -> tuple[list[str], str]`
  - Behavior: Abstract. Returns (args, incomplete).
  - Raises: `NotImplementedError`
- **`ShellComplete.get_completions`** (`src/click/shell_completion.py:353-365`)
  - Signature: `def get_completions(self, args: list[str], incomplete: str) -> list[CompletionItem[str]]`
  - Behavior: Calls `_resolve_context(cli, ctx_args, prog_name, args)`, then `_resolve_incomplete(ctx, args, incomplete)`. Then returns `obj.shell_complete(ctx, incomplete)`.
  - Edge case: incomplete may be ''
  - Edge case: `args` can be mutated, because an `--opt=val` incomplete appends the option name to it
  - Edge case: ctx_args gets resilient_parsing=True set on it (mutated)
- **`ShellComplete.format_completion`** (`src/click/shell_completion.py:367-373`)
  - Signature: `def format_completion(self, item: CompletionItem[str]) -> str`
  - Behavior: Abstract. Turns a CompletionItem into a string for the shell script.
  - Raises: `NotImplementedError`
- **`ShellComplete.complete`** (`src/click/shell_completion.py:375-385`)
  - Signature: `def complete(self) -> str`
  - Behavior: Returns the newline-joined formatted completions.
  - Edge case: No completions gives an empty string
- **`BashComplete`** (`src/click/shell_completion.py:388-444`)
  - Signature: `class BashComplete(ShellComplete)`
  - Behavior: name='bash'. get_completion_args splits COMP_WORDS with split_arg_string and reads int(COMP_CWORD). args = cwords[1:cword]; incomplete = cwords[cword], or '' on IndexError. format_completion returns `type,value` and ignores help. source() first runs _check_version.
  - Edge case: Missing env vars raise KeyError
  - Edge case: A non-integer COMP_CWORD raises ValueError
  - Edge case: Help text is dropped
  - Raises (unconfirmed, likely via a helper): `KeyError`, `ValueError`
- **`BashComplete._check_version`** (`src/click/shell_completion.py:395-425`)
  - Signature: `def _check_version() -> None`
  - Behavior: Static method. Runs `bash --norc -c 'echo ${BASH_VERSION}'` with subprocess. It echoes a message to stderr if bash is older than 4.4 or the version cannot be detected. It does not raise or abort.
  - Edge case: No bash on PATH prints the 'Couldn't detect Bash version' message
  - Edge case: Tests patch it out with monkeypatch
- **`ZshComplete`** (`src/click/shell_completion.py:447-476`)
  - Signature: `class ZshComplete(ShellComplete)`
  - Behavior: name='zsh'. Same args logic as Bash. format_completion returns `type\nvalue\nhelp` with help defaulting to '_'. Colons in value are escaped as `\:` only when help is not '_'.
  - Edge case: Colon escaping applies only to items that have help text
  - Edge case: The script is deliberately frozen for backward compatibility
- **`FishComplete`** (`src/click/shell_completion.py:479-513`)
  - Signature: `class FishComplete(ShellComplete)`
  - Behavior: name='fish'. COMP_CWORD holds the partial word itself, not an index. args = cwords[1:]. If incomplete is non-empty it is passed through split_arg_string(...)[0], and the same word is popped from args if it is the last one. format_completion returns `type,value` and appends `\t<help>` when help is set. In help, newlines are escaped as `\n` and tabs become spaces (8.4.2).
  - Edge case: An empty COMP_CWORD gives incomplete=''
  - Edge case: A quoted partial word is unquoted by the split
- **`PowerShellComplete`** (`src/click/shell_completion.py:516-547`)
  - Signature: `class PowerShellComplete(ShellComplete)`
  - Behavior: name='powershell' (added in 8.5.0). Same args logic as Bash, using an index COMP_CWORD. format_completion returns `type\nvalue\nhelp`, with help defaulting to '_'. \r and \n in help become spaces.
  - Edge case: The PowerShell script consumes 3 lines per item
- **`add_completion_class`** (`src/click/shell_completion.py:560-577`)
  - Signature: `def add_completion_class(cls: type[_ShellCompleteT], name: str | None=None) -> type[_ShellCompleteT]`
  - Behavior: Sets `_available_shells[name or cls.name] = cls` and returns cls, so it works as a decorator (no-argument form only).
  - Edge case: Overwrites an existing registration silently
  - Edge case: Raises AttributeError if name is None and cls has no `name`
  - Raises (unconfirmed, likely via a helper): `AttributeError`
- **`get_completion_class`** (`src/click/shell_completion.py:588-595`)
  - Signature: `def get_completion_class(shell: str) -> type[ShellComplete] | None`
  - Behavior: Returns `_available_shells.get(shell)`, or None if the shell is not registered. Typing overloads exist for bash, fish and zsh. There is no overload for powershell, which falls to the `str` overload.
  - Edge case: Unknown shell returns None
- **`split_arg_string`** (`src/click/shell_completion.py:598-631`)
  - Signature: `def split_arg_string(string: str) -> list[str]`
  - Behavior: Uses shlex.shlex(posix=True) with whitespace_split=True and commenters=''. If shlex raises ValueError (unclosed quote or trailing backslash), it appends the partial token `lex.token` to the output.
  - Edge case: 'example \'my file' gives ['example','my file']
  - Edge case: 'example my\\' gives ['example','my']
  - Edge case: Empty string gives []
  - Edge case: '#' is not treated as a comment
- **`_resolve_context`** (`src/click/shell_completion.py:691-749`)
  - Signature: `def _resolve_context(cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, args: list[str]) -> Context`
  - Behavior: Sets ctx_args['resilient_parsing']=True and calls cli.make_context(prog_name, args.copy(), **ctx_args). For Groups it follows subcommands with resolve_command and make_context(resilient_parsing=True). Chained groups use allow_extra_args and allow_interspersed_args=False. It returns the deepest context. It stops early if resolve_command returns None for the command.
  - Edge case: Callbacks and prompts are not run (resilient parsing)
  - Edge case: Unknown subcommand returns the current ctx
- **`_resolve_incomplete`** (`src/click/shell_completion.py:752-796`)
  - Signature: `def _resolve_incomplete(ctx: Context, args: list[str], incomplete: str) -> tuple[Command | Parameter, str]`
  - Behavior: Normalizes '=': `incomplete=='='` becomes ''. `--opt=val` is split, and the name is appended to args. If '--' is not in args and incomplete starts with an option prefix, it returns (ctx.command, incomplete). Otherwise it returns the first Option for which _is_incomplete_option is true. Next it returns the first Argument that is still incomplete. Finally it falls back to (ctx.command, incomplete), which gives subcommand names.
  - Edge case: After '--', option-like words are values
  - Edge case: Flags and counts never need values
- **`_is_incomplete_argument`** (`src/click/shell_completion.py:634-654`)
  - Signature: `def _is_incomplete_argument(ctx: Context, param: Parameter) -> bool`
  - Behavior: True for an Argument that has nargs=-1, or was not given on the command line, or has nargs>1 with fewer values than nargs.
  - Edge case: Non-Argument params return False
- **`_is_incomplete_option`** (`src/click/shell_completion.py:666-688`)
  - Signature: `def _is_incomplete_option(ctx: Context, args: list[str], param: Parameter) -> bool`
  - Behavior: True if param is an Option that is not a flag or count, and the last option-looking arg within nargs positions from the end is in param.opts.
  - Edge case: Flags and counts return False

### Error conventions
The module raises no exceptions deliberately. shell_complete signals failure through return codes: 1 for an unknown shell or instruction, 0 for success. Command._main_shell_completion then calls sys.exit(rv). Abstract methods raise bare NotImplementedError (lines 351 and 373). Missing COMP_WORDS or COMP_CWORD env vars surface as KeyError from os.environ. split_arg_string catches the shlex ValueError internally. BashComplete._check_version reports problems through echo(..., err=True) using gettext `_()` messages. The messages are plain sentences ending in a period, for example "Shell completion is not supported for Bash versions older than 4.4.".

### Examples
Direct get_completions test helper (`tests/test_shell_completion.py:24-26`)
```
def _get_completions(cli, args, incomplete):
    comp = ShellComplete(cli, {}, cli.name, "_CLICK_COMPLETE")
    return comp.get_completions(args, incomplete)
```
Full end-to-end complete via env var (`tests/test_shell_completion.py:388-391`)
```
cli = Group("cli", commands=[Command("a"), Command("b", help="bee")])
env["_CLI_COMPLETE"] = f"{shell}_complete"
result = runner.invoke(cli, env=env)
assert result.output == expect
```
Registering a custom shell (`tests/test_shell_completion.py:520-528`)
```
class MyshComplete(ShellComplete):
    name = "mysh"
    source_template = "dummy source"
assert add_completion_class(MyshComplete) is MyshComplete
```
CompletionItem extra attributes (`tests/test_shell_completion.py:337-339`)
```
c = CompletionItem("test", a=1)
assert c.a == 1
assert c.b is None
```

### Tests
- `tests/test_shell_completion.py`: Plain pytest functions with bare asserts. A helper `_get_words` builds a ShellComplete directly and compares the lists of values. Full-flow tests use the `runner` fixture with `env={'_CLI_COMPLETE': '<shell>_complete'}` and compare result.output strings. They are parametrized over bash, zsh, fish and powershell. The `_patch_for_completion` fixture monkeypatches BashComplete._check_version. The `_restore_available_shells` fixture snapshots and restores `_available_shells` for the add_completion_class tests. There are also tests for zsh colon escaping, LF line endings, closed files, and the fish and powershell help escaping.

### Extension points
- **add_completion_class / _available_shells** (`src/click/shell_completion.py:560`): Register a new ShellComplete subclass for another shell (for example nushell or elvish) by setting name, source_template, get_completion_args and format_completion.
- **ShellComplete.source_vars / source_template** (`src/click/shell_completion.py:326`): Add template variables or replace the script in a subclass.
- **ShellComplete.get_completions** (`src/click/shell_completion.py:353`): Filter, sort or post-process the CompletionItems before they are formatted.
- **ShellComplete.format_completion** (`src/click/shell_completion.py:367`): Emit custom wire formats, including use of CompletionItem kwargs metadata.
- **CompletionItem kwargs (_info)** (`src/click/shell_completion.py:88`): Carry custom metadata such as a group or a suffix to custom shell classes.
- **Parameter shell_complete callback** (`src/click/core.py:2878`): Per-parameter custom completion functions, which produce the CompletionItem lists.
- **Command._main_shell_completion** (`src/click/core.py:1619`): Override to change the complete_var or hook completion.

### Gaps (model's judgment, not verifiable from code)
- No way to unregister a shell or list the registered shells publicly. Callers must touch the private `_available_shells`. Why plausible: The registry already has add and get functions; remove and list are small additions. Nearest: `add_completion_class`
- Bash ignores help text, and Bash has no description support. Why plausible: Other shells show the help, and it could be added through the script template. Nearest: `BashComplete.format_completion`
- The four get_completion_args implementations are duplicated, and bash, zsh and powershell are identical. Why plausible: A shared helper or intermediate base class would remove the copies. Nearest: `ShellComplete.get_completion_args`
- No dedicated error handling or diagnostics for a malformed instruction (it just returns 1 silently), and missing env vars raise KeyError. Why plausible: A friendly message is feasible. Nearest: `shell_complete`
- The get_completion_class overloads omit 'powershell'. Why plausible: A typing oversight with a one-line fix. Nearest: `get_completion_class`

## Module card: `src/click/formatting.py`
src/click/formatting.py holds click's help-text layout code. It has a module-level FORCED_WIDTH override, the helpers measure_table, iter_rows, wrap_text and join_options, and the in-memory HelpFormatter class. HelpFormatter accumulates strings in a buffer and tracks the current indent. It provides write_usage, write_heading, write_text, write_dl, the section and indentation context managers, and getvalue. Width is measured with term_len, which ignores ANSI escapes. wrap_text delegates to click._textwrap.TextWrapper, which I did not read. Command.format_help and Group.format_help in core.py create the formatter through Context.make_formatter, which uses Context.formatter_class (core.py:315, 638-649).

### Interfaces
- **`wrap_text`** (`src/click/formatting.py:31-107`)
  - Signature: `def wrap_text(text: str, width: int=78, initial_indent: str='', subsequent_indent: str='', preserve_paragraphs: bool=False) -> str`
  - Behavior: wrap_text(text, width=78, initial_indent='', subsequent_indent='', preserve_paragraphs=False) -> str. It calls text.expandtabs() first, then builds a click._textwrap.TextWrapper with replace_whitespace=False. Without preserve_paragraphs it returns wrapper.fill(text). With preserve_paragraphs it splits text.splitlines() into paragraphs at empty lines. The first line's leading indent (measured with term_len) is recorded per paragraph and re-applied through wrapper.extra_indent. Lines within a paragraph are joined with spaces. If a paragraph's first line is only '\b' (checked with strip()), the marker line is dropped and the remaining lines are kept verbatim through wrapper.indent_only, joined with '\n'. Paragraphs are joined with '\n\n'. Since 8.4.0, width ignores ANSI escapes.
  - Edge case: Empty text returns '' without the initial_indent, which is why write_usage special-cases empty args.
  - Edge case: A single leading '\b' paragraph keeps its line breaks and indentation.
  - Edge case: Tabs are expanded to 8-column stops.
  - Edge case: Styled long words are broken between visible characters (test_wrap_text_visible_width).
- **`measure_table`** (`src/click/formatting.py:14-21`)
  - Signature: `def measure_table(rows: cabc.Iterable[tuple[str, str]]) -> tuple[int, ...]`
  - Behavior: Takes an iterable of row tuples and returns a tuple of the maximum term_len for each column index, ordered by column index.
  - Edge case: An empty rows iterable returns ().
  - Edge case: Rows of differing length are measured per index.
- **`iter_rows`** (`src/click/formatting.py:24-28`)
  - Signature: `def iter_rows(rows: cabc.Iterable[tuple[str, str]], col_count: int) -> cabc.Iterator[tuple[str, ...]]`
  - Behavior: Generator that pads each row tuple with empty strings up to col_count. It does `row + ('',) * (col_count - len(row))`.
  - Edge case: A row longer than col_count is yielded unchanged.
  - Edge case: rows must contain tuples, because a list row would fail on tuple concatenation.
- **`join_options`** (`src/click/formatting.py:302-320`)
  - Signature: `def join_options(options: cabc.Iterable[str]) -> tuple[str, bool]`
  - Behavior: Takes option strings and returns (', '.join(sorted opts), any_prefix_is_slash). The prefix of each option comes from parser._split_opt(opt)[0]. Options are stably sorted by prefix length, so '-v' comes before '--verbose'. The flag is True if any prefix is exactly '/'.
  - Edge case: An empty iterable returns ('', False).
  - Edge case: Options with equal prefix length keep their input order.
- **`HelpFormatter`** (`src/click/formatting.py:110-299`)
  - Signature: `class HelpFormatter  # __init__(self, indent_increment: int=2, width: int | None=None, max_width: int | None=None)`
  - Behavior: HelpFormatter(indent_increment=2, width=None, max_width=None). max_width defaults to 80. If width is None it uses FORCED_WIDTH when set. Otherwise it uses max(min(shutil.get_terminal_size().columns, max_width) - 2, 50). Attributes are indent_increment, width, current_indent (starts at 0) and buffer (a list of str). Output is always in memory.
  - Edge case: The computed width has a floor of 50.
  - Edge case: An explicit width is used as given, with no clamp.
- **`HelpFormatter.write`** (`src/click/formatting.py:146-148`)
  - Signature: `def write(self, string: str) -> None`
  - Behavior: Appends the string to self.buffer with no processing. All other write_* methods go through it, so overriding it intercepts everything.
- **`HelpFormatter.indent`** (`src/click/formatting.py:150-152`)
  - Signature: `def indent(self) -> None`
  - Behavior: Adds indent_increment to current_indent.
  - Edge case: There is no lower bound check.
- **`HelpFormatter.dedent`** (`src/click/formatting.py:154-156`)
  - Signature: `def dedent(self) -> None`
  - Behavior: Subtracts indent_increment from current_indent.
  - Edge case: It can go negative if unbalanced.
- **`HelpFormatter.write_usage`** (`src/click/formatting.py:158-202`)
  - Signature: `def write_usage(self, prog: str, args: str='', prefix: str | None=None) -> None`
  - Behavior: write_usage(prog, args='', prefix=None). The default prefix is _('Usage:') + ' '. It builds usage_prefix = f'{prefix:>{current_indent}}{prog} '. With empty args it writes usage_prefix.rstrip(' ') and '\n' and returns. Otherwise, if width - current_indent >= term_len(usage_prefix) + 20, it writes wrap_text(args) with initial_indent=usage_prefix and a subsequent indent of spaces matching the prefix width. If not, it writes the prefix, then '\n', then args wrapped with an indent of max(current_indent, term_len(prefix)) + 4. Both non-empty branches end with '\n'.
  - Edge case: Empty args gives 'Usage: prog\n' with no trailing space.
  - Edge case: A styled prefix is measured with term_len.
  - Edge case: The prefix is right-aligned to current_indent, so a prefix longer than the indent is not padded.
- **`HelpFormatter.write_heading`** (`src/click/formatting.py:204-206`)
  - Signature: `def write_heading(self, heading: str) -> None`
  - Behavior: Writes f"{'':>{current_indent}}{heading}:\n". A colon is always appended.
  - Edge case: A heading that already ends in ':' gets a double colon.
- **`HelpFormatter.write_paragraph`** (`src/click/formatting.py:208-211`)
  - Signature: `def write_paragraph(self) -> None`
  - Behavior: Writes '\n' only if the buffer is non-empty. This avoids a leading blank line.
  - Edge case: It does nothing on a fresh formatter.
- **`HelpFormatter.write_text`** (`src/click/formatting.py:213-227`)
  - Signature: `def write_text(self, text: str) -> None`
  - Behavior: Wraps text with wrap_text(text, self.width, initial_indent and subsequent_indent set to ' ' * current_indent, preserve_paragraphs=True), then writes '\n'. The result honors the '\b' no-rewrap marker.
  - Edge case: Empty text writes only '\n'.
- **`HelpFormatter.write_dl`** (`src/click/formatting.py:229-271`)
  - Signature: `def write_dl(self, rows: cabc.Iterable[tuple[str, str]], col_max: int=30, col_spacing: int=2) -> None`
  - Behavior: write_dl(rows, col_max=30, col_spacing=2). The rows are materialised into a list. The first column width is min(widest term, col_max) + col_spacing. Each term is written at current_indent. If the term is empty-valued (second is empty) only a newline follows. If term_len(first) fits within first_col - col_spacing, it is padded to the column. Otherwise the description goes on the next line, indented first_col + current_indent. The description is wrapped with wrap_text(second, max(width - first_col - 2, 10), preserve_paragraphs=True). The first wrapped line follows the term, and the continuation lines are indented by first_col + current_indent.
  - Edge case: Rows with a length other than 2 (including an empty rows list) raise TypeError.
  - Edge case: Short rows are padded via iter_rows.
  - Edge case: A second value that wraps to no lines writes '\n'.
  - Edge case: The text width has a floor of 10.
  - Raises: `TypeError`
- **`HelpFormatter.section`** (`src/click/formatting.py:274-286`)
  - Signature: `def section(self, name: str) -> cabc.Generator[None]`
  - Behavior: Context manager that calls write_paragraph, then write_heading(name), then indent(). It yields, and dedent() runs in a finally block.
  - Edge case: Dedent is guaranteed even if the body raises.
- **`HelpFormatter.indentation`** (`src/click/formatting.py:289-295`)
  - Signature: `def indentation(self) -> cabc.Generator[None]`
  - Behavior: Context manager that calls indent(), yields, then calls dedent() in a finally block.
- **`HelpFormatter.getvalue`** (`src/click/formatting.py:297-299`)
  - Signature: `def getvalue(self) -> str`
  - Behavior: Returns ''.join(self.buffer).
  - Edge case: Returns '' if nothing has been written.
- **`FORCED_WIDTH`** (`src/click/formatting.py:11-11`)
  - Signature: `FORCED_WIDTH: int | None = None`
  - Behavior: Module-level `int | None`, default None. HelpFormatter.__init__ reads it when width is None. testing.py sets it to 80 during CliRunner isolation (testing.py:437-438) and restores it afterwards (testing.py:592).
  - Edge case: It is read at construction time only.

### Error conventions
The only exception raised directly is TypeError("Expected two columns for definition list") in HelpFormatter.write_dl. The message is a short sentence in capitalized style, with no trailing period and no values interpolated. Nothing else validates its input. The user-facing 'Usage:' string goes through gettext (`_`).

### Examples
HelpFormatter.write_text at a fixed width and indent (`tests/test_formatting.py:426-433`)
```
formatter = click.HelpFormatter(width=len("  Lorem ipsum dolor sit amet,"))
formatter.current_indent = 2
formatter.write_text(text)
actual = formatter.getvalue()
assert actual == "  Lorem ipsum dolor sit amet,\n  consectetur adipiscing elit\n"
```
Styled usage prefix is measured by visible width (`tests/test_formatting.py:507-514`)
```
formatter = click.HelpFormatter(width=40)
formatter.write_usage("cli", "[OPTIONS]", prefix=styled_prefix)
visible = strip_ansi(formatter.getvalue())
assert visible == "Usage: cli [OPTIONS]\n"
```
wrap_text with ANSI input compared with the stripped equivalent (`tests/test_formatting.py:492-500`)
```
styled = click.formatting.wrap_text(body, width=width, initial_indent=initial_indent)
plain = click.formatting.wrap_text(strip_ansi(body), width=width, initial_indent=strip_ansi(initial_indent))
assert [strip_ansi(l) for l in styled.splitlines()] == plain.splitlines()
```
End-to-end help output at a forced terminal width (`tests/test_formatting.py:30-35`)
```
result = runner.invoke(cli, ["--help"], terminal_width=60)
assert result.output.splitlines() == ["Usage: cli [OPTIONS]", "", "  First paragraph.", ...]
```

### Tests
- `tests/test_formatting.py`: Plain pytest functions using the `runner` fixture. They call runner.invoke(cli, ['--help'], terminal_width=N) and compare result.output.splitlines() to an exact list of lines. Direct unit tests build click.HelpFormatter(...) and compare getvalue() to an exact string. The ANSI tests are parametrized with pytest.param(..., id=...), and they compare strip_ansi output of styled input against plain input. They cover wrapping of long usage lines, '\b' paragraphs, empty-args usage, docstring truncation and usage errors.

### Extension points
- **Context.formatter_class** (`src/click/core.py:315`): Set formatter_class to a HelpFormatter subclass (for example one that overrides write_dl, write_usage or write_heading) so every command renders with it. Context.make_formatter (core.py:638-649) instantiates it with width=terminal_width and max_width=max_content_width.
- **HelpFormatter.write** (`src/click/formatting.py:146`): Override to post-process or style every chunk, or to stream the output instead of buffering it.
- **HelpFormatter.write_usage prefix parameter** (`src/click/formatting.py:158`): A caller-supplied (possibly styled) prefix replaces 'Usage: '.
- **HelpFormatter.write_dl col_max and col_spacing** (`src/click/formatting.py:229`): Subclasses can change the column layout, for example a different col_max, or extra columns beyond two.
- **FORCED_WIDTH** (`src/click/formatting.py:11`): Module-level override of the default width, used by the testing runner.

### Gaps (model's judgment, not verifiable from code)
- write_dl accepts only two columns, so a three-column table (for example option, default and description) is not possible. Why plausible: measure_table and iter_rows are already generic over any number of columns. Only the `len(widths) != 2` check restricts write_dl. Nearest: `HelpFormatter.write_dl`
- Hanging-indent or bullet-list text helpers. Only write_text with the '\b' marker preserves layout. Why plausible: wrap_text already takes initial_indent and subsequent_indent separately, so a write_text variant exposing them is a small addition. Nearest: `HelpFormatter.write_text`
- write_heading has no way to skip the colon or take a custom suffix. Why plausible: The format string is hard-coded as heading plus ':'. A parameter would be a small change. Nearest: `HelpFormatter.write_heading`
- The max_width default of 80 and the minimum width of 50 are hard-coded, with no configuration. Why plausible: Related constants such as col_max and col_spacing are already parameters on write_dl. Nearest: `HelpFormatter.__init__`

## Module card: `src/click/exceptions.py`
src/click/exceptions.py defines Click's exception hierarchy. ClickException (exit_code 1) and UsageError (exit_code 2) can be shown to the user via show(). Subclasses cover bad or missing parameters, unknown options and commands, and bad option or argument usage. FileError is a ClickException. Abort and Exit are RuntimeErrors used only for control flow. NoArgsIsHelpError is also defined here and is not in the role description. Only FileError has a dedicated test file. I did not read core.py, docs, or the other tests that exercise these classes.

### Interfaces
- **`ClickException`** (`src/click/exceptions.py:35-65`)
  - Signature: `class ClickException(Exception)  # __init__(self, message: str)`
  - Behavior: Base class for exceptions Click catches and prints. __init__(message) calls Exception.__init__, caches show_color = resolve_color_default() because the context is gone by print time, and stores message. exit_code is a ClassVar equal to 1. format_message() returns message. __str__ returns message. show(file=None) writes 'Error: {message}' to get_text_stderr() (when file is None) via echo, using the cached show_color.
  - Edge case: file=None defaults to stderr
  - Edge case: show_color may be None
- **`ClickException.format_message`** (`src/click/exceptions.py:51-52`)
  - Signature: `def format_message(self) -> str`
  - Behavior: Returns self.message. Subclasses override it to build the user-facing text, and show() always goes through it.
- **`ClickException.show`** (`src/click/exceptions.py:57-65`)
  - Signature: `def show(self, file: t.IO[t.Any] | None=None) -> None`
  - Behavior: Echoes the translated 'Error: {message}' line to the given file, or to stderr by default. Colour comes from the show_color cached at construction.
  - Edge case: file=None means stderr
- **`UsageError`** (`src/click/exceptions.py:68-111`)
  - Signature: `class UsageError(ClickException)  # __init__(self, message: str, ctx: Context | None=None)`
  - Behavior: exit_code 2. __init__(message, ctx=None) stores ctx and cmd (ctx.command, or None when there is no ctx). show() prints the usage text from ctx.get_usage(), then, if the command has a help option, a hint such as "Try 'cmd --help' for help.". The hint uses the longest help option name. After that it prints 'Error: ...'. The colour is ctx.color. Without a ctx it prints only the Error line, with color=None.
  - Edge case: ctx=None prints only the Error line
  - Edge case: no help option means no hint
  - Edge case: hint picks max(help_names, key=len)
- **`UsageError.show`** (`src/click/exceptions.py:87-111`)
  - Signature: `def show(self, file: t.IO[t.Any] | None=None) -> None`
  - Behavior: Prints usage and the help hint when ctx is set, then the 'Error:' line, all to file (stderr by default).
  - Edge case: ctx may be None
- **`BadParameter`** (`src/click/exceptions.py:114-156`)
  - Signature: `class BadParameter(UsageError)  # __init__(self, message: str, ctx: Context | None=None, param: Parameter | None=None, param_hint: cabc.Sequence[str] | str | None=None)`
  - Behavior: Subclass of UsageError. __init__(message, ctx=None, param=None, param_hint=None). format_message() chooses a hint in this order: param_hint, then param.get_error_hint(ctx), otherwise none. With a hint it returns 'Invalid value for {hint}: {message}'. With no hint it returns 'Invalid value: {message}'. A list or tuple hint is joined as "'a' / 'b'" through _join_param_hints, which applies repr to each item. Click fills in ctx and param itself when the exception is raised from a callback or type.
  - Edge case: a str param_hint is used as-is
  - Edge case: a sequence param_hint is repr-joined with ' / '
- **`BadParameter.format_message`** (`src/click/exceptions.py:146-156`)
  - Signature: `def format_message(self) -> str`
  - Behavior: Builds the 'Invalid value for X: msg' text as described for BadParameter.
  - Edge case: no hint and no param gives 'Invalid value: msg'
- **`MissingParameter`** (`src/click/exceptions.py:159-229`)
  - Signature: `class MissingParameter(BadParameter)  # __init__(self, message: str | None=None, ctx: Context | None=None, param: Parameter | None=None, param_hint: cabc.Sequence[str] | str | None=None, param_type: str | None=None)`
  - Behavior: Subclass of BadParameter. __init__(message=None, ctx=None, param=None, param_hint=None, param_type=None) passes message or '' to the parent. format_message() returns '{Missing X}{ hint}.{ msg}'. param_type defaults to param.param_type_name. 'argument', 'option' and 'parameter' map to the translated 'Missing argument', 'Missing option' and 'Missing parameter'. Any other value gives 'Missing {param_type}'. If param is set, param.type.get_missing_message(param, ctx) is appended to the message after '. ', or used on its own when the message is empty. __str__ returns the message, or 'Missing parameter: {param.name}' when the message is empty.
  - Edge case: empty message is allowed
  - Edge case: param_type=None and param=None gives 'Missing None'
  - Edge case: with no hint there is no hint segment, so the text ends in '.'
- **`NoSuchOption`** (`src/click/exceptions.py:232-265`)
  - Signature: `class NoSuchOption(UsageError)  # __init__(self, option_name: str, message: str | None=None, possibilities: cabc.Iterable[str] | None=None, ctx: Context | None=None)`
  - Behavior: Subclass of UsageError. __init__(option_name, message=None, possibilities=None, ctx=None). The default message is "No such option 'name'." The possibilities argument is filtered through difflib.get_close_matches(option_name, possibilities) (default n=3, cutoff 0.6) and stored as a list. It is None if possibilities is empty or None. format_message() appends 'Did you mean X?' for one match, or '(Did you mean one of: ...?)' for several, with names sorted and repr-quoted.
  - Edge case: falsy possibilities gives possibilities=None
  - Edge case: no close match gives an empty list, and the suggestion is omitted because the list is falsy
- **`NoSuchCommand`** (`src/click/exceptions.py:268-301`)
  - Signature: `class NoSuchCommand(UsageError)  # __init__(self, command_name: str, message: str | None=None, possibilities: cabc.Iterable[str] | None=None, ctx: Context | None=None)`
  - Behavior: Same shape as NoSuchOption, with command_name. It is marked versionadded 8.4.0. The default message is "No such command 'name'." Suggestions come from difflib.get_close_matches.
  - Edge case: same as NoSuchOption
- **`BadOptionUsage`** (`src/click/exceptions.py:304-320`)
  - Signature: `class BadOptionUsage(UsageError)  # __init__(self, option_name: str, message: str, ctx: Context | None=None)`
  - Behavior: Subclass of UsageError. __init__(option_name, message, ctx=None). It stores option_name and does not change the message. Used when an option is supplied but misused, for example with the wrong number of values.
- **`BadArgumentUsage`** (`src/click/exceptions.py:323-329`)
  - Signature: `class BadArgumentUsage(UsageError)`
  - Behavior: Subclass of UsageError with no added behavior. Used for wrong argument usage, such as the wrong number of values.
- **`NoArgsIsHelpError`** (`src/click/exceptions.py:332-339`)
  - Signature: `class NoArgsIsHelpError(UsageError)  # __init__(self, ctx: Context)`
  - Behavior: Subclass of UsageError. __init__(ctx) uses ctx.get_help() as the message. show() echoes only format_message() with err=True and color=ctx.color. It has no 'Error:' prefix and no usage line. Its show() takes a file argument but passes err=True along with it.
  - Edge case: ctx is required
- **`FileError`** (`src/click/exceptions.py:342-359`)
  - Signature: `class FileError(ClickException)  # __init__(self, filename: str, hint: str | None=None)`
  - Behavior: Subclass of ClickException. __init__(filename, hint=None). The hint defaults to the translated 'unknown error' and is stored as the message. ui_filename = format_filename(filename) and filename is the raw value. format_message() returns "Could not open file {ui_filename!r}: {message}".
  - Edge case: a surrogate filename is rendered with the replacement character U+FFFD
- **`Abort`** (`src/click/exceptions.py:362-363`)
  - Signature: `class Abort(RuntimeError)`
  - Behavior: Subclass of RuntimeError with no extra behavior. It signals an abort and is not a ClickException.
- **`Exit`** (`src/click/exceptions.py:366-378`)
  - Signature: `class Exit(RuntimeError)  # __init__(self, code: int=0)`
  - Behavior: Subclass of RuntimeError with __slots__ ('exit_code',). __init__(code=0) sets exit_code and does not call super().__init__. It is not a ClickException and is not exported in __init__.py.
  - Edge case: it never calls Exception.__init__, so args is empty

### Error conventions
ClickException subclasses are shown as 'Error: <message>'. UsageError and its subclasses have exit_code 2 and print usage plus a help hint first. Plain ClickException and FileError have exit_code 1. BadParameter messages read 'Invalid value for X: ...'. Missing parameters read 'Missing option/argument/parameter X.'. Unknown names read \"No such option/command 'x'.\" plus an optional 'Did you mean ...?'. All user-facing strings go through gettext (_ and ngettext). Names are shown with repr (!r). Abort and Exit are RuntimeErrors for control flow and are not shown as messages.

### Examples
FileError formats a surrogate filename without crashing (`tests/test_exceptions/test_FileError.py:4-6`)
```
message = click.FileError(filename="\udcff").format_message()
assert message == "Could not open file '�': unknown error"
```

### Tests
- `tests/test_exceptions/test_FileError.py`: A single plain pytest function that constructs click.FileError with a surrogate filename and compares format_message() to the exact string using a bare assert. No other class in this module has a test file in tests/test_exceptions/. I did not search other test files for coverage of these classes.

### Extension points
- **ClickException.format_message** (`src/click/exceptions.py:51`): Subclasses override it to customize the message. show() calls it.
- **ClickException.exit_code** (`src/click/exceptions.py:39`): A custom subclass sets its own class-level exit code.
- **ClickException.show** (`src/click/exceptions.py:57`): Override to change output format or destination, for example JSON errors.
- **UsageError.show** (`src/click/exceptions.py:87`): Customize the usage and hint rendering.
- **_format_possibilities** (`src/click/exceptions.py:26`): A shared helper for suggestion formatting, used by NoSuchOption and NoSuchCommand.
- **BadParameter.format_message** (`src/click/exceptions.py:146`): A custom message template for invalid values.

### Gaps (model's judgment, not verifiable from code)
- Exit and Abort are not ClickExceptions, and Exit is not re-exported publicly. Why plausible: A public Exit export would match Context.exit usage. Nearest: `Exit`
- No configurable cutoff or count for difflib suggestions. Both NoSuchOption and NoSuchCommand duplicate the same matching code. Why plausible: A shared helper with n and cutoff arguments is a small refactor. Nearest: `NoSuchOption.__init__`
- The FileError hint carries no errno or original OSError. FileError has no cause or structured data. Why plausible: Accepting an OSError would give richer messages. Nearest: `FileError`
- No machine-readable (dict or JSON) representation of errors. Why plausible: Programmatic CLIs benefit from structured errors. Nearest: `ClickException.show`
- MissingParameter cannot report several missing parameters at once. Why plausible: Users often fix all missing parameters in one pass. Nearest: `MissingParameter`

## Upstream (pinned 8.5.1 (CHANGES.md says released 2026-11-09; GitHub releases page shows 06 Nov), latest 8.5.1 released; 8.6.0 unreleased on main)

### Changes after the pinned commit
- [Drop Python 3.10 support (#3920)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): 8.6.0 (unreleased) drops Python 3.10.
- [Deprecate bad parameter names (#3866)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): Names that aren't valid identifiers or are keywords are deprecated (TypeError in 9.0). Non-lowercase identifier-style option names are also deprecated.
- [Add Parameter.spec, deprecate human_readable_name (#3877)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): New Parameter.spec property shows how users type the parameter. get_help_spec moves from Option to Parameter, and Argument overrides it to return its metavar. Errors and warnings show the spec. human_readable_name is deprecated and its return value changes.
- [CliRunner echoes ^D and ^Z (#3878)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): With echo_stdin=True, CliRunner echoes \x04 and \x1a as ^D and ^Z and no longer passes them to the command.
- [CliRunner.invoke accepts context_settings (#3896)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): New context_settings argument on CliRunner.invoke.
- [Help pages no longer break within hyphenated or long words (#3902)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): Help text wrapping change.
- [Docs and CI changes (#3917, #3918, #3897, #3898, #3909)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): catch_exceptions testing docs, file-object parameter docs, Nuitka standalone guide, Click UI scope/direction doc, and Python 3.15 added to the test matrix.

### Open or planned
- [#2784 Allow adding dynamic parameters to every Context](https://github.com/pallets/click/pull/2784): Open PR.
- [#2880 PromptBuilder for click.prompt/confirm format customization](https://github.com/pallets/click/pull/2880): Open PR.
- [#2864 Improve internationalization](https://github.com/pallets/click/pull/2864): Open PR.
- [#3880 Split PAGER and EDITOR with a Windows-specific shlex equivalent](https://github.com/pallets/click/pull/3880): Open PR.
- [#3827 Require parameter name to be a non-keyword identifier](https://github.com/pallets/click/pull/3827): Open PR. Overlaps with the merged deprecation in #3866.
- [#3859 and #3412 Add pyrefly type checking](https://github.com/pallets/click/pull/3859): Two overlapping open PRs. Tooling only.
- [#3051 Reference tables for kwargs (WIP)](https://github.com/pallets/click/pull/3051): Open docs PR.
- [#3921 Python 3.11 cleanups](https://github.com/pallets/click/pull/3921): Open PR. Cleanup only.

### Do not propose
- PowerShell shell completion (8.5.0)
- Argument help parameter and Positional arguments help section (8.5.0, 8.5.1)
- Parameter-level help argument (8.5.1)
- custom_version_option (8.5.0); version_option feature set is frozen
- Option.get_help_spec / Parameter.spec / get_help_spec on Parameter (8.5.1, 8.6.0)
- CliRunner context_settings, CliRunner capture='fd', and ^D/^Z echo (8.4.0, 8.6.0)
- get_pager_file, streaming echo_via_pager, PAGER params forwarding
- NoSuchCommand suggestions (8.4.0)
- Deprecation of invalid, keyword or non-lowercase parameter names
- Reserved _click_default_help name and parameter name collision warnings
- Dynamic parameters on every Context (PR #2784)
- PromptBuilder prompt/confirm formatting customization (PR #2880)
- Windows-aware PAGER/EDITOR splitting (PR #3880)
- Colorama removal and default Windows ANSI
- Hyphen-safe help wrapping and abbreviation-aware short help
- Python 3.10 drop and Python 3.15 test matrix

### Upstream limitations
- Merged-PR and open-PR lists came from summarized GitHub list pages, so they may be incomplete. Item URLs for merged PRs point to the list page, not individual PRs.
- Open issues were not enumerated: the label-filtered query returned 0 results. The unfiltered issue list was not read.
- The raw CHANGES.rst URL returned 404; CHANGES.md was used instead. The summarized main-branch changelog may be paraphrased.
- The release date differs between the repo CHANGES.md (2026-11-09) and the releases page (06 Nov). The releases page's 06 Nov matches the 'Release 8.5.1' PR merge date.
- Only the 8.5.1 section and the first 80 lines of the local changelog were read.

## Verification
### Dropped claims
- (none)

### Notes
- modules without a deep dive: src/click/utils.py, src/click/testing.py, src/click/_compat.py, src/click/globals.py
- src/click/types.py: gap 'BOOL true/false strings are not user-configurable' names a nearest interface `BoolParamType.bool_states` that is not in this file

## Open questions
- I did not read src/click/decorators.py, types.py, parser.py, termui.py, testing.py, shell_completion.py, _compat.py or the docs. Their roles are inferred from the exports in __init__.py, from grep, and from file names.
- The mapping of test files to source files is partly inferred from file names (for example test_termui to termui). I did not open most test files.
- I did not read the CI workflow (.github/workflows/tests.yaml) or .pre-commit-config.yaml.
- I did not check whether any runtime dependency is declared, such as colorama on Windows. pyproject.toml's [project] table shows no dependencies key.
- Whether `ctx.exit()` and `Exit` are exported publicly was not checked. __init__.py does not re-export Exit.

## Limitations
- The map is based on the clone at commit cf19179e8e2fd54c601378cec9e0d21bb12b6fb1, described as ref 8.5.1. I did not verify that the commit matches the 8.5.1 tag, because git describe was blocked.
- No code or tests were run, so every command's verified flag is false.
- Only pyproject.toml, __init__.py, parts of core.py, CHANGES.md, conftest.py and test_deprecations.py were read in full or in part. Everything else is based on file listings and grep.
- `src/click/core.py`: I did not read the Context body (lines 213-520) or the Option help and prompt methods in full, nor Command.__init__ and Group.__init__.
- `src/click/core.py`: I read only the test names in tests/test_context.py. The other listed test files were not opened.
- `src/click/core.py`: The result_callback replace semantics are inferred from the signature.
- `src/click/core.py`: Examples come from the source (docstring and implementation) rather than docs or test files.
- `src/click/decorators.py`: Params are stored on the function as __click_params__, and the order depends on command() reversing that list.
- `src/click/decorators.py`: The command() decorator pops params from the shared attrs dict, so the decorator is not safely reusable.
- `src/click/decorators.py`: version_option's package detection uses frame inspection, which is brittle in wrappers, and the version is only resolved when the option is invoked.
- `src/click/decorators.py`: pass_context and pass_obj do not preserve the typed Context subclass beyond annotations.
- `src/click/decorators.py`: argument() and option() accept **attrs untyped, so all validation happens in the Option/Argument constructors.
- `src/click/decorators.py`: I did not read the typing tests or test_options.py contents in detail.
- `src/click/types.py`: Choice rebuilds its normalized mapping on every convert and does not validate uniqueness of normalized values.
- `src/click/types.py`: FuncParamType, UUID and DateTime catch only ValueError; other exceptions propagate (e.g. DateTime TypeError on non-str).
- `src/click/types.py`: BoolParamType.convert raises AttributeError for non-str, non-bool input.
- `src/click/types.py`: Tuple.convert relies on len(value); no nargs validation here.
- `src/click/types.py`: Path executable check uses the unresolved value while other checks use the resolved path.
- `src/click/types.py`: File's to_info_dict does not include lazy/atomic/errors.
- `src/click/types.py`: Tests directly covering this module are sparse for Choice (one test); other types are covered in sibling test files in tests/test_types/.
- `src/click/parser.py`: The module is private and deprecated; the docstring says it will be removed in Click 9.0, and the shim message points users to the stdlib optparse.
- `src/click/parser.py`: There is no type conversion or defaulting; everything is raw strings, UNSET or FLAG_NEEDS_VALUE.
- `src/click/parser.py`: Flags are copied from ctx once, in __init__.
- `src/click/parser.py`: Actions are plain strings dispatched through an if/elif chain.
- `src/click/parser.py`: No abbreviation matching of long options.
- `src/click/parser.py`: In resilient_parsing mode, UsageError is swallowed and partial results are returned.
- `src/click/parser.py`: I did not read tests/test_options.py, tests/test_arguments.py or tests/test_basic.py, which exercise the parser indirectly.
- `src/click/termui.py`: I did not read _termui_impl.py, so the behavior of ProgressBar, Editor, open_url and the pager is inferred from termui.py and from test names. I did not read the docs either.
- `src/click/termui.py`: I only grepped the test files for names and read short parts of them.
- `src/click/termui.py`: prompt with default=None loops forever on empty input.
- `src/click/termui.py`: pause and clear do nothing if not attached to a tty.
- `src/click/termui.py`: getchar always reads from the terminal even if stdin is piped.
- `src/click/termui.py`: Styling is plain ANSI. echo strips it for non-tty output, and unstyle strips it explicitly.
- `src/click/termui.py`: Colors are not validated against terminal capability.
- `src/click/shell_completion.py`: Completion runs make_context with resilient_parsing=True, so side effects in callbacks are skipped, but any custom shell_complete code still runs on every Tab press.
- `src/click/shell_completion.py`: Bash support is documented as requiring bash >= 4.4. The check only prints a warning when the script is sourced.
- `src/click/shell_completion.py`: The Zsh script is frozen for backward compatibility, which limits changes to its wire format.
- `src/click/shell_completion.py`: The wire formats are not escaped for commas or newlines in values. Bash and Fish split on ',', and the Zsh and PowerShell formats rely on newlines.
- `src/click/shell_completion.py`: `_check_version` compares the version strings lexicographically (`major < '4'`), which is wrong for 2-digit major versions such as 10.
- `src/click/shell_completion.py`: ShellComplete.source with `%` formatting breaks on a stray `%` in a template.
- `src/click/formatting.py`: The formatter always buffers in memory.
- `src/click/formatting.py`: Width is only handled for ANSI escapes via term_len. Wide CJK or emoji characters are not accounted for, as far as this module shows.
- `src/click/formatting.py`: dedent has no underflow protection.
- `src/click/formatting.py`: The '\b' no-rewrap marker only works with preserve_paragraphs=True, and only when it is the first line of a paragraph.
- `src/click/formatting.py`: wrap_text expands tabs to 8-column stops.
- `src/click/formatting.py`: Help text is not translated here beyond the 'Usage:' string.
- `src/click/formatting.py`: I did not read click/_textwrap.py or click._compat.term_len, so the wrapping details come from the tests and docstrings.
- `src/click/exceptions.py`: Exit.__init__ does not call super().__init__, so args is empty.
- `src/click/exceptions.py`: ClickException.show_color is captured at construction time, so later changes to the colour setting are not seen.
- `src/click/exceptions.py`: Most classes (UsageError, BadParameter, MissingParameter, NoSuchOption, NoSuchCommand, and the others) have no dedicated test file under tests/test_exceptions/.
- `src/click/exceptions.py`: Several attributes are annotated t.Final, which is a typing-only constraint.
- `src/click/exceptions.py`: NoArgsIsHelpError.show passes err=True while also accepting a file argument.
- `src/click/exceptions.py`: I did not read core.py, the docs, or other test files, so how these classes are raised and caught is not covered here.
