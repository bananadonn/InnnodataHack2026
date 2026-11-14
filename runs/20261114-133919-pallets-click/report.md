# Repository report: pallets/click

- URL: https://github.com/pallets/click.git
- Requested ref: 8.5.1
- Commit: `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`
- Run: `20261114-133919-pallets-click` · model `claude-sonnet-5-5`
- Verification: 180 of 180 claimed interfaces confirmed in the source; 0 claims dropped

## Purpose
Click is a Python library for building command-line interfaces. You compose commands, groups, options and arguments with decorators. It generates help, parses and converts arguments, prompts the user, shows progress bars, and provides shell completion and a test runner.

## Intended users
Python developers who write CLI tools. Libraries such as Flask build on it. Pallets maintainers and contributors are the other group.

## Languages, frameworks, dependencies
- Languages: Python (>=3.10)
- Frameworks: flit_core (build backend), pytest, tox with tox-uv, mypy and pyright, ruff, pre-commit, Sphinx with myst-parser (docs)
- Dependencies: Runtime: none declared in pyproject.toml. No [project].dependencies key was seen, so it relies on the standard library; Windows console support is in _winconsole.py, Dependency groups: dev (ruff, tox, tox-uv); tests (pytest); tests-random (pytest, pytest-randomly, pytest-xdist); typing (mypy, pyright, pytest); docs (sphinx and plugins); pre-commit; gha-update

## Entry points
- `src/click/__init__.py:10`: Public API re-exports (Command, Group, Option, Argument, Context, decorators, exceptions, termui, types, utils). A module-level __getattr__ at line 76 serves the deprecated names.
- `src/click/core.py:1483`: Command.main(): the CLI entry point. It handles shell completion, makes the Context, invokes the command, and maps exceptions to exit codes.
- `src/click/testing.py:317`: CliRunner, the test harness that invokes commands in isolation.
- `src/click/decorators.py:1`: The @command, @group, @option and @argument decorators that most users call first. Line 1 is the top of the module; I did not read the file.

## Key modules (most feature-relevant first)
- `src/click/core.py`: Context, Command, Group, CommandCollection, Parameter, Option, Argument and ParameterSource. It holds the parse, convert, default and invoke logic. It is about 3800 lines long. *Feature relevance:* Most features on commands, options or arguments, such as a new Option or Parameter keyword, help rendering or context behaviour, are added here.
- `src/click/decorators.py`: Decorators for commands, groups, options, arguments and the built-in version, help, password and confirmation options. *Feature relevance:* A new parameter or option keyword usually needs a matching decorator signature here.
- `src/click/types.py`: ParamType and its subclasses (Choice, IntRange, FloatRange, File, Path, DateTime, Tuple, and others), plus the BOOL, INT and STRING singletons. *Feature relevance:* New parameter types or type conversion rules go here.
- `src/click/parser.py`: The internal option and argument parser. The old OptionParser name is deprecated. *Feature relevance:* Changes to how tokens are parsed, such as option prefixes or nargs, are made here.
- `src/click/shell_completion.py`: Shell completion, with bash, zsh, fish and (per CHANGES.md 8.5.0) PowerShell. *Feature relevance:* A new shell or completion behaviour goes here.
- `src/click/termui.py`: Interactive helpers: prompt, confirm, style, secho, progressbar, edit, launch, pause, getchar and echo_via_pager. *Feature relevance:* New terminal UI helpers go here. The implementations live in _termui_impl.py.
- `src/click/exceptions.py`: ClickException and its subclasses: UsageError, BadParameter, MissingParameter, Abort, Exit and others. *Feature relevance:* New error types and error formatting.
- `src/click/formatting.py`: HelpFormatter and text wrapping. *Feature relevance:* Help output layout changes.
- `src/click/utils.py`: echo, open_file, LazyFile, KeepOpenFile, get_app_dir, format_filename and the program-name and argument-expansion helpers. *Feature relevance:* General utilities. The module also hosts deprecated names through __getattr__ at about line 669.
- `src/click/testing.py`: CliRunner, Result, and stream capture classes such as StreamMixer and _FDCapture. *Feature relevance:* Test-runner features such as input, output and isolation.
- `src/click/_compat.py`: Internal compatibility layer for streams and platforms. I did not read it. *Feature relevance:* Stream and platform handling that features may touch.
- `src/click/globals.py`: Context stack and get_current_context. I did not read it. *Feature relevance:* Access to the current context.

## Execution flow
The user calls the command object, or Command.main(), which is core.py:1483. main() takes args from sys.argv[1:], expanding them on Windows, and detects the program name. self._main_shell_completion handles any completion request and exits early. Then make_context builds a Context and calls Command.parse_args, which uses the parser and each Parameter's handle_parse_result. That step resolves the value from the command line, an environment variable, a default map or the default, then runs process_value to convert and validate it. Command.invoke runs the callback. A Group.invoke resolves the subcommand through resolve_command, makes a sub-context and invokes it. In standalone mode, main() catches Exit, Abort, KeyboardInterrupt, EOFError, ClickException and EPIPE OSError. It prints the message and calls sys.exit. With standalone_mode=False it returns the value or propagates the exception.

## Tests (runner: pytest. Config is in pyproject.toml: testpaths=tests, filterwarnings=error, and stress tests excluded by default via addopts.)
- `tests/test_basic.py` covers `src/click/core.py`, `src/click/decorators.py`
- `tests/test_options.py` covers `src/click/core.py`
- `tests/test_arguments.py` covers `src/click/core.py`
- `tests/test_commands.py` covers `src/click/core.py`
- `tests/test_context.py` covers `src/click/core.py`
- `tests/test_chain.py` covers `src/click/core.py`
- `tests/test_defaults.py` covers `src/click/core.py`
- `tests/test_command_decorators.py` covers `src/click/decorators.py`
- `tests/test_parser.py` covers `src/click/parser.py`
- `tests/test_shell_completion.py` covers `src/click/shell_completion.py`
- `tests/test_termui.py` covers `src/click/termui.py`, `src/click/_termui_impl.py`
- `tests/test_testing.py` covers `src/click/testing.py`
- `tests/test_formatting.py` covers `src/click/formatting.py`
- `tests/test_compat.py` covers `src/click/_compat.py`
- `tests/test_deprecations.py` covers `src/click/__init__.py`, `src/click/core.py`
- `tests/test_imports.py` covers `src/click/__init__.py`
- `tests/test_info_dict.py` covers `src/click/core.py`, `src/click/types.py`
- `tests/test_exceptions/test_FileError.py` covers `src/click/exceptions.py`
- `tests/test_types/test_Choice.py` covers `src/click/types.py`
- `tests/test_types/test_convert_type.py` covers `src/click/types.py`
- `tests/test_utils/test_echo.py` covers `src/click/utils.py`
- `tests/test_utils/test_prompt.py` covers `src/click/termui.py`
- `tests/test_utils/test_LazyFile.py` covers `src/click/utils.py`
- `tests/typing/typing_aliased_group.py` covers `src/click/decorators.py`, `src/click/core.py`

### Test conventions
- Files are named test_<topic>.py. Larger areas become packages: tests/test_types, tests/test_utils and tests/test_exceptions, with one file per class or function, e.g. test_Choice.py.
- The shared fixture `runner` in tests/conftest.py returns CliRunner() with function scope.
- Warnings are turned into errors (filterwarnings=error), so tests that expect a warning must catch it explicitly.
- Stress tests carry @pytest.mark.stress and are run only via `tox -e stress`.
- Static typing checks run on tests/typing/typing_*.py with mypy and pyright, not pytest.
- I did not read individual tests, so assertion style is not documented here.

## Compatibility rules
- The public API is whatever src/click/__init__.py re-exports with `as` aliases. Internals use underscore prefixes (_compat, _termui_impl, _utils, _winconsole). (`src/click/__init__.py:10-73`)
- Deprecations keep the old name alive through a module-level __getattr__. It emits DeprecationWarning with stacklevel=2 and a message naming the removal version (Click 9.0, or 9.1 for __version__). (`src/click/__init__.py:76-144`)
- The Python floor is 3.10, and the type checkers target 3.10. (`pyproject.toml:16-16`)
- Warnings fail the tests, and stress tests are excluded by default. (`pyproject.toml:83-91`)
- Typing is strict. The package ships py.typed (src/click/py.typed). mypy runs in strict mode on src and tests/typing, and pyright runs --verifytypes. (`pyproject.toml:107-116`)
- The ruff config requires `typing` imported as `t` and single-line imports. (`pyproject.toml:126-143`)
- Docstrings carry versionchanged and versionadded notes. CHANGES.md uses a per-version bullet list with {pr} and {issue} references. (`src/click/core.py:1523-1532`)
- Contributor rules: avoid ternary expressions because coverage cannot measure both branches. Avoid unnecessary dependencies, preferring the standard library. Wrap Markdown at 80 columns. (`docs/contributing.md:33-46`)
- The command-level `deprecated` parameter accepts a bool or a str. (`src/click/core.py:983-991`)

## Setup and test commands
- `uv sync`: Install the default groups (dev, pre-commit, tests, typing). This is inferred from tool.uv default-groups, and no command is written in the file. (source: pyproject.toml; discovered, not executed)
- `pytest`: Run the test suite (source: pyproject.toml; discovered, not executed)
- `tox`: Run the environments listed in env_list: Python 3.10–3.14, 3.14t, pypy3.11, stress, style, typing and docs (source: pyproject.toml; discovered, not executed)
- `tox r -e stress`: Run the stress tests (source: docs/contributing.md; discovered, not executed)
- `tox r -e random`: Run the tests in parallel in random order (source: docs/contributing.md; discovered, not executed)
- `tox r -e typing`: Run mypy and pyright --verifytypes (source: pyproject.toml; discovered, not executed)
- `tox r -e style`: Run all pre-commit hooks on all files (source: pyproject.toml; discovered, not executed)
- `tox r -e docs`: Build the docs with sphinx-build -W (source: pyproject.toml; discovered, not executed)

## Evidence
- The project version is 8.5.1, Python >=3.10, and it builds with flit_core. (`pyproject.toml:1-16`)
- CHANGES.md has a 8.5.1 section dated 2026-11-09. (`CHANGES.md:1-33`)
- main() runs shell completion, then make_context, invoke and exception mapping. (`src/click/core.py:1534-1612`)
- core.py defines Context, Command, Group, CommandCollection, Parameter, Option and Argument. (`src/click/core.py:213-3698`)
- The test fixture `runner` is CliRunner(). (`tests/conftest.py:6-8`)
- CliRunner and Result are defined in testing.py. (`src/click/testing.py:231-317`)

## Module card: `src/click/core.py`
src/click/core.py holds click's runtime. Context carries per-invocation state and is inherited from the parent context. Command parses args into a context and invokes its callback. Group dispatches to subcommands, with an optional chain mode and a result callback. CommandCollection flattens commands from other groups. Parameter, Option and Argument turn user input into values. Parameter.consume_value picks the value in the order command line, env var, default_map, default. Parameter.process_value then runs type cast, required check and callback. Option adds flags, prompts, counts and auto env vars. ParameterSource is an IntEnum recording where each value came from. A private sentinel, UNSET, marks "no value" internally and is turned into None before user code sees it. Several parameters can share one name (feature switches), and handle_parse_result decides which one wins using ParameterSource.

### Interfaces
- **`ParameterSource`** (`src/click/core.py:174-210`)
  - Signature: `class ParameterSource(enum.IntEnum)`
  - Behavior: IntEnum with members PROMPT, COMMANDLINE, ENVIRONMENT, DEFAULT_MAP, DEFAULT, auto-numbered from most to least explicit. Comparisons such as `source < ParameterSource.DEFAULT_MAP` mean 'explicitly provided'. Parameter.handle_parse_result uses that comparison for deprecation warnings and for feature-switch arbitration.
  - Edge case: Context.get_parameter_source returns None for a name that never had a source set
- **`Context.__init__`** (`src/click/core.py:345-518`)
  - Signature: `def __init__(self, command: Command, parent: Context | None=None, info_name: str | None=None, obj: t.Any | None=None, auto_envvar_prefix: str | None=None, default_map: cabc.MutableMapping[str, t.Any] | None=None, terminal_width: int | None=None, max_content_width: int | None=None, resilient_parsing: bool=False, allow_extra_args: bool | None=None, allow_interspersed_args: bool | None=None, ignore_unknown_options: bool | None=None, help_option_names: list[str] | None=None, token_normalize_func: t.Callable[[str], str] | None=None, color: bool | None=None, show_default: bool | None=None) -> None`
  - Behavior: Builds a context. Most settings (obj, default_map, terminal_width, max_content_width, help_option_names, token_normalize_func, color, show_default) are inherited from the parent when None. allow_extra_args, allow_interspersed_args and ignore_unknown_options fall back to the command's attributes. default_map for a child is parent.default_map.get(info_name) when not given. auto_envvar_prefix is uppercased, and when absent it becomes '<PARENT_PREFIX>_<INFO_NAME upper>'; '-' is replaced by '_'. help_option_names defaults to ['--help']. obj and meta are shared with the parent.
  - Edge case: The parent's _opt_prefixes set is copied
  - Edge case: an explicit auto_envvar_prefix is uppercased
  - Edge case: info_name None means no prefix is derived from the parent
- **`Context.scope`** (`src/click/core.py:573-608`)
  - Signature: `def scope(self, cleanup: bool=True) -> cabc.Generator[Context]`
  - Behavior: Context manager that pushes the context onto the thread-local stack. With cleanup=False the depth is bumped so closing callbacks do not run on exit. Context.__enter__ and __exit__ track nesting depth, and only at depth 0 do they run the ExitStack.
  - Edge case: Nested entries defer cleanup until the outermost exit
  - Edge case: the exit stack is replaced with a new one after closing, so the context can be reused
- **`Context.with_resource`** (`src/click/core.py:652-679`)
  - Signature: `def with_resource(self, context_manager: AbstractContextManager[V]) -> V`
  - Behavior: Enters a context manager on the context's ExitStack and returns its __enter__ result. It is cleaned up when the context closes.
- **`Context.call_on_close`** (`src/click/core.py:681-691`)
  - Signature: `def call_on_close(self, f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]`
  - Behavior: Registers a callback on the ExitStack, run at teardown in LIFO order. Returns the callback, so it works as a decorator.
- **`Context.lookup_default`** (`src/click/core.py:789-809`)
  - Signature: `def lookup_default(self, name: str, call: bool=True) -> t.Any | None`
  - Behavior: Reads default_map[name]. Returns None when the map is None, the key is missing, or the stored value is the UNSET sentinel. A callable value is called unless call=False.
  - Edge case: a key present with value None counts as 'present' in _default_map_has, so it blocks the parameter's own default
- **`Context.invoke`** (`src/click/core.py:861-911`)
  - Signature: `def invoke(self, callback: Command | t.Callable[..., V], /, *args: t.Any, **kwargs: t.Any) -> t.Any | V`
  - Behavior: Given a plain callable, runs it with the given args inside `with augment_usage_errors(self), ctx`. Given a Command, it creates a sub-context and, for each exposed param not in kwargs, fills in param.get_default(ctx) cast by type_cast_value (UNSET becomes None). It then stores kwargs in ctx.params and calls the command's callback directly. The command's own parse step and callback chain are skipped.
  - Edge case: a Command with callback None raises TypeError
  - Edge case: UNSET defaults become None
  - Raises: `TypeError`
- **`Context.forward`** (`src/click/core.py:913-930`)
  - Signature: `def forward(self, cmd: Command, /, *args: t.Any, **kwargs: t.Any) -> t.Any`
  - Behavior: Like invoke, but kwargs missing from the call are filled from the current ctx.params. Only accepts Command objects.
  - Edge case: a non-Command argument raises TypeError
  - Raises: `TypeError`
- **`Context.get_parameter_source`** (`src/click/core.py:941-957`)
  - Signature: `def get_parameter_source(self, name: str) -> ParameterSource | None`
  - Behavior: Returns the ParameterSource recorded for the parameter name, or None. Context.set_parameter_source stores it.
  - Edge case: unknown name returns None
- **`Context.fail`** (`src/click/core.py:811-817`)
  - Signature: `def fail(self, message: str) -> t.NoReturn`
  - Behavior: Raises UsageError(message, ctx). Context.abort raises Abort. Context.exit(code=0) first closes the context (running close callbacks), then raises Exit(code).
  - Raises: `UsageError`, `Abort`
  - Raises (unconfirmed, likely via a helper): `Exit`
- **`Context.find_object`** (`src/click/core.py:744-754`)
  - Signature: `def find_object(self, object_type: type[V]) -> V | None`
  - Behavior: Walks up the parent chain and returns the first ctx.obj that is an instance of the type, else None. Context.ensure_object does the same, but when none is found it sets self.obj to object_type() and returns that.
  - Edge case: ensure_object assigns on the innermost context only
- **`Command.__init__`** (`src/click/core.py:1036-1078`)
  - Signature: `def __init__(self, name: str | None, context_settings: cabc.MutableMapping[str, t.Any] | None=None, callback: t.Callable[..., t.Any] | None=None, params: list[Parameter] | None=None, help: str | None=None, epilog: str | None=None, short_help: str | None=None, options_metavar: str | None='[OPTIONS]', add_help_option: bool=True, no_args_is_help: bool=False, hidden: bool=False, deprecated: bool | str=False) -> None`
  - Behavior: Stores name, context_settings (default {}), callback, params (default []), help, epilog, short_help, options_metavar ('[OPTIONS]'), add_help_option, no_args_is_help, hidden and deprecated. Class attributes control context creation: context_class, allow_extra_args=False, allow_interspersed_args=True, ignore_unknown_options=False.
  - Edge case: name may be None
  - Edge case: params is copied only when falsy, otherwise the same list is stored
- **`Command.get_params`** (`src/click/core.py:1103-1157`)
  - Signature: `def get_params(self, ctx: Context) -> list[Parameter]`
  - Behavior: Returns self.params plus the cached help option when enabled. Under __debug__ it warns (UserWarning) on duplicate option strings. It also warns when a name collides with the reserved help storage name, or when an Argument shares a name with another parameter.
  - Edge case: help option names already used by other params are dropped
  - Edge case: help option is stored under the reserved name _click_default_help
- **`Command.make_context`** (`src/click/core.py:1330-1365`)
  - Signature: `def make_context(self, info_name: str | None, args: list[str], parent: Context | None=None, **extra: t.Any) -> Context`
  - Behavior: Merges context_settings into **extra (explicit extra wins). It builds ctx = self.context_class(self, info_name=..., parent=..., **extra). It then calls parse_args(ctx, args) inside ctx.scope(cleanup=False) and returns the context. It does not invoke the callback.
- **`Command.parse_args`** (`src/click/core.py:1367-1398`)
  - Signature: `def parse_args(self, ctx: Context, args: list[str]) -> list[str]`
  - Behavior: Raises NoArgsIsHelpError if there are no args, no_args_is_help is set and parsing is not resilient. It builds the parser with make_parser, parses, then runs handle_parse_result for each param in the order given by iter_params_for_processing (eager first, then the order given on the command line, then declaration order). Remaining UNSET values in ctx.params become None. Extra args raise through ctx.fail unless allow_extra_args or resilient_parsing is set. It then sets ctx.args and merges the option prefixes.
  - Edge case: resilient_parsing suppresses the errors
  - Raises: `NoArgsIsHelpError`
  - Raises (unconfirmed, likely via a helper): `UsageError`
- **`Command.invoke`** (`src/click/core.py:1400-1414`)
  - Signature: `def invoke(self, ctx: Context) -> t.Any`
  - Behavior: If deprecated, echoes a red 'DeprecationWarning: The command ... is deprecated.' to stderr. If a callback exists, it returns ctx.invoke(self.callback, **ctx.params). With no callback it returns None.
  - Edge case: a missing callback returns None silently
- **`Command.main`** (`src/click/core.py:1483-1617`)
  - Signature: `def main(self, args: cabc.Sequence[str] | None=None, prog_name: str | None=None, complete_var: str | None=None, standalone_mode: bool=True, windows_expand_args: bool=True, **extra: t.Any) -> t.Any`
  - Behavior: Entry point. It reads sys.argv[1:] when args is None (with Windows glob expansion), detects the program name, and handles shell completion through the _<PROG>_COMPLETE env var (exits early). Then it runs make_context and invoke. In standalone mode it calls sys.exit: Exit gives the code, Abort and KeyboardInterrupt/EOFError print 'Aborted!' with exit code 1, ClickException is shown with its exit_code, and EPIPE is silenced. With standalone_mode=False the return value is returned, Exit returns its exit_code, ClickException and Abort propagate, and Ctrl-C/EOF are re-raised as Abort. Command.__call__ is an alias.
  - Edge case: a non-EPIPE OSError is re-raised
  - Edge case: **extra goes to the Context constructor
  - Raises: `Abort`, `ClickException`
- **`Command.shell_complete`** (`src/click/core.py:1416-1461`)
  - Signature: `def shell_complete(self, ctx: Context, incomplete: str) -> list[CompletionItem]`
  - Behavior: Completes option names when the incomplete token starts with a non-alphanumeric character. It skips hidden options and non-multiple options already given on the command line. It also adds sibling subcommands of any ancestor group that is in chain mode.
- **`Group.__init__`** (`src/click/core.py:1730-1783`)
  - Signature: `def __init__(self, name: str | None=None, commands: cabc.MutableMapping[str, Command] | cabc.Sequence[Command] | None=None, invoke_without_command: bool=False, no_args_is_help: bool | None=None, subcommand_metavar: str | None=None, chain: bool=False, result_callback: t.Callable[..., t.Any] | None=None, **kwargs: t.Any) -> None`
  - Behavior: Accepts commands as a mapping or a sequence of Commands (a sequence is keyed by c.name, skipping None names). no_args_is_help defaults to `not invoke_without_command`. subcommand_metavar is derived from chain and invoke_without_command. result_callback is stored as _result_callback. It sets allow_extra_args=True and allow_interspersed_args=False at class level, and class-level command_class and group_class attributes.
  - Edge case: a chained group with an optional Argument raises RuntimeError
  - Raises: `RuntimeError`
- **`Group.add_command`** (`src/click/core.py:1803-1811`)
  - Signature: `def add_command(self, cmd: Command, name: str | None=None) -> None`
  - Behavior: Registers cmd under name or cmd.name. In chain mode, adding a Group is rejected through _check_nested_chain.
  - Edge case: no name raises TypeError
  - Edge case: replaces an existing entry silently
  - Raises: `TypeError`
  - Raises (unconfirmed, likely via a helper): `RuntimeError`
- **`Group.command`** (`src/click/core.py:1821-1860`)
  - Signature: `def command(self, *args: t.Any, **kwargs: t.Any) -> t.Callable[[t.Callable[..., t.Any]], Command] | Command`
  - Behavior: Decorator that builds a command with click.command and registers it on this group. It works with or without parentheses. It uses command_class as cls when no cls kwarg is given.
  - Edge case: a bare callable plus kwargs trips an assert
  - Raises (unconfirmed, likely via a helper): `AssertionError`
- **`Group.group`** (`src/click/core.py:1870-1912`)
  - Signature: `def group(self, *args: t.Any, **kwargs: t.Any) -> t.Callable[[t.Callable[..., t.Any]], Group] | Group`
  - Behavior: Same as Group.command but for subgroups. group_class is used as cls, and group_class = type means 'use type(self)'.
  - Raises (unconfirmed, likely via a helper): `AssertionError`
- **`Group.result_callback`** (`src/click/core.py:1914-1957`)
  - Signature: `def result_callback(self, replace: bool=False) -> t.Callable[[F], F]`
  - Behavior: Decorator that sets the result callback, called as f(result, **group_params). If one already exists, the new one is chained after the old one (old is called first, its result goes to the new one). replace=True overwrites the old one. The callback receives a single return value, or a list of return values in chain mode.
  - Edge case: a group with invoke_without_command and no subcommand passes the group's return value, or [] in chain mode
- **`Group.invoke`** (`src/click/core.py:2020-2086`)
  - Signature: `def invoke(self, ctx: Context) -> t.Any`
  - Behavior: With no subcommand: if invoke_without_command is set it runs the group callback and then the result callback, otherwise it fails with 'Missing command.'. In normal mode it resolves the command, sets ctx.invoked_subcommand, runs the group callback, builds the subcontext and invokes it. In chain mode it sets invoked_subcommand to '*' (or None when there are no args), runs the group callback, then builds all subcontexts first (allow_extra_args=True, allow_interspersed_args=False) and invokes them in order, collecting the results in a list. Both modes feed the result callback.
  - Edge case: the group callback runs before the subcommand is parsed
  - Edge case: in chain mode all subcommand parsing completes before any subcommand runs
  - Raises (unconfirmed, likely via a helper): `UsageError`
- **`Group.resolve_command`** (`src/click/core.py:2088-2112`)
  - Signature: `def resolve_command(self, ctx: Context, args: list[str]) -> tuple[str | None, Command | None, list[str]]`
  - Behavior: Looks up args[0] with get_command. On a miss it retries after token_normalize_func. If the token still misses and parsing is not resilient and it looks like an option, it re-runs self.parse_args(ctx, args), so --help and errors on group options surface. Otherwise it raises NoSuchCommand with the possibilities. Returns (name, cmd, rest).
  - Edge case: with resilient_parsing it returns (None, None, rest)
  - Raises: `NoSuchCommand`
- **`Group.get_command`** (`src/click/core.py:1959-1963`)
  - Signature: `def get_command(self, ctx: Context, cmd_name: str) -> Command | None`
  - Behavior: Plain lookup in self.commands. list_commands returns sorted(self.commands). Both are the overridable hooks for dynamic or lazy command loading, and help, completion, to_info_dict and resolve_command all go through them.
  - Edge case: help skips commands for which get_command returns None
- **`CommandCollection`** (`src/click/core.py:2141-2196`)
  - Signature: `class CommandCollection(Group)  # __init__(self, name: str | None=None, sources: list[Group] | None=None, **kwargs: t.Any)`
  - Behavior: A Group subclass with a list of sources (Groups). get_command checks its own commands first, then each source in order. list_commands is the sorted union. Source parameters and callbacks are not used. add_source appends a source. In chain mode a source Group raises RuntimeError.
  - Edge case: first source wins on a name collision
  - Raises (unconfirmed, likely via a helper): `RuntimeError`
- **`Parameter.__init__`** (`src/click/core.py:2328-2407`)
  - Signature: `def __init__(self, param_decls: cabc.Sequence[str] | None=None, type: types.ParamType[t.Any] | t.Any | None=None, required: bool=False, default: t.Any | t.Callable[[], t.Any] | None=UNSET, callback: t.Callable[[Context, Parameter, t.Any], t.Any] | None=None, nargs: int | None=None, multiple: bool=False, metavar: str | None=None, expose_value: bool=True, is_eager: bool=False, envvar: str | cabc.Sequence[str] | None=None, shell_complete: t.Callable[[Context, Parameter, str], list[CompletionItem] | list[str]] | None=None, deprecated: bool | str=False, help: str | None=None) -> None`
  - Behavior: Parses the declarations with _parse_decls. It resolves the type via types.convert_type(type, default), and nargs defaults to the composite type's arity or 1. default defaults to the UNSET sentinel, and _default_explicit records whether a default was passed. If deprecated is set, a '(DEPRECATED...)' label is appended to help. The ValueError checks run only under __debug__.
  - Edge case: a composite type with a mismatched nargs raises ValueError
  - Edge case: required together with deprecated raises ValueError
  - Raises: `ValueError`
- **`Parameter.consume_value`** (`src/click/core.py:2518-2564`)
  - Signature: `def consume_value(self, ctx: Context, opts: cabc.Mapping[str, t.Any]) -> tuple[t.Any, ParameterSource]`
  - Behavior: Resolves the raw value in precedence order. First the parser value (COMMANDLINE), then the envvar via value_from_envvar (ENVIRONMENT), then ctx.lookup_default (DEFAULT_MAP; a string is split when nargs != 1), then get_default (DEFAULT). It returns (value, source) and gives UNSET if nothing is found.
  - Edge case: an empty envvar string counts as unset
  - Edge case: a default_map key present with None is used as the value
- **`Parameter.type_cast_value`** (`src/click/core.py:2566-2620`)
  - Signature: `def type_cast_value(self, ctx: Context, value: t.Any) -> t.Any`
  - Behavior: None becomes () for multiple or nargs=-1, otherwise it stays None. It converts via self.type, per item for nargs=-1, as an exact-length tuple for nargs>1, and wraps in a tuple per item for multiple.
  - Edge case: a non-iterable value raises BadParameter 'Value must be an iterable.'
  - Edge case: a nargs length mismatch raises BadParameter 'Takes N values but M were given.'
  - Raises: `BadParameter`
- **`Parameter.process_value`** (`src/click/core.py:2640-2700`)
  - Signature: `def process_value(self, ctx: Context, value: t.Any) -> t.Any`
  - Behavior: UNSET becomes () for multiple or nargs=-1, otherwise the value is type cast. A required parameter whose value is missing raises MissingParameter. The callback(ctx, param, value) then runs. It receives None for UNSET, and while it runs, other UNSET entries in ctx.params are shown as None.
  - Edge case: value_is_missing treats UNSET and () (for nargs != 1 or multiple) as missing
  - Raises: `MissingParameter`
- **`Parameter.handle_parse_result`** (`src/click/core.py:2763-2849`)
  - Signature: `def handle_parse_result(self, ctx: Context, opts: cabc.Mapping[str, t.Any], args: list[str]) -> tuple[t.Any, list[str]]`
  - Behavior: Per-parameter pipeline. It calls consume_value, records the source, echoes a red deprecation warning to stderr if the value is explicit (source < DEFAULT_MAP), then process_value. In resilient_parsing mode any exception turns the value into UNSET. It then decides which parameter owns ctx.params[name] when several share a name (feature switches): a more explicit source wins, and the same source wins by later order unless that would replace an explicit default with an inferred one. It writes ctx.params only if expose_value is true.
  - Edge case: errors are wrapped in augment_usage_errors, which attaches ctx and param to BadParameter
  - Raises (unconfirmed, likely via a helper): `BadParameter`, `MissingParameter`
- **`Option.__init__`** (`src/click/core.py:2983-3058`)
  - Signature: `def __init__(self, param_decls: cabc.Sequence[str] | None=None, show_default: bool | str | None=None, prompt: bool | str=False, confirmation_prompt: bool | str=False, prompt_required: bool=True, hide_input: bool=False, is_flag: bool | None=None, flag_value: t.Any=UNSET, multiple: bool=False, count: bool=False, allow_from_autoenv: bool=True, type: types.ParamType[t.Any] | t.Any | None=None, help: str | None=None, hidden: bool=False, show_choices: bool=True, show_envvar: bool=False, deprecated: bool | str=False, **attrs: t.Any) -> None`
  - Behavior: Steps in order: prompt text (prompt=True needs a name and becomes the name with underscores replaced by spaces, capitalised); flag inference; type picking (count gives IntRange(min=0); bool flag gives BoolParamType); count sets default=0 if default was unset; then validation. is_flag is inferred from flag_value, secondary '/' declarations, or an explicit value. Option.get_default lazily resolves UNSET to False for non-required boolean flags, () for non-required multi flags, and True to flag_value for non-boolean flags.
  - Edge case: prompt=True without a name raises TypeError
  - Edge case: deprecated with prompt raises ValueError
  - Edge case: nargs=-1 raises TypeError
  - Edge case: secondary opts on a non-bool flag raise TypeError
  - Edge case: count with multiple or is_flag raises TypeError
  - Edge case: a repeated name, an identical true/false pair, or no derivable name raise TypeError/ValueError
  - Edge case: a name given without any option strings raises TypeError
  - Raises: `TypeError`
  - Raises (unconfirmed, likely via a helper): `ValueError`
- **`Option.consume_value`** (`src/click/core.py:3627-3681`)
  - Signature: `def consume_value(self, ctx: Context, opts: cabc.Mapping[str, Parameter]) -> tuple[t.Any, ParameterSource]`
  - Behavior: Extends Parameter.consume_value. If the parser yielded FLAG_NEEDS_VALUE, it prompts when prompt is set and parsing is not resilient (source PROMPT), otherwise it uses flag_activation_value (COMMANDLINE). It also substitutes the activation value inside multiple lists. When the value is unset or comes from a default, and prompt is enabled with (required or prompt_required), it calls prompt_for_value (source PROMPT).
  - Edge case: no prompts under resilient_parsing
- **`Option.value_from_envvar`** (`src/click/core.py:3579-3625`)
  - Signature: `def value_from_envvar(self, ctx: Context) -> t.Any`
  - Behavior: Uses Parameter.resolve_envvar_value, then falls back to '<ctx.auto_envvar_prefix>_<NAME>' when allow_from_autoenv is true. For non-bool flags: the string equal to flag_value gives flag_value; a truthy bool reading gives flag_value, a falsy one gives False, and an unrecognised one gives None. Otherwise it splits for nargs != 1 or multiple (batched by nargs when both apply).
  - Edge case: empty env value counts as unset
- **`Option.prompt_for_value`** (`src/click/core.py:3506-3553`)
  - Signature: `def prompt_for_value(self, ctx: Context) -> t.Any`
  - Behavior: Locks in get_default, then uses confirm() for boolean flags (default coerced to bool, or None when unset). Otherwise it calls prompt() with type, hide_input, confirmation_prompt, show_choices, and value_proc=process_value.
  - Edge case: show_default is forwarded only when not None
- **`Argument.__init__`** (`src/click/core.py:3713-3733`)
  - Signature: `def __init__(self, param_decls: cabc.Sequence[str], required: bool | None=None, help: str | None=None, **attrs: t.Any) -> None`
  - Behavior: required defaults to True when no default was given and nargs > 0 (nargs=-1 gives False), and to False when a default exists. multiple is rejected. Exactly one declaration is allowed, and the name is the declaration with '-' replaced by '_' and lower-cased. param_type_name is 'argument'. A deprecated argument gets '!' appended to its metavar. Optional arguments are shown in [brackets] unless the metavar is already bracketed, and nargs != 1 appends '...'.
  - Edge case: multiple raises TypeError
  - Edge case: no declaration with expose_value=True raises TypeError
  - Edge case: more than one declaration raises TypeError
  - Edge case: no declaration with expose_value=False gives an empty name
  - Raises: `TypeError`

### Error conventions
Programming errors use built-in exceptions: TypeError for bad declarations (names, flag/prompt/count combinations, Argument with multiple or the wrong number of decls, missing command name or callback); ValueError for invalid combinations such as required+deprecated, deprecated+prompt, nargs vs composite type arity, or a same-flag true/false pair; RuntimeError for chain-mode misuse (nested groups, optional arguments in chain mode). Many of these checks run only under __debug__ (Parameter.__init__, Option._validate). Messages are plain, with quoted names (e.g. "'nargs' must be ..."). Runtime user errors use click.exceptions: UsageError (via ctx.fail, e.g. 'Missing command.' and 'Got unexpected extra argument(s) (...)'), BadParameter (conversion, 'Takes N values but M were given.', 'Value must be an iterable.'), MissingParameter, NoSuchCommand, NoArgsIsHelpError. Exit and Abort are control flow. The augment_usage_errors context manager attaches ctx and param to errors that lack them. User-facing strings go through gettext (`_`, ngettext); developer errors do not. Deprecation notices are echoed in red to stderr as 'DeprecationWarning: The ... is deprecated.[ reason]'. Python warnings.warn is used for duplicate names/opts (in Command.get_params) and for deprecated attribute access (BaseCommand, MultiCommand, Context.protected_args).

### Examples
Passing default_map through the runner to override an option default for a subcommand (`tests/test_commands.py:104-117`)
```
@click.group()
def cli():
    pass

@cli.command()
@click.option("--name", default="normal")
def foo(name):
    click.echo(name)

result = runner.invoke(cli, ["foo"], default_map={"foo": {"name": "changed"}})
assert result.output == "changed\n"
```
Group result callback, including invoke_without_command with chain (`tests/test_chain.py:95-104`)
```
@click.group(invoke_without_command=True, chain=chain)
def cli():
    return 1

@cli.result_callback()
def process_result(result):
    click.echo(result, nl=False)

result = runner.invoke(cli, [])
```
Result callback docstring example (receives the subcommand result plus the group params) (`src/click/core.py:1925-1932`)
```
@click.group()
@click.option('-i', '--input', default=23)
def cli(input):
    return 42

@cli.result_callback()
def process_result(result, input):
    return result + input
```
Using the parameter source ordering to detect an explicitly provided value (`src/click/core.py:186-188`)
```
source = ctx.get_parameter_source("port")
if source < click.ParameterSource.DEFAULT_MAP:
    ...  # value was explicitly set
```
Registering a resource for cleanup on the context (`src/click/core.py:668-672`)
```
@click.group()
@click.option("--name")
@click.pass_context
def cli(ctx):
    ctx.obj = ctx.with_resource(connect_db(name))
```

### Tests
- `tests/test_commands.py`: Uses the `runner` fixture with runner.invoke(cli, args, default_map=...). It asserts on result.output, result.exit_code and result.exception. Covers groups, help output and default_map (e.g. lines 104-117 and 355).
- `tests/test_chain.py`: Uses parametrized chain/non-chain cases with runner.invoke. It compares result.output against expected strings for result callbacks, chained results and arguments (e.g. lines 88-104).
- `tests/test_context.py`: Tests the Context API directly. It covers get_parameter_source across the parametrized sources (default_map at lines 734-769) and context object behaviour. Assertions are on the returned values.
- `tests/test_defaults.py`: Parametrized tests of default resolution. It covers flag defaults in default_map, Context.lookup_default hiding the UNSET sentinel, and callable defaults in default_map (lines 171-232). It asserts on the returned values and the (value, source) pairs.
- `tests/test_options.py`: Option behaviour via runner.invoke and result.output/exit_code. Not individually read.
- `tests/test_arguments.py`: Argument behaviour via runner.invoke. Not individually read.
- `tests/test_basic.py`: Basic CLI end-to-end tests via runner. Not individually read.
- `tests/test_deprecations.py`: Deprecation tests. Warnings are errors under filterwarnings=error, so expected ones must be caught explicitly. Not individually read.
- `tests/test_info_dict.py`: Compares to_info_dict output with expected dicts. Not individually read.
- `tests/typing/typing_aliased_group.py`: Static typing check only (mypy/pyright), not run by pytest.

### Extension points
- **Context.formatter_class** (`src/click/core.py:315`): A custom HelpFormatter subclass, used by Context.make_formatter.
- **Command.context_class** (`src/click/core.py:1011`): A Context subclass used by make_context (and by _make_sub_context via type(self)).
- **Group.command_class / Group.group_class** (`src/click/core.py:1709`): Default classes for the Group.command and Group.group decorators. group_class=type means 'use the group's own class'.
- **Group.get_command / Group.list_commands** (`src/click/core.py:1959`): Override for lazy or plugin loading, aliases or fuzzy lookup. CommandCollection, help, completion and to_info_dict all go through them.
- **Group.resolve_command** (`src/click/core.py:2088`): Override to add prefix matching, aliases or default commands. It already honours Context.token_normalize_func.
- **Group.result_callback** (`src/click/core.py:1914`): Post-processing hook that receives the results of subcommands. In chain mode it receives them as a list (pipelines).
- **Parameter callback and shell_complete arguments** (`src/click/core.py:2342`): Validation or transformation callbacks (ctx, param, value), and custom completion functions.
- **Parameter.type_cast_value / process_value / consume_value / get_default / resolve_envvar_value** (`src/click/core.py:2566`): Subclass overrides for custom value sources (config files, secrets stores), conversion rules or extra validation. process_value and consume_value are marked :meta private: but are overridden by Option.
- **Context.default_map and Command.context_settings** (`src/click/core.py:1061`): Config-file-driven defaults. Nested default_map keys follow the command's info_name, and context_settings are merged into the context kwargs.
- **Context.call_on_close / with_resource / meta** (`src/click/core.py:681`): Resource cleanup hooks and shared state for plugins.
- **Command.format_* / get_help_record / get_usage_pieces** (`src/click/core.py:1159`): Help rendering customisations such as extra sections or grouped options.
- **Option.get_help_extra** (`src/click/core.py:3423`): Extra annotations in option help (default, range, env var, required).
- **Command.get_params / make_parser** (`src/click/core.py:1103`): Injecting dynamic parameters, or altering the parser setup.

### Gaps (model's judgment, not verifiable from code)
- No built-in command aliases or unambiguous-prefix matching for subcommands. Group.resolve_command does exact lookup, plus token_normalize_func, only. Why plausible: A small override or hook in resolve_command would cover it. Documented recipes for this exist but nothing in core. Nearest: `Group.resolve_command`
- No mutually-exclusive or required-together option constraints. Options only interact through shared names (feature switches). Why plausible: The post-parse pass in Command.parse_args has all params and sources available, so a validation hook could slot in there. Nearest: `Command.parse_args`
- No built-in config-file or layered default source. default_map is the only injection point and must be supplied by the caller. Why plausible: consume_value already has an ordered source chain, so another source would fit between ENVIRONMENT and DEFAULT_MAP, with a matching ParameterSource member. Nearest: `Parameter.consume_value`
- No per-command post-parse or pre-invoke hooks. Only Group.result_callback exists, and only for groups. Why plausible: Command.invoke is a single place to wrap, and the Group result-callback chaining logic could be reused. Nearest: `Group.result_callback`
- Group.add_command silently overwrites existing names, and there is no way to remove or unregister a command. Why plausible: It is a small API addition, and commands is a plain dict. Nearest: `Group.add_command`
- Option has no explicit group or section for help output. Command.format_options lists all options in one flat section. Why plausible: Option.get_help_record and Command.format_options are the natural place for grouping. Nearest: `Command.format_options`

## Module card: `src/click/decorators.py`
src/click/decorators.py (626 lines) holds the decorator layer. Context-passing decorators: pass_context, pass_obj, make_pass_decorator, pass_meta_key. Builders: command and group. Parameter attachers: argument and option. Pre-configured options: confirmation_option, password_option, version_option, custom_version_option and help_option. Parameters are stashed on the function's `__click_params__` list by `_param_memo`. `command()` consumes that list when it builds the Command, and it appends in reverse so the order matches the source. All pre-configured options are thin wrappers that call `option()` with `kwargs.setdefault(...)`.

### Interfaces
- **`pass_context`** (`src/click/decorators.py:28-36`)
  - Signature: `def pass_context(f: t.Callable[te.Concatenate[Context, P], R]) -> t.Callable[P, R]`
  - Behavior: Wraps f so it is called with get_current_context() as first arg, then the original args. Uses update_wrapper. Does not go through ctx.invoke.
  - Edge case: Called outside an active context, get_current_context() raises RuntimeError (raised in globals, not here)
- **`pass_obj`** (`src/click/decorators.py:39-48`)
  - Signature: `def pass_obj(f: t.Callable[te.Concatenate[T, P], R]) -> t.Callable[P, R]`
  - Behavior: Passes get_current_context().obj as first arg, then the original args. Uses update_wrapper.
  - Edge case: obj may be None if the context has no obj set; it is passed through as None
- **`make_pass_decorator`** (`src/click/decorators.py:51-97`)
  - Signature: `def make_pass_decorator(object_type: type[T], ensure: bool=False) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]`
  - Behavior: Returns a decorator. At call time it takes ctx.ensure_object(object_type) if ensure=True, otherwise ctx.find_object(object_type). It then calls ctx.invoke(f, obj, *args, **kwargs).
  - Edge case: With ensure=False and no matching object found (None), it raises RuntimeError
  - Edge case: ensure=True creates the object and stores it on the context
  - Edge case: Uses isinstance matching via find_object, over the innermost context outward
  - Raises: `RuntimeError`
- **`pass_meta_key`** (`src/click/decorators.py:100-130`)
  - Signature: `def pass_meta_key(key: str, *, doc_description: str | None=None) -> t.Callable[[t.Callable[te.Concatenate[T, P], R]], t.Callable[P, R]]`
  - Behavior: Returns a decorator that passes ctx.meta[key] as first arg via ctx.invoke. Builds the decorator's __doc__ from doc_description, defaulting to "the 'key' key from :attr:`click.Context.meta`". doc_description is keyword-only.
  - Edge case: A missing key raises KeyError from ctx.meta[key] at call time
  - Raises (unconfirmed, likely via a helper): `KeyError`
- **`command`** (`src/click/decorators.py:168-255`)
  - Signature: `def command(name: str | _AnyCallable | None=None, cls: type[CmdType] | None=None, **attrs: t.Any) -> Command | t.Callable[[_AnyCallable], Command | CmdType]`
  - Behavior: Creates a Command (or `cls`) from a function. Usable bare (`@command`) or with parentheses. If `name` is callable it is treated as the function, and cls/attrs must be unset, enforced with assert. The decorator pops `params` from attrs. It appends the function's `__click_params__` in reversed order and deletes the attribute. help defaults to f.__doc__ when attrs['help'] is None. The name defaults to f.__name__ lowercased with _ replaced by -, and a trailing -command/-cmd/-group/-grp suffix is stripped. It then builds cls(name=..., callback=f, params=params, **attrs) and sets cmd.__doc__ = f.__doc__.
  - Edge case: Decorating an existing Command raises TypeError
  - Edge case: `attrs.pop('params')` mutates the shared attrs dict, so a decorator object reused across several functions loses `params` after its first use
  - Edge case: The caller's params list is extended in place
  - Edge case: A name that is only a suffix (e.g. 'command') is not stripped, because rpartition finds no separator
  - Edge case: A positional name passed together with a callable name is not allowed (assert)
  - Raises: `TypeError`
  - Raises (unconfirmed, likely via a helper): `AssertionError`
- **`group`** (`src/click/decorators.py:293-311`)
  - Signature: `def group(name: str | _AnyCallable | None=None, cls: type[GrpType] | None=None, **attrs: t.Any) -> Group | t.Callable[[_AnyCallable], Group | GrpType]`
  - Behavior: Same as command, with cls defaulting to Group. A callable `name` gives command(cls=cls, **attrs)(name). Otherwise it calls command(name, cls, **attrs).
  - Edge case: With bare use, a positional cls is not possible (name is the function)
  - Raises (unconfirmed, likely via a helper): `TypeError`
- **`argument`** (`src/click/decorators.py:324-349`)
  - Signature: `def argument(*param_decls: str, cls: type[Argument] | None=None, **attrs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Returns a decorator that builds cls(param_decls, **attrs), with cls defaulting to Argument. It attaches it through _param_memo and returns f unchanged.
  - Edge case: Works on a Command instance, where it appends directly to f.params (not reversed), or on a plain function, where it appends to __click_params__
  - Edge case: Decorator order: the bottom-most decorator becomes the first parameter, because command() reverses the list
- **`option`** (`src/click/decorators.py:352-377`)
  - Signature: `def option(*param_decls: str, cls: type[Option] | None=None, **attrs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Same as argument but builds an Option, with cls defaulting to Option. param_decls are passed as a tuple to the constructor. Attaches it via _param_memo and returns f.
  - Edge case: The Option is instantiated when the decorator is applied, not at decoration-factory time, so each application gets a fresh Option
  - Edge case: Declaration errors come from Option.__init__ (core)
- **`confirmation_option`** (`src/click/decorators.py:380-401`)
  - Signature: `def confirmation_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Wraps option. Default decl is ('--yes'). Defaults set with setdefault: is_flag=True, callback (calls ctx.abort() if the value is falsy), expose_value=False, prompt=_('Do you want to continue?'), help=_('Confirm the action without prompting.').
  - Edge case: Any default can be overridden through kwargs
  - Edge case: Declining the prompt aborts, so Abort/exit code 1
  - Edge case: Passing --yes skips the prompt
- **`password_option`** (`src/click/decorators.py:404-418`)
  - Signature: `def password_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Wraps option. Default decl is ('--password'). Defaults set with setdefault: prompt=True, confirmation_prompt=True, hide_input=True. The value stays exposed to the function.
  - Edge case: The values can be overridden in kwargs
- **`version_option`** (`src/click/decorators.py:421-556`)
  - Signature: `def version_option(version: str | None=None, *param_decls: str, package_name: str | None=None, prog_name: str | None=None, message: str | None=None, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Adds an eager --version flag. Signature: (version=None, *param_decls, package_name=None, prog_name=None, message=None, **kwargs). If both version and package_name are None, it inspects the caller's frame globals (__name__, or __package__ if __main__) and takes the top-level segment as package_name. The callback is skipped if the value is falsy or ctx.resilient_parsing. prog_name defaults to ctx.find_root().info_name. If version is None, it calls importlib.metadata.version(package_name). On PackageNotFoundError it tries packages_distributions(): one match is used, several raise RuntimeError, none raise RuntimeError. The default message is '%(prog)s, version %(version)s', and the % mapping has only prog, package and version. It then echoes with color=ctx.color and calls ctx.exit(). Defaults set with setdefault: is_flag, expose_value=False, is_eager=True, help. callback is forced via kwargs['callback'] = callback, which overrides any user callback.
  - Edge case: Version detection is lazy (done at invocation, not at decoration time)
  - Edge case: Caches the resolved version, prog_name and package_name through nonlocal
  - Edge case: If version is None and package_name is None and the frame cannot be found, a RuntimeError is raised at invocation
  - Edge case: The docstring says the message slots are frozen
  - Raises: `RuntimeError`
- **`custom_version_option`** (`src/click/decorators.py:559-598`)
  - Signature: `def custom_version_option(callback: t.Callable[[Context], str], *param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Added in 8.5.0. Signature: (callback: Callable[[Context], str], *param_decls, **kwargs). The inner show_version skips when the value is falsy or ctx.resilient_parsing. Otherwise it echoes callback(ctx) with color=ctx.color and calls ctx.exit(). Default decl is ('--version'). Defaults set with setdefault: is_flag, expose_value=False, is_eager=True, help. callback is forced via kwargs['callback'] = show_version.
  - Edge case: The user's callback receives only a Context
  - Edge case: Passing callback= in kwargs would conflict with the positional parameter name; use the positional parameter instead
- **`help_option`** (`src/click/decorators.py:601-625`)
  - Signature: `def help_option(*param_decls: str, **kwargs: t.Any) -> t.Callable[[FC], FC]`
  - Behavior: Adds a --help flag. Default decl is ('--help'). The callback show_help echoes ctx.get_help() with color=ctx.color and calls ctx.exit(), when the value is set and not resilient_parsing. Defaults set with setdefault: is_flag, expose_value=False, is_eager=True, help=_('Show this message and exit.'), callback=show_help.
  - Edge case: The callback can be overridden through kwargs
  - Edge case: Passing custom names, e.g. '-h', is the supported way to rename help flags

### Error conventions
TypeError is used for double conversion of a callback into a command (message: 'Attempted to convert a callback into a command twice.'). AssertionError is used with imperative 'Use ...' messages for misuse of the bare form of command. RuntimeError is used at invocation time for missing context objects (make_pass_decorator) and for version detection failures; the message quotes the name with !r and suggests passing 'package_name'. User-facing option strings are wrapped in gettext `_()`. Failures are not raised as ClickException.

### Examples
Bare @click.command (`tests/test_command_decorators.py:6-9`)
```
@click.command
def cli():
    click.echo("hello")
```
params= combined with a decorated argument (`tests/test_command_decorators.py:63-68`)
```
opt = click.Argument(["a"])

@click.command(params=[opt])
@click.argument("b")
def cli(a, b):
    click.echo(f"{a} {b}")
```
custom_version_option with two names (`tests/test_basic.py:936-939`)
```
@click.command()
@click.custom_version_option(lambda ctx: "custom 9.9.9", "-V", "--version")
def cli():
    pass
```
confirmation_option with a custom prompt, from the docs (`docs/option-decorators.md:79-79`)
```
@click.confirmation_option(prompt='Are you sure you want to drop the db?')
```

### Tests
- `tests/test_command_decorators.py`: Uses the `runner` fixture and runner.invoke. Asserts result.exception is None and result.output equals the expected string. Also checks cli.params[i].name, and parametrizes test_generate_name over function names to check suffix stripping.
- `tests/test_basic.py`: Covers version_option (import-name resolution, ambiguity and unknown-package errors via monkeypatch, asserting exit_code != 0 and message text in str(result.exception)) and custom_version_option (exit_code == 0 and exact output). Also covers pass_context-style usage and option behaviors.
- `tests/typing/typing_aliased_group.py`: A static typing check run with mypy and pyright, not pytest. It checks that the group/command overloads type correctly. I did not read this file; other typing_*_option.py files exist for help, version, password and confirmation options.

### Extension points
- **command(cls=...)/group(cls=...) class hook** (`src/click/decorators.py:248`): Custom Command/Group subclasses are instantiated here with name, callback, params and **attrs. Extra attrs flow through to the subclass constructor.
- **option(cls=...)** (`src/click/decorators.py:374`): Custom Option subclasses can be supplied. Any new pre-configured option can be written as a wrapper calling option() with setdefault kwargs.
- **argument(cls=...)** (`src/click/decorators.py:346`): Custom Argument subclasses.
- **_param_memo** (`src/click/decorators.py:314`): Central place where parameters are recorded (__click_params__ on a function, or Command.params).
- **make_pass_decorator** (`src/click/decorators.py:51`): A factory for typed context-object injectors. pass_meta_key at line 100 is the sibling factory for meta keys.
- **custom_version_option callback** (`src/click/decorators.py:559`): A user callable that renders arbitrary version output.
- **help_option / confirmation_option callbacks** (`src/click/decorators.py:610`): Callbacks can be replaced through kwargs['callback'], since they use setdefault.

### Gaps (model's judgment, not verifiable from code)
- command() does not copy attrs, so `attrs.pop('params')` mutates it and a decorator object reused for several functions loses its params after the first use Why plausible: A small robustness fix: copy attrs inside decorator(). Nearest: `command`
- There is no pass-decorator for a named key of ctx.params or ctx.obj attribute, and no option-less decorator for other eager options (e.g. --debug or --verbose counting flags). Why plausible: Matches how pass_meta_key and help_option are built on existing primitives. Nearest: `pass_meta_key`
- version_option replaces any user-supplied `callback` (kwargs['callback'] = callback), unlike help_option and confirmation_option, which use setdefault. Its message slots are documented as frozen. Why plausible: The inconsistency could be documented or unified. The docstring points users to custom_version_option instead. Nearest: `version_option`
- Missing-key errors from pass_meta_key surface as a bare KeyError, with no message naming the key. Why plausible: A descriptive RuntimeError, like the one in make_pass_decorator, would be consistent. Nearest: `pass_meta_key`

## Module card: `src/click/types.py`
src/click/types.py defines ParamType, a generic abstract base class. A ParamType validates and converts a raw value (CLI string, env var, default or prompt input) into a Python value. Its subclasses are FuncParamType, UnprocessedParamType, StringParamType, Choice, DateTime, IntParamType/IntRange, FloatParamType/FloatRange, BoolParamType, UUIDParameterType, File, Path and the composite Tuple. convert_type maps Python types or defaults to ParamType instances. Module-level singletons are UNPROCESSED, STRING, INT, FLOAT, BOOL and UUID. Failures go through ParamType.fail, which raises BadParameter. Every type has to_info_dict for documentation tooling. A few types add shell_complete and get_metavar. I read the whole file. For tests I read only test_Choice.py in full, and I grepped test_convert_type.py and test_info_dict.py. I did not read the docs.

### Interfaces
- **`ParamType`** (`src/click/types.py:65-239`)
  - Signature: `class ParamType(t.Generic[_ValueT_co, _InputT_contra], abc.ABC)`
  - Behavior: Generic ABC (value type, input type). Class attrs: is_composite=False, arity=1, name (must be set by subclasses), envvar_list_splitter=None (None means whitespace split). The default convert returns the value unchanged. On Python < 3.13, __class_getitem__ fills in Any as the second type parameter.
  - Edge case: A subclass without `name` gets the class name (suffix stripped) in to_info_dict via hasattr
- **`ParamType.__call__`** (`src/click/types.py:159-167`)
  - Signature: `def __call__(self, value: _InputT_contra | None, param: Parameter | None=None, ctx: Context | None=None) -> _ValueT_co | None`
  - Behavior: Returns None if value is None. Otherwise returns self.convert(value, param, ctx). param and ctx default to None.
  - Edge case: None short-circuits without calling convert
- **`ParamType.convert`** (`src/click/types.py:179-203`)
  - Signature: `def convert(self, value: _InputT_contra, param: Parameter | None, ctx: Context | None) -> _ValueT_co`
  - Behavior: Override point. The base implementation returns the value as-is (cast). Subclasses should accept already-converted values and work with param and ctx set to None (prompts).
  - Edge case: param/ctx may be None
- **`ParamType.fail`** (`src/click/types.py:215-222`)
  - Signature: `def fail(self, message: str, param: Parameter | None=None, ctx: Context | None=None) -> t.NoReturn`
  - Behavior: Raises BadParameter(message, ctx=ctx, param=param). Typed NoReturn.
  - Raises: `BadParameter`
- **`ParamType.to_info_dict`** (`src/click/types.py:122-141`)
  - Signature: `def to_info_dict(self) -> ParamTypeInfoDict`
  - Behavior: Returns {'param_type': class name truncated at 'ParamType' and then 'ParameterType', 'name': self.name or the class-derived name}. Subclasses extend it by merging extra keys.
  - Edge case: IntParamType gives 'Int', UUIDParameterType gives 'UUID'
- **`ParamType.get_metavar`** (`src/click/types.py:169-170`)
  - Signature: `def get_metavar(self, param: Parameter, ctx: Context) -> str | None`
  - Behavior: Returns None by default. Used for help-text metavar.
- **`ParamType.get_missing_message`** (`src/click/types.py:172-177`)
  - Signature: `def get_missing_message(self, param: Parameter, ctx: Context | None) -> str | None`
  - Behavior: Returns None by default. Extra text for a missing-parameter error.
- **`ParamType.split_envvar_value`** (`src/click/types.py:205-213`)
  - Signature: `def split_envvar_value(self, rv: str) -> cabc.Sequence[str]`
  - Behavior: Returns (rv or '').split(self.envvar_list_splitter).
  - Edge case: None or empty string becomes ''.split(), which is []
  - Edge case: With a splitter of None, whitespace is stripped; otherwise empty items can appear
- **`ParamType.shell_complete`** (`src/click/types.py:224-239`)
  - Signature: `def shell_complete(self, ctx: Context, param: Parameter, incomplete: str) -> list[CompletionItem]`
  - Behavior: Returns [] by default. Subclasses return CompletionItem lists.
- **`CompositeParamType`** (`src/click/types.py:242-247`)
  - Signature: `class CompositeParamType(ParamType[_ValueT_co])`
  - Behavior: ParamType subclass with is_composite=True and an abstract arity property. Base for Tuple.
- **`FuncParamType`** (`src/click/types.py:264-289`)
  - Signature: `class FuncParamType(ParamType[_ValueT_co], t.Generic[_ValueT_contra, _ValueT_co])  # __init__(self, func: t.Callable[[_ValueT_contra], _ValueT_co])`
  - Behavior: Wraps a callable. name is func.__name__. convert calls func(value). A ValueError becomes fail(str(exc)). If the message is empty it falls back to str(value), or to bytes decoded as utf-8 with 'replace' on UnicodeError. to_info_dict adds 'func'.
  - Edge case: Only ValueError is caught; other exceptions propagate
  - Edge case: Callables without __name__ (e.g. functools.partial) fail in __init__ with AttributeError
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`UnprocessedParamType`** (`src/click/types.py:292-301`)
  - Signature: `class UnprocessedParamType(ParamType[t.Any])`
  - Behavior: name='text'. convert returns the value untouched, so bytes are not decoded. repr is 'UNPROCESSED'.
- **`StringParamType`** (`src/click/types.py:304-326`)
  - Signature: `class StringParamType(ParamType[str])`
  - Behavior: name='text'. bytes are decoded with the argv encoding, then the filesystem encoding, then utf-8 with 'replace'. Anything else becomes str(value).
  - Edge case: Never fails; undecodable bytes get replacement characters
- **`Choice`** (`src/click/types.py:342-515`)
  - Signature: `class Choice(ParamType[_ValueT_co], t.Generic[_ValueT_co])  # __init__(self, choices: cabc.Iterable[_ValueT_co], case_sensitive: bool=True)`
  - Behavior: Choice(choices, case_sensitive=True). choices is stored as a tuple, so any iterable works. convert normalizes the input and each choice via normalize_choice, then returns the first original choice whose normalized form matches. Enum members normalize to .name, other values to str(). If ctx.token_normalize_func is set it is applied. With case_sensitive=False the value is casefolded. get_metavar gives {a|b} for a required argument and [a|b] otherwise. For an option with show_choices False it shows type names, e.g. [TEXT]. get_missing_message lists the choices. shell_complete returns prefix-matching CompletionItems. to_info_dict adds choices and case_sensitive.
  - Edge case: The mapping is rebuilt on every convert call
  - Edge case: Duplicate normalized values silently resolve to the first match
  - Edge case: Non-str inputs are normalized with str()
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Choice.normalize_choice`** (`src/click/types.py:406-424`)
  - Signature: `def normalize_choice(self, choice: object, ctx: Context | None) -> str`
  - Behavior: normalize_choice(choice, ctx) -> str. Override to customize how values and choices are mapped to strings. Each choice should normalize to a unique string.
  - Edge case: ctx may be None
- **`Choice.get_invalid_choice_message`** (`src/click/types.py:478-490`)
  - Signature: `def get_invalid_choice_message(self, value: t.Any, ctx: Context | None) -> str`
  - Behavior: get_invalid_choice_message(value, ctx) uses ngettext. Singular: "'d' is not 'a'." Plural: "'d' is not one of 'a', 'b', 'c'." Normalized choices are shown with repr.
  - Edge case: The plural form is chosen by len(self.choices)
- **`DateTime`** (`src/click/types.py:522-590`)
  - Signature: `class DateTime(ParamType[datetime])  # __init__(self, formats: cabc.Sequence[str] | None=None)`
  - Behavior: DateTime(formats=None). Defaults to '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S' and '%Y-%m-%d %H:%M:%S'. convert returns a datetime as-is. Otherwise it tries each format with strptime in order and returns the first success. get_metavar returns [fmt1|fmt2]. to_info_dict adds formats.
  - Edge case: An empty formats list falls back to the defaults (`formats or [...]`)
  - Edge case: A non-str value passed to strptime raises TypeError, which is not caught
  - Edge case: A generator for formats is unsafe
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`IntRange`** (`src/click/types.py:744-765`)
  - Signature: `class IntRange(_NumberRangeBase[int, int], IntParamType)`
  - Behavior: IntRange(min=None, max=None, min_open=False, max_open=False, clamp=False), a subclass of IntParamType. Converts via int() and then checks the range. With clamp, an out-of-range value returns the bound, or bound±1 when that side is open. Otherwise it fails with '{value} is not in the range {x<=...}.' to_info_dict includes min, max, min_open, max_open and clamp. name='integer range'.
  - Edge case: Clamping is checked on min first, then max
  - Edge case: int() ValueError becomes 'is not a valid integer range' (the message uses self.name)
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`FloatRange`** (`src/click/types.py:776-816`)
  - Signature: `class FloatRange(_NumberRangeBase[float, float], FloatParamType)  # __init__(self, min: float | None=None, max: float | None=None, min_open: bool=False, max_open: bool=False, clamp: bool=False)`
  - Behavior: Same parameters as IntRange, with float conversion and name='float range'. The constructor raises TypeError if clamp is combined with min_open or max_open. _clamp raises RuntimeError for open bounds.
  - Edge case: float('nan') passes the range comparisons as False and so is accepted
  - Edge case: The error message uses the type name, 'float range'
  - Raises: `TypeError`, `RuntimeError`
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`IntParamType`** (`src/click/types.py:736-741`)
  - Signature: `class IntParamType(_NumberParamTypeBase[t.SupportsInt | t.SupportsIndex, int])`
  - Behavior: name='integer'. Uses _number_class=int. Invalid input gives "{value!r} is not a valid integer." repr is 'INT'.
  - Edge case: int('1_000') is accepted by Python's int
  - Edge case: Float strings are rejected
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`FloatParamType`** (`src/click/types.py:768-773`)
  - Signature: `class FloatParamType(_NumberParamTypeBase[t.SupportsFloat | t.SupportsIndex, float])`
  - Behavior: name='float'. Uses float(). repr is 'FLOAT'.
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`BoolParamType`** (`src/click/types.py:819-885`)
  - Signature: `class BoolParamType(ParamType[bool])`
  - Behavior: name='boolean'. The bool_states dict maps 1/0/yes/no/true/false/on/off/t/f/y/n and '' to a bool. str_to_bool strips and lowercases, and passes through bool values. It returns None for unknown strings, and convert then fails listing the sorted recognized values.
  - Edge case: The empty string converts to False
  - Edge case: A non-str, non-bool value (e.g. int 1) raises AttributeError on .strip()
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`UUIDParameterType`** (`src/click/types.py:888-907`)
  - Signature: `class UUIDParameterType(ParamType[uuid.UUID])`
  - Behavior: name='uuid'. Returns a uuid.UUID as-is. Otherwise strips the string and calls uuid.UUID. Exposed as the UUID singleton.
  - Edge case: Invalid input fails with "... is not a valid UUID."
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`File`** (`src/click/types.py:915-1043`)
  - Signature: `class File(ParamType[t.IO[t.Any]])  # __init__(self, mode: str='r', encoding: str | None=None, errors: str | None='strict', lazy: bool | None=None, atomic: bool=False)`
  - Behavior: File(mode='r', encoding=None, errors='strict', lazy=None, atomic=False). Values that already have read or write are returned as-is. resolve_lazy_flag: an explicit lazy wins; '-' is never lazy; a mode containing 'w' is lazy; otherwise not lazy. A lazy file becomes _LazyFile and is registered via ctx.call_on_close(close_intelligently). A non-lazy file is opened with open_stream and closed or flushed on context close. OSError becomes fail with "'filename': strerror". envvar_list_splitter is os.path.pathsep. shell_complete returns a file-type CompletionItem.
  - Edge case: With ctx=None the caller must close the file
  - Edge case: Modes like 'a' or 'x' are not lazy by default
  - Edge case: Only 'w' triggers the lazy default
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Path`** (`src/click/types.py:1059-1251`)
  - Signature: `class Path(ParamType[_PathT_co, str | os.PathLike[str]], t.Generic[_PathT_co])  # __init__(self, exists: bool=False, file_okay: bool=True, dir_okay: bool=True, writable: bool=False, readable: bool=True, resolve_path: bool=False, allow_dash: bool=False, path_type: type[_PathT_co] | None=None, executable: bool=False)`
  - Behavior: Path(exists=False, file_okay=True, dir_okay=True, writable=False, readable=True, resolve_path=False, allow_dash=False, path_type=None, executable=False). name is 'file', 'directory' or 'path' depending on file_okay and dir_okay. convert skips checks for '-' when file_okay and allow_dash are set. With resolve_path it applies realpath. If os.stat fails and exists is False it returns the coerced value without further checks. Otherwise it checks existence, then file vs dir, then readable, writable and executable. coerce_path_result applies path_type: str uses fsdecode, bytes uses fsencode, other types are called with the value. The executable check uses the original value, not the resolved rv.
  - Edge case: Checks are skipped silently for a nonexistent path when exists=False
  - Edge case: Dash with bytes input is compared against b'-'
  - Edge case: to_info_dict omits executable, resolve_path and path_type
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`Path.coerce_path_result`** (`src/click/types.py:1147-1159`)
  - Signature: `def coerce_path_result(self, value: str | os.PathLike[str]) -> _PathT_co`
  - Behavior: coerce_path_result(value) converts to self.type (the path_type argument). It is a no-op when the value is already an instance of that type.
  - Edge case: path_type=None leaves the value unchanged
- **`Tuple`** (`src/click/types.py:1258-1308`)
  - Signature: `class Tuple(CompositeParamType[tuple[t.Any, ...]])  # __init__(self, types: cabc.Sequence[type[t.Any] | ParamType[t.Any]])`
  - Behavior: Tuple(types) is a composite type. Each entry goes through convert_type. arity is len(types). name is '<int text>' style. convert checks the length, then applies each type to its item and returns a tuple. to_info_dict nests each type's info dict.
  - Edge case: len(value) is called, so a non-sized value raises TypeError
  - Edge case: An empty tuple has arity 0
  - Raises (unconfirmed, likely via a helper): `BadParameter`
- **`convert_type`** (`src/click/types.py:1356-1397`)
  - Signature: `def convert_type(ty: t.Any | None=None, default: t.Any | None=None) -> ParamType[t.Any]`
  - Behavior: convert_type(ty=None, default=None). _guess_type infers the type from the default. A tuple or list default uses its first item's type, or a tuple of types for nested sequences, and an empty one gives STRING. A tuple of types yields Tuple. A ParamType instance is returned unchanged. str or None gives STRING, int gives INT, float gives FLOAT, bool gives BOOL. A guessed type with no match falls back to STRING. Any other callable is wrapped in FuncParamType.
  - Edge case: Passing a ParamType subclass instead of an instance fails an AssertionError check when __debug__ is on
  - Edge case: dict or list are wrapped as FuncParamType
  - Edge case: uuid.UUID is not special-cased and becomes FuncParamType
  - Raises: `AssertionError`
- **`BoolParamType.str_to_bool`** (`src/click/types.py:856-868`)
  - Signature: `def str_to_bool(value: str | bool) -> bool | None`
  - Behavior: Static method that returns the bool for a string, or None when unknown.
  - Edge case: bool input is returned as-is

### Error conventions
Conversion and validation failures call ParamType.fail, which raises click.exceptions.BadParameter(message, ctx=ctx, param=param). Programmer errors raise other types: FloatRange.__init__ raises TypeError, FloatRange._clamp raises RuntimeError, and convert_type raises AssertionError when given a ParamType class. Messages are wrapped in gettext `_()`, or ngettext for singular/plural, and use `{value!r}`. Formats include "{value!r} is not a valid integer.", "{value} is not in the range {range}.", "{Name} {filename!r} does not exist." and "{value!r} is not one of 'a', 'b'.". Errors from the OS for File are "'name': strerror".

### Examples
Choice invalid-choice message (`tests/test_types/test_Choice.py:5-7`)
```
choice = click.Choice(["a", "b", "c"])
message = choice.get_invalid_choice_message("d", ctx=None)
assert message == "'d' is not one of 'a', 'b', 'c'."
```
Info dict for Choice (`tests/test_info_dict.py:110-116`)
```
click.Choice(("a", "b")),
{"param_type": "Choice", "name": "choice", "choices": ("a", "b"), "case_sensitive": True}
```
IntRange info dict (`tests/test_info_dict.py:126-135`)
```
click.IntRange(0, 10, clamp=True)  # -> param_type 'IntRange', name 'integer range', min 0, max 10, clamp True
```
convert_type infers STRING from an empty container default (`tests/test_types/test_convert_type.py:25-27`)
```
assert click.types.convert_type(None, default) is click.STRING
```
Unknown callables become FuncParamType (`tests/test_types/test_convert_type.py:93-94`)
```
param_type = click.types.convert_type(dict)
assert isinstance(param_type, click.types.FuncParamType)
```

### Tests
- `tests/test_types/test_Choice.py`: A single plain-assert test. It calls Choice.get_invalid_choice_message directly with ctx=None and compares the exact string.
- `tests/test_types/test_convert_type.py`: Parametrized tests. They check that convert_type returns the identical singleton (`is click.STRING` etc.) for defaults. For container types and dict they check isinstance(..., FuncParamType), and for a nested default they check a Tuple result.
- `tests/test_info_dict.py`: A pytest.param table that pairs each type instance with an expected to_info_dict dict, with ids like 'Choice ParamType'. It compares equality against the full dict.

### Extension points
- **ParamType.convert / name / subclassing** (`src/click/types.py:179`): A custom type subclasses ParamType[T], sets `name`, and implements convert(), using self.fail for errors.
- **Choice.normalize_choice** (`src/click/types.py:406`): Override it for custom matching, such as prefix or alias matching, or normalization of non-str choices.
- **Choice.get_invalid_choice_message** (`src/click/types.py:478`): Override it for custom error text, for example to add did-you-mean suggestions.
- **BoolParamType.bool_states** (`src/click/types.py:822`): A class-level dict that can be subclassed or mutated to add recognized boolean strings. It is not user-configurable via a public API.
- **ParamType.shell_complete** (`src/click/types.py:224`): Custom completion items for a custom type.
- **ParamType.envvar_list_splitter** (`src/click/types.py:106`): Change how env-var values are split into lists.
- **convert_type** (`src/click/types.py:1356`): The dispatch from Python type to ParamType is a hardcoded if-chain. A registry could be added here for types such as UUID, Path or datetime.
- **Path.coerce_path_result** (`src/click/types.py:1147`): Hook for post-processing the result, e.g. a custom path_type or expanduser.
- **_NumberRangeBase._clamp / _NumberParamTypeBase._number_class** (`src/click/types.py:700`): A new numeric type such as Decimal can be added by subclassing with a _number_class and a _clamp.
- **CompositeParamType** (`src/click/types.py:242`): New multi-value types with an abstract arity.

### Gaps (model's judgment, not verifiable from code)
- No Enum-aware type. Choice accepts enum members, but matching is by name only and there is no value-based option. Why plausible: Choice.normalize_choice already special-cases enum.Enum and uses .name. Nearest: `Choice.normalize_choice`
- BoolParamType.bool_states is not configurable per instance, as its own docstring notes. Why plausible: The docstring says future work may make the mapping user-configurable. Nearest: `BoolParamType.bool_states`
- No Decimal, date-only, time or timedelta types, and no timezone-aware DateTime. Why plausible: Number types are built on _number_class, and DateTime only wraps strptime. Nearest: `DateTime`
- Path.to_info_dict omits executable, resolve_path and path_type. FloatRange cannot clamp open bounds, though math.nextafter would allow it. Why plausible: A code comment says nextafter could be used, and the info dict is a documentation-tooling interface. Nearest: `FloatRange._clamp`
- Choice has no prefix or fuzzy matching and no suggestion text in the error. Why plausible: get_invalid_choice_message and normalize_choice are existing overridable hooks. Nearest: `Choice.get_invalid_choice_message`

## Module card: `src/click/parser.py`
src/click/parser.py is Click's internal, optparse-derived parser. _OptionParser holds short/long option tables and positional _Argument specs. parse_args first scans options (_process_args_for_options) and then assigns positionals via _unpack_args. It returns (opts dict, leftover args, order list of Parameter objects). Core's Command.make_parser builds it and Option/Argument.add_to_parser register params. Old public names (OptionParser, Option, Argument, split_opt, normalize_opt, ParsingState, split_arg_string) are served by a module __getattr__ that emits DeprecationWarning.

### Interfaces
- **`_OptionParser`** (`src/click/parser.py:224-500`)
  - Signature: `class _OptionParser  # __init__(self, ctx: Context | None=None)`
  - Behavior: Internal parser. __init__(ctx=None) sets allow_interspersed_args=True and ignore_unknown_options=False, then copies both from ctx if given. Maintains _short_opt, _long_opt dicts, _opt_prefixes={'-','--'}, _args list. Docstring marks it deprecated 8.2, removal in 9.0.
  - Edge case: ctx None is allowed: no token normalization, no resilient parsing
- **`_OptionParser.add_option`** (`src/click/parser.py:265-288`)
  - Signature: `def add_option(self, obj: CoreOption, opts: cabc.Sequence[str], dest: str | None, action: str | None=None, nargs: int=1, const: t.Any | None=None) -> None`
  - Behavior: Normalizes each opt string via _normalize_opt (ctx.token_normalize_func), builds an _Option, adds its prefixes to _opt_prefixes, and registers short opts in _short_opt and long opts in _long_opt. dest is not inferred. Actions: store, store_const, append, append_const, count (default store).
  - Edge case: Option string with no prefix (starts with alnum) raises ValueError from _Option
  - Edge case: Later registration of the same opt string overwrites the earlier one
  - Edge case: Custom prefixes such as + or ! get added to _opt_prefixes
  - Raises (unconfirmed, likely via a helper): `ValueError`
- **`_OptionParser.add_argument`** (`src/click/parser.py:290-296`)
  - Signature: `def add_argument(self, obj: CoreArgument, dest: str | None, nargs: int=1) -> None`
  - Behavior: Appends an _Argument(obj, dest, nargs) to _args. Order of calls determines positional order.
  - Edge case: nargs=-1 means consume the remainder; two nargs<0 args later raise TypeError in _unpack_args
- **`_OptionParser.parse_args`** (`src/click/parser.py:298-314`)
  - Signature: `def parse_args(self, args: list[str]) -> tuple[dict[str, t.Any], list[str], list[CoreParameter]]`
  - Behavior: Creates _ParsingState(args), runs _process_args_for_options then _process_args_for_args, and returns (state.opts, state.largs, state.order). Mutates the passed list (rargs is popped).
  - Edge case: UsageError is swallowed when ctx is not None and ctx.resilient_parsing is True, returning the partial state
  - Edge case: Without ctx, UsageError always propagates
  - Raises: `UsageError`
  - Raises (unconfirmed, likely via a helper): `NoSuchOption`, `BadOptionUsage`, `BadArgumentUsage`, `TypeError`
- **`_OptionParser._process_args_for_options`** (`src/click/parser.py:327-341`)
  - Signature: `def _process_args_for_options(self, state: _ParsingState) -> None`
  - Behavior: Loop popping from rargs. '--' stops option processing and is consumed (dropped). An arg whose first char is in _opt_prefixes and len>1 goes to _process_opts. Otherwise, with allow_interspersed_args it is appended to largs, else it is pushed back onto rargs and parsing stops.
  - Edge case: A lone '-' is treated as a positional
  - Edge case: Without interspersed args, the first non-option stops option parsing
- **`_OptionParser._process_args_for_args`** (`src/click/parser.py:316-325`)
  - Signature: `def _process_args_for_args(self, state: _ParsingState) -> None`
  - Behavior: Calls _unpack_args on largs+rargs using each arg's nargs, calls each _Argument.process with its slice, then sets largs to the leftovers and rargs to [].
  - Edge case: Surplus values stay in largs, which is the returned leftover list
  - Edge case: Missing values become UNSET
  - Raises (unconfirmed, likely via a helper): `BadArgumentUsage`, `TypeError`
- **`_OptionParser._process_opts`** (`src/click/parser.py:470-500`)
  - Signature: `def _process_opts(self, arg: str, state: _ParsingState) -> None`
  - Behavior: Splits arg on the first '=' into long_opt and explicit_value, normalizes, and tries _match_long_opt. On NoSuchOption: if arg[:2] is not a known prefix (for example '-abc'), falls back to _match_short_opt. Otherwise, re-raises unless ignore_unknown_options, in which case the whole arg goes to largs.
  - Edge case: '-foo' can match a registered long option with a single dash
  - Edge case: Short-option clusters are only tried for single-char prefixes
  - Raises: `NoSuchOption`
- **`_OptionParser._match_long_opt`** (`src/click/parser.py:363-388`)
  - Signature: `def _match_long_opt(self, opt: str, explicit_value: str | None, state: _ParsingState) -> None`
  - Behavior: Looks up opt in _long_opt. If the option takes a value, an explicit '=value' is inserted at the front of rargs and then read by _get_value_from_state. Otherwise the value is UNSET, then option.process is called.
  - Edge case: Unknown opt raises NoSuchOption with possibilities=_long_opt for suggestions
  - Edge case: A flag given '=value' raises BadOptionUsage
  - Raises: `NoSuchOption`, `BadOptionUsage`
- **`_OptionParser._match_short_opt`** (`src/click/parser.py:390-428`)
  - Signature: `def _match_short_opt(self, arg: str, state: _ParsingState) -> None`
  - Behavior: Iterates over the characters of a cluster like -abc. Each character is normalized and looked up in _short_opt. A value-taking option consumes the remainder of the cluster as its value (pushed onto rargs) and stops.
  - Edge case: With ignore_unknown_options, unknown characters are collected and re-appended to largs as prefix+chars
  - Edge case: Otherwise unknown raises NoSuchOption
  - Raises: `NoSuchOption`
  - Raises (unconfirmed, likely via a helper): `BadOptionUsage`
- **`_OptionParser._get_value_from_state`** (`src/click/parser.py:430-468`)
  - Signature: `def _get_value_from_state(self, option_name: str, option: _Option, state: _ParsingState) -> str | cabc.Sequence[str] | T_UNSET | T_FLAG_NEEDS_VALUE`
  - Behavior: Gets the option value from rargs. If fewer than nargs remain: returns FLAG_NEEDS_VALUE when option.obj._flag_needs_value, else raises. For nargs==1 the next token is used, except that with _flag_needs_value a following token that looks like an option gives FLAG_NEEDS_VALUE. For nargs>1 returns a tuple and consumes nargs items.
  - Edge case: Value tokens that start with a prefix are consumed as values for ordinary options
  - Raises: `BadOptionUsage`
- **`_Option`** (`src/click/parser.py:127-182`)
  - Signature: `class _Option  # __init__(self, obj: CoreOption, opts: cabc.Sequence[str], dest: str | None, action: str | None=None, nargs: int=1, const: t.Any | None=None)`
  - Behavior: Holds the parsed option spec: _short_opts (prefix len 1 and name len 1), _long_opts (everything else), prefixes, dest, action (default 'store'), nargs, const, obj. takes_value is true for store and append. process(value, state) applies the action to state.opts and appends obj to state.order.
  - Edge case: Unknown action raises ValueError('unknown action ...') at process time, not at construction
  - Edge case: count starts from 0 and increments
  - Edge case: append and append_const use setdefault lists
  - Raises: `ValueError`
- **`_Option.process`** (`src/click/parser.py:169-182`)
  - Signature: `def process(self, value: t.Any, state: _ParsingState) -> None`
  - Behavior: store sets opts[dest]=value; store_const sets const; append and append_const append to a list; count increments. Always appends obj to state.order, so repeated options are recorded repeatedly.
  - Edge case: Unknown action raises ValueError
  - Raises: `ValueError`
- **`_Argument.process`** (`src/click/parser.py:191-213`)
  - Signature: `def process(self, value: str | cabc.Sequence[str | T_UNSET] | T_UNSET, state: _ParsingState) -> None`
  - Behavior: For nargs>1: if all items are UNSET the value becomes UNSET, if only some are it raises BadArgumentUsage. An empty tuple becomes UNSET. Stores into state.opts[dest] and appends obj to state.order.
  - Edge case: nargs=-1 with no values gives UNSET (not an empty tuple)
  - Raises: `BadArgumentUsage`
- **`_ParsingState`** (`src/click/parser.py:216-221`)
  - Signature: `class _ParsingState  # __init__(self, rargs: list[str])`
  - Behavior: Holds mutable parse state: opts dict, largs (leftovers/positionals), rargs (remaining), order list.
- **`_unpack_args`** (`src/click/parser.py:51-108`)
  - Signature: `def _unpack_args(args: cabc.Sequence[str], nargs_spec: cabc.Sequence[int]) -> tuple[cabc.Sequence[str | cabc.Sequence[str | T_UNSET] | T_UNSET], list[str]]`
  - Behavior: Distributes args across the nargs_spec. nargs==1 gives a str, nargs>1 gives a tuple, nargs<0 is a wildcard that takes the remainder. Specs after the wildcard are filled from the end, then reversed. Returns (tuple of values, leftover list). Missing values are UNSET.
  - Edge case: Only one wildcard is allowed
  - Edge case: Without a wildcard, excess args are returned as leftovers
  - Raises: `TypeError`
- **`_split_opt`** (`src/click/parser.py:111-117`)
  - Signature: `def _split_opt(opt: str) -> tuple[str, str]`
  - Behavior: Returns (prefix, rest). If the first char is alphanumeric the prefix is ''. If the first two chars are equal ('--') the prefix is two chars. Otherwise the prefix is one char.
  - Edge case: An empty string gives ('', '')
- **`_normalize_opt`** (`src/click/parser.py:120-124`)
  - Signature: `def _normalize_opt(opt: str, ctx: Context | None) -> str`
  - Behavior: Returns opt unchanged if ctx is None or has no token_normalize_func. Otherwise splits off the prefix and applies the function to the name only.
- **`__getattr__`** (`src/click/parser.py:503-533`)
  - Signature: `def __getattr__(name: str) -> object`
  - Behavior: Module-level deprecation shim. Names OptionParser, Argument, Option, split_opt, normalize_opt, ParsingState return globals()['_<name>'] with a DeprecationWarning (stacklevel 2). split_arg_string is re-imported from shell_completion with a warning. Anything else raises AttributeError.
  - Edge case: Other unknown names raise AttributeError(name)
  - Raises: `AttributeError`

### Error conventions
Parse problems raise click.exceptions UsageError subclasses. NoSuchOption is for an unknown option (with a possibilities list for suggestions). BadOptionUsage(option_name, msg) covers a missing value, a value given to a flag, or a wrong nargs count. BadArgumentUsage covers a partially filled multi-value positional. Programmer errors use ValueError (invalid option prefix or unknown action) and TypeError (two nargs<0). Messages are gettext-wrapped (`_` and `ngettext`) and use repr-quoted names, e.g. "Option {name!r} requires an argument." / "Option {name!r} requires {nargs} arguments." / "Option {name!r} does not take a value." / "Argument {name!r} takes {nargs} values.". The ValueError and TypeError messages: "Invalid start character for option ({option})" is translated, "Cannot have two nargs < 0" is not.

### Examples
Parser defaults to only - and -- as prefixes (`tests/test_parser.py:22-24`)
```
parser = _OptionParser()
assert parser._opt_prefixes == {"-", "--"}
```
Custom option prefixes are collected when options are added (`tests/test_parser.py:27-32`)
```
ctx = click.Context(click.Command("test"))
parser = _OptionParser(ctx)
click.Option("+p", is_flag=True).add_to_parser(parser, ctx)
click.Option("!e", is_flag=True).add_to_parser(parser, ctx)
assert parser._opt_prefixes == {"-", "--", "+", "!"}
```
How core builds the parser (Command.make_parser) (`src/click/core.py:1227-1229`)
```
parser = _OptionParser(ctx)
# ... params add themselves via param.add_to_parser(parser, ctx)
```

### Tests
- `tests/test_parser.py`: Plain pytest asserts. It checks private state (_opt_prefixes) directly on _OptionParser, both default and after Option.add_to_parser with custom prefixes '+' and '!'. It also has a parametrized test of shell_completion.split_arg_string. There are no direct tests of the parse_args error paths. Those are covered indirectly by the CliRunner-based tests for options and arguments elsewhere (not read).

### Extension points
- **Command.make_parser** (`src/click/core.py:1227`): Override in a Command subclass to return a customized _OptionParser (a subclass with different matching rules) or to pre-register extra options.
- **Parameter.add_to_parser (Option/Argument)** (`src/click/core.py:3325`): Custom Option/Argument subclasses decide how they register with the parser (action, nargs, const, dest).
- **Context.token_normalize_func via _normalize_opt** (`src/click/parser.py:120`): Supplying token_normalize_func on the Context changes how option names are matched (case-insensitive or alias handling).
- **_Option.process action dispatch** (`src/click/parser.py:169`): A new action (for example 'extend') could be added to the if/elif chain and to takes_value.
- **_OptionParser.allow_interspersed_args / ignore_unknown_options** (`src/click/parser.py:249`): Context flags that tune parsing. Plugins can set them via Context settings.

### Gaps (model's judgment, not verifiable from code)
- No abbreviation or prefix matching of long options (such as --verb for --verbose) Why plausible: _match_long_opt does an exact dict lookup. NoSuchOption already gets the possibilities list, so a unique-prefix lookup would fit in the same place. Nearest: `_OptionParser._match_long_opt`
- No 'extend' action and no per-option duplicate-use detection or error Why plausible: The actions are a fixed set. Repeated store options silently overwrite, though state.order already records repeats. Nearest: `_Option.process`
- No explicit '=' value support for short options (-o=val keeps '=' as part of the value) Why plausible: Short-cluster handling just pushes the remainder of the cluster as the value. Nearest: `_OptionParser._match_short_opt`
- Duplicate or conflicting option registration is not detected Why plausible: add_option silently overwrites existing entries in the dict. Nearest: `_OptionParser.add_option`

## Module card: `src/click/shell_completion.py`
src/click/shell_completion.py implements Click's shell completion. shell_complete() parses an instruction such as "bash_source" or "zsh_complete" from an env var. It looks up a ShellComplete subclass in the `_available_shells` registry. It then either prints the shell script (`source`) or the formatted completions (`complete`). Completion resolves a Context chain from the already-typed args (`_resolve_context`), picks the object that completes the incomplete word (`_resolve_incomplete`), and calls that object's `shell_complete(ctx, incomplete)`. That call returns a list of CompletionItem. Each shell subclass supplies a script template (`source_template`), env-var parsing (`get_completion_args`) and an output wire format (`format_completion`). Wire formats: bash and fish use "type,value" lines (fish adds a tab and help), while zsh and powershell use 3-line "type\nvalue\nhelp" records with "_" as the no-help sentinel. Custom shells can be registered with add_completion_class.

### Interfaces
- **`shell_complete`** (`src/click/shell_completion.py:19-55`)
  - Signature: `def shell_complete(cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, complete_var: str, instruction: str) -> t.Literal[0, 1]`
  - Behavior: Entry point (line 19). Splits `instruction` with partition('_') into shell and instruction. Looks up the class with get_completion_class, instantiates it as comp_cls(cli, ctx_args, prog_name, complete_var), and returns 0 or 1. 'source' echoes comp.source() as encoded bytes with nl=False. 'complete' echoes comp.complete() as encoded bytes, with a trailing newline. Bytes are written so Windows does not turn LF into CRLF.
  - Edge case: Unknown shell returns 1
  - Edge case: Unknown instruction returns 1
  - Edge case: Instruction without '_' gives shell=whole string and instruction='' so it returns 1 (or 1 for unknown shell)
  - Edge case: The shell name is the part before the first underscore, so registered names containing '_' can never match
- **`CompletionItem`** (`src/click/shell_completion.py:67-101`)
  - Signature: `class CompletionItem(t.Generic[_ValueT_co])  # __init__(self, value: _ValueT_co, type: str='plain', help: str | None=None, **kwargs: t.Any)`
  - Behavior: Generic class with __slots__ value, type, help, _info (line 67). Defaults: type='plain', help=None. Extra **kwargs are kept in _info and read as attributes through __getattr__.
  - Edge case: Unknown attribute returns None instead of raising AttributeError
  - Edge case: type values the built-in shell scripts handle: plain, dir, file; any other type is ignored by the bash, fish and powershell scripts
- **`CompletionItem.__getattr__`** (`src/click/shell_completion.py:100-101`)
  - Signature: `def __getattr__(self, name: str) -> t.Any`
  - Behavior: Returns self._info.get(name), so missing metadata is None (line 100).
  - Edge case: Only called for attributes not found normally
- **`ShellComplete`** (`src/click/shell_completion.py:277-385`)
  - Signature: `class ShellComplete  # __init__(self, cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, complete_var: str)`
  - Behavior: Base class (line 277, versionadded 8.0). Holds cli, ctx_args, prog_name, complete_var. Subclasses must set the class vars `name` and `source_template`.
  - Edge case: get_completion_args and format_completion are abstract and raise NotImplementedError in the base class
  - Edge case: The base class can be used directly to call get_completions (tests do this)
  - Raises: `NotImplementedError`
- **`ShellComplete.__init__`** (`src/click/shell_completion.py:306-316`)
  - Signature: `def __init__(self, cli: Command, ctx_args: cabc.MutableMapping[str, t.Any], prog_name: str, complete_var: str) -> None`
  - Behavior: Stores cli, ctx_args (a mutable mapping), prog_name and complete_var (line 306).
  - Edge case: ctx_args is later mutated by _resolve_context, which sets resilient_parsing=True
- **`ShellComplete.func_name`** (`src/click/shell_completion.py:319-324`)
  - Signature: `def func_name(self) -> str`
  - Behavior: Property (line 318). Replaces '-' with '_' in prog_name, strips non-word ASCII characters with re.sub(r'\W*', '', flags=re.ASCII), and returns f'_{safe}_completion'.
  - Edge case: A prog_name with only symbols gives '__completion'
- **`ShellComplete.source_vars`** (`src/click/shell_completion.py:326-336`)
  - Signature: `def source_vars(self) -> _SourceVarsDict`
  - Behavior: Returns the dict used to format source_template (line 326), with keys complete_func (func_name), complete_var and prog_name.
  - Edge case: Subclasses can add keys, though the _SourceVarsDict TypedDict only declares three
- **`ShellComplete.source`** (`src/click/shell_completion.py:338-344`)
  - Signature: `def source(self) -> str`
  - Behavior: Returns source_template % source_vars() (line 338).
  - Edge case: A literal '%' in a custom template must be written as '%%', otherwise the formatting fails
  - Edge case: The result is encoded and written without a trailing newline by shell_complete
  - Raises (unconfirmed, likely via a helper): `KeyError`, `TypeError`, `ValueError`
- **`ShellComplete.get_completion_args`** (`src/click/shell_completion.py:346-351`)
  - Signature: `def get_completion_args(self) -> tuple[list[str], str]`
  - Behavior: Abstract (line 346). Must return (args, incomplete) read from env vars.
  - Raises: `NotImplementedError`
- **`ShellComplete.get_completions`** (`src/click/shell_completion.py:353-365`)
  - Signature: `def get_completions(self, args: list[str], incomplete: str) -> list[CompletionItem[str]]`
  - Behavior: Line 353. Calls _resolve_context, then _resolve_incomplete, then obj.shell_complete(ctx, incomplete). Returns a list of CompletionItem.
  - Edge case: Empty incomplete is allowed
  - Edge case: args may be mutated by _resolve_incomplete (an '--opt=value' split appends the option name)
- **`ShellComplete.format_completion`** (`src/click/shell_completion.py:367-373`)
  - Signature: `def format_completion(self, item: CompletionItem[str]) -> str`
  - Behavior: Abstract (line 367). Turns one CompletionItem into the shell wire string.
  - Raises: `NotImplementedError`
- **`ShellComplete.complete`** (`src/click/shell_completion.py:375-385`)
  - Signature: `def complete(self) -> str`
  - Behavior: Line 375. Calls get_completion_args, then get_completions, then format_completion on each item. Joins the results with '\n'.
  - Edge case: No completions gives an empty string; shell_complete's echo then still adds a newline
  - Edge case: The result has no trailing newline of its own, since echo adds one
- **`BashComplete`** (`src/click/shell_completion.py:388-444`)
  - Signature: `class BashComplete(ShellComplete)`
  - Behavior: name='bash', template _SOURCE_BASH (line 388). The script runs `env COMP_WORDS=... COMP_CWORD=... VAR=bash_complete $1`, then handles types: dir sets compopt -o dirnames, file sets compopt -o default, plain appends to COMPREPLY. The script registers with `complete -o nosort`, which needs Bash >= 4.4.
  - Edge case: The bash script ignores item.help
- **`BashComplete._check_version`** (`src/click/shell_completion.py:395-425`)
  - Signature: `def _check_version() -> None`
  - Behavior: Static method (line 394). Finds bash with shutil.which and runs `bash --norc -c 'echo ${BASH_VERSION}'`. Prints a translated warning to stderr if the version is below 4.4, or if bash is not found or the version can't be parsed.
  - Edge case: Never aborts; it only warns on stderr
  - Edge case: The version comparison is done on strings, so '10' < '4' is True (a bug for major versions >= 10)
  - Edge case: Tests monkeypatch it
- **`BashComplete.source`** (`src/click/shell_completion.py:427-429`)
  - Signature: `def source(self) -> str`
  - Behavior: Calls _check_version(), then super().source() (line 427).
  - Edge case: Runs a subprocess on every source call
- **`BashComplete.get_completion_args`** (`src/click/shell_completion.py:431-441`)
  - Signature: `def get_completion_args(self) -> tuple[list[str], str]`
  - Behavior: Line 431. Splits env COMP_WORDS with split_arg_string. cword=int(env COMP_CWORD). args=cwords[1:cword]. incomplete=cwords[cword], or '' on IndexError.
  - Edge case: A missing env var raises KeyError
  - Edge case: A non-integer COMP_CWORD raises ValueError
  - Raises (unconfirmed, likely via a helper): `KeyError`, `ValueError`
- **`BashComplete.format_completion`** (`src/click/shell_completion.py:443-444`)
  - Signature: `def format_completion(self, item: CompletionItem[t.Any]) -> str`
  - Behavior: Returns f'{type},{value}' (line 443). The help text is dropped.
  - Edge case: A value containing a comma or newline is not escaped; the script does `IFS=',' read type value`, which keeps the rest of the line in value
- **`ZshComplete`** (`src/click/shell_completion.py:447-476`)
  - Signature: `class ZshComplete(ShellComplete)`
  - Behavior: name='zsh', template _SOURCE_ZSH (line 447). The script uses _describe for items with help and compadd for items without. It is frozen for backwards compatibility, so changes go into format_completion.
- **`ZshComplete.format_completion`** (`src/click/shell_completion.py:465-476`)
  - Signature: `def format_completion(self, item: CompletionItem[str]) -> str`
  - Behavior: Line 465. help_ = item.help or '_'. Escapes ':' as '\:' in the value only when help is present (not '_'). Returns 'type\nvalue\nhelp'.
  - Edge case: A real help text of '_' is treated as no help
  - Edge case: A multi-line help is not sanitized
- **`ZshComplete.get_completion_args`** (`src/click/shell_completion.py:453-463`)
  - Signature: `def get_completion_args(self) -> tuple[list[str], str]`
  - Behavior: Same as BashComplete: COMP_WORDS and COMP_CWORD, args=cwords[1:cword] (line 453).
  - Edge case: Missing env var raises KeyError
  - Edge case: Non-integer COMP_CWORD raises ValueError
  - Raises (unconfirmed, likely via a helper): `KeyError`, `ValueError`
- **`FishComplete`** (`src/click/shell_completion.py:479-513`)
  - Signature: `class FishComplete(ShellComplete)`
  - Behavior: name='fish', template _SOURCE_FISH (line 479). get_completion_args (line 485) reads COMP_WORDS (the whole command line) and COMP_CWORD (the current token, not an index). The incomplete word is split_arg_string(COMP_CWORD)[0] when non-empty. args=cwords[1:], and the last element is popped if it equals incomplete.
  - Edge case: COMP_CWORD='' gives an empty incomplete
  - Edge case: A quoted partial word is unquoted
  - Edge case: A missing env var raises KeyError
  - Raises (unconfirmed, likely via a helper): `KeyError`
- **`FishComplete.format_completion`** (`src/click/shell_completion.py:499-513`)
  - Signature: `def format_completion(self, item: CompletionItem[str]) -> str`
  - Behavior: Line 499. With help: 'type,value\thelp', where newlines in the help become literal backslash-n and tabs become spaces. Without help: 'type,value'.
  - Edge case: An empty help string is treated as no help
- **`PowerShellComplete`** (`src/click/shell_completion.py:516-547`)
  - Signature: `class PowerShellComplete(ShellComplete)`
  - Behavior: name='powershell', template _SOURCE_POWERSHELL (line 516, versionadded 8.5.0). The template uses Register-ArgumentCompleter -Native and parses the output 3 lines at a time. Types: plain gives a CompletionResult with a tooltip; dir and file use Get-ChildItem with a prefix glob.
  - Edge case: The prefix for dir/file is wordToComplete+'*'
- **`PowerShellComplete.format_completion`** (`src/click/shell_completion.py:537-547`)
  - Signature: `def format_completion(self, item: CompletionItem[str]) -> str`
  - Behavior: Line 537. Same 3-line format as zsh. Help has \r and \n replaced by spaces ('_' if no help). The value is not escaped.
  - Edge case: CRLF becomes two spaces
  - Edge case: A value containing a newline would break the framing
- **`PowerShellComplete.get_completion_args`** (`src/click/shell_completion.py:525-535`)
  - Signature: `def get_completion_args(self) -> tuple[list[str], str]`
  - Behavior: Same logic as Bash and Zsh (line 525).
  - Edge case: Missing env var raises KeyError
  - Raises (unconfirmed, likely via a helper): `KeyError`, `ValueError`
- **`add_completion_class`** (`src/click/shell_completion.py:560-577`)
  - Signature: `def add_completion_class(cls: type[_ShellCompleteT], name: str | None=None) -> type[_ShellCompleteT]`
  - Behavior: Registers cls in the module-level `_available_shells` under name or cls.name and returns cls, so it works as a decorator (line 560).
  - Edge case: Overwrites an existing entry silently
  - Edge case: No validation of the name
  - Edge case: If name is None and the class has no `name` attribute, AttributeError is raised
  - Raises (unconfirmed, likely via a helper): `AttributeError`
- **`get_completion_class`** (`src/click/shell_completion.py:588-595`)
  - Signature: `def get_completion_class(shell: str) -> type[ShellComplete] | None`
  - Behavior: Dict lookup in _available_shells (line 588). It has typing overloads for 'bash', 'fish' and 'zsh' only (no powershell overload).
  - Edge case: Unknown name returns None
- **`split_arg_string`** (`src/click/shell_completion.py:598-631`)
  - Signature: `def split_arg_string(string: str) -> list[str]`
  - Behavior: Line 598. A shlex.shlex posix=True, whitespace_split=True, commenters='' split. On ValueError (unclosed quote or trailing escape) it appends lex.token as the partial token. Moved here from parser in 8.2.
  - Edge case: Unclosed quote keeps the partial token without the quote
  - Edge case: Trailing backslash is dropped
  - Edge case: Empty string gives []

### Error conventions
The module has no custom exception types. shell_complete signals failure through a return code of 1, with no message. The bash version check prints translated messages to stderr with echo(err=True) and does not raise; the messages are sentences with no 'Error:' prefix. The abstract methods raise bare NotImplementedError. Bad environment variables (missing COMP_WORDS or COMP_CWORD, or a non-integer COMP_CWORD) surface as raw KeyError or ValueError from os.environ and int(). The completion code assumes make_context runs with resilient_parsing=True, so Click usage errors are suppressed during resolution.

### Examples
Base ShellComplete used to get completions directly in tests (`tests/test_shell_completion.py:24-26`)
```
def _get_completions(cli, args, incomplete):
    comp = ShellComplete(cli, {}, cli.name, "_CLICK_COMPLETE")
    return comp.get_completions(args, incomplete)
```
Option name completion hides options already used (`tests/test_shell_completion.py:34-40`)
```
cli = Command("cli", params=[Option(["-t", "--test"])])
assert _get_words(cli, [], "-") == ["-t", "--test", "--help"]
assert _get_words(cli, ["-t", "a"], "-") == ["--help"]
```
Registering a custom shell by decorator (`tests/test_shell_completion.py:566-569`)
```
@add_completion_class
class MyshComplete(ShellComplete):
    name = "mysh"
    source_template = "dummy source"
```
Full complete via env var instruction (`tests/test_shell_completion.py:388-390`)
```
cli = Group("cli", commands=[Command("a"), Command("b", help="bee")])
env["_CLI_COMPLETE"] = f"{shell}_complete"
result = runner.invoke(cli, env=env)
```
CompletionItem arbitrary metadata (`tests/test_shell_completion.py:337-339`)
```
c = CompletionItem("test", a=1)
assert c.a == 1
assert c.b is None
```

### Tests
- `tests/test_shell_completion.py`: Plain pytest asserts. Most tests call a local helper that builds ShellComplete(cli, {}, name, '_CLICK_COMPLETE') and compare the list of .value strings from get_completions. Cases covered: groups, chained groups, options, arguments, nargs, `--`, hidden params, Choice, Path and File types, and context_settings. The end-to-end tests use the `runner` fixture with env={'_CLI_COMPLETE': '<shell>_source|complete', COMP_WORDS, COMP_CWORD} and compare result.output exactly or by substring. BashComplete._check_version is monkeypatched out. Registry tests use a fixture that saves, clears and restores `_available_shells`. Other tests check the LF-only line endings of source output, zsh colon escaping, fish and PowerShell help escaping via format_completion, and no ResourceWarning from unclosed files. Some of these tests I saw only by name, not in full.

### Extension points
- **_available_shells / add_completion_class** (`src/click/shell_completion.py:560`): Register new ShellComplete subclasses (for example nushell, elvish or tcsh) with a name, a source_template, and get_completion_args and format_completion implementations.
- **ShellComplete.source_vars** (`src/click/shell_completion.py:326`): Override to add template variables, or to tweak the generated script per class.
- **ShellComplete.format_completion** (`src/click/shell_completion.py:367`): Override to change the wire format, for example escaping values or passing the CompletionItem's extra metadata to a custom shell script.
- **ShellComplete.get_completions** (`src/click/shell_completion.py:353`): Override to filter, sort or post-process the CompletionItem list before formatting.
- **CompletionItem type/kwargs** (`src/click/shell_completion.py:88`): New item types (beyond plain, dir, file) or extra kwargs, used by custom type completions and a matching custom shell script.
- **_resolve_incomplete** (`src/click/shell_completion.py:752`): Dispatch point that picks the Command or Parameter whose shell_complete(ctx, incomplete) is called. Custom Parameter, Command or ParamType shell_complete methods plug in here.
- **source_template class var** (`src/click/shell_completion.py:296`): Replace the script text on a subclass, for example to extend the bash script to use help text.

### Gaps (model's judgment, not verifiable from code)
- Bash script ignores help text and CompletionItem.help. There is no descriptive completion for bash. Why plausible: The bash wire format already carries only type and value, but the other shells carry help. Bash 5.x can show descriptions through a custom display approach. Nearest: `BashComplete.format_completion`
- Value escaping is inconsistent. Bash and PowerShell values containing commas or newlines are not escaped, and zsh help is not newline-sanitized. Why plausible: Fish and PowerShell already sanitize help text, so the same treatment applies to zsh help and to values. Nearest: `ZshComplete.format_completion`
- get_completion_class has no typing overload for 'powershell'. The Bash version check compares version strings lexicographically and breaks for majors >= 10. Why plausible: Small fixes that follow the existing patterns. Nearest: `get_completion_class`
- No auto-detection of the shell, and no built-in install command that writes the script to the shell's rc or completions directory. Why plausible: The `source` instruction already produces the script, so a helper could wrap it for the user. Nearest: `shell_complete`
- Env var parsing failures (KeyError or ValueError) are not handled gracefully in get_completion_args. Why plausible: Shell scripts could be invoked incorrectly, and a clean exit code would be friendlier. Nearest: `ShellComplete.get_completion_args`

## Module card: `src/click/termui.py`
src/click/termui.py holds Click's interactive and terminal helpers. It has prompt/confirm built on a swappable `visible_prompt_func` (input) and `hidden_prompt_func` (getpass). It also has ANSI style/unstyle/secho, and thin lazy wrappers over `_termui_impl` (progressbar, edit, launch, getchar, raw_terminal, pager). It also has clear and pause. Prompts go through `_readline_prompt`, which passes the full prompt text to the input function so readline works. It strips ANSI itself when the stream doesn't support color.

### Interfaces
- **`prompt`** (`src/click/termui.py:168-286`)
  - Signature: `def prompt(text: str, default: V | str | None=None, hide_input: bool=False, confirmation_prompt: bool | str=False, type: ParamType[V, str] | type[V] | None=None, value_proc: t.Callable[[str], V] | None=None, prompt_suffix: str=': ', show_default: bool | str=True, err: bool=False, show_choices: bool=True) -> V`
  - Behavior: Builds the prompt via _build_prompt (text, then ' (choices)' if type is a Choice and show_choices, then ' [default]' if show_default, then prompt_suffix default ': '). If value_proc is None it uses convert_type(type, default). Loops reading input via hidden_prompt_func if hide_input, else visible_prompt_func. Empty input returns the default if default is not None, otherwise it re-prompts forever. The default is cast and passed through value_proc like typed input. A UsageError from value_proc prints 'Error: <message>' (via echo, to stderr if err) and re-prompts. With hide_input the message is masked via _mask_hidden_input. confirmation_prompt (True gives 'Repeat for confirmation', or a custom string) asks a second time. A mismatch prints 'Error: The two entered values do not match.' and restarts. If both are empty, confirmation is accepted.
  - Edge case: show_default as str shows ' [(str)]' instead of the value
  - Edge case: default of None with empty input re-prompts
  - Edge case: File defaults are shown by name via _format_default
  - Edge case: KeyboardInterrupt/EOFError become Abort; with hide_input a newline is echoed first
  - Edge case: empty confirmation re-asks unless the first value was also empty
  - Raises: `Abort`
- **`confirm`** (`src/click/termui.py:289-345`)
  - Signature: `def confirm(text: str, default: bool | None=False, abort: bool=False, prompt_suffix: str=': ', show_default: bool=True, err: bool=False) -> bool`
  - Behavior: Yes/no prompt. The suffix is '[Y/n]', '[y/N]' or '[y/n]' depending on default (True, False, None), shown only if show_default. Input is lowercased and stripped. y/yes gives True, n/no gives False, and empty returns default when it is not None. Anything else echoes 'Error: invalid input' and re-asks. If abort=True a negative answer raises Abort.
  - Edge case: default=None repeats until a valid answer
  - Edge case: EOF/KeyboardInterrupt raise Abort
  - Raises: `Abort`
- **`hidden_prompt_func`** (`src/click/termui.py:79-82`)
  - Signature: `def hidden_prompt_func(prompt: str) -> str`
  - Behavior: Imports getpass lazily and returns getpass.getpass(prompt). It is a module-level hook that tests and doc tools monkeypatch.
- **`get_pager_file`** (`src/click/termui.py:348-364`)
  - Signature: `def get_pager_file(color: bool | None=None) -> t.ContextManager[t.TextIO]`
  - Behavior: Resolves color with resolve_color_default, then delegates to _termui_impl.get_pager_file(color=...). It returns a context manager yielding a writable text file for the pager (new in 8.4.0).
  - Edge case: color=None means autodetect
- **`echo_via_pager`** (`src/click/termui.py:367-399`)
  - Signature: `def echo_via_pager(text_or_generator: cabc.Iterable[str] | t.Callable[[], cabc.Iterable[str]] | str, color: bool | None=None) -> None`
  - Behavior: Accepts a str, an iterable, or a generator function (called with no args). A str becomes a one-item list. Each element is coerced to str. Writes via get_pager_file, flushing after each write, and appends a final '\n' (chained as an iterable of characters).
  - Edge case: non-str elements are str()'d
  - Edge case: only generator functions, not other callables, are called
- **`progressbar`** (`src/click/termui.py:443-599`)
  - Signature: `def progressbar(iterable: cabc.Iterable[V] | None=None, length: int | None=None, label: str | None=None, hidden: bool=False, show_eta: bool=True, show_percent: bool | None=None, show_pos: bool=False, item_show_func: t.Callable[[V | None], str | None] | None=None, fill_char: str='#', empty_char: str='-', bar_template: str='%(label)s  [%(bar)s]  %(info)s', info_sep: str='  ', width: int=36, file: t.TextIO | None=None, color: bool | None=None, update_min_steps: int=1) -> ProgressBar[V]`
  - Behavior: Resolves color, then builds and returns _termui_impl.ProgressBar with all args forwarded. It is used as a context manager and iterable. Defaults: show_eta=True, fill '#', empty '-', template '%(label)s  [%(bar)s]  %(info)s', info_sep two spaces, width 36 (0 means full terminal width), update_min_steps=1. The overloads require length when there is no iterable. If the file is not a TTY only the label is printed, and hidden=True suppresses even that.
  - Edge case: item_show_func may receive None
  - Edge case: show_percent defaults to True only if the length is known
- **`clear`** (`src/click/termui.py:602-613`)
  - Signature: `def clear() -> None`
  - Behavior: If stdout is a TTY, echoes '\033[2J\033[1;1H' with nl=False. Otherwise it does nothing.
  - Edge case: no-op when not a TTY
- **`style`** (`src/click/termui.py:641-765`)
  - Signature: `def style(text: t.Any, fg: int | tuple[int, int, int] | str | None=None, bg: int | tuple[int, int, int] | str | None=None, bold: bool | None=None, dim: bool | None=None, underline: bool | None=None, overline: bool | None=None, italic: bool | None=None, blink: bool | None=None, reverse: bool | None=None, strikethrough: bool | None=None, reset: bool=True) -> str`
  - Behavior: Converts non-str text with str(). Builds ANSI codes in this order: fg, bg (offset 10), bold, dim, underline, overline, italic, blink, reverse, strikethrough. Each flag None is skipped, True turns it on, False emits the off code (22, 24, 55, 23, 25, 27, 29). Appends the text, then '\033[0m' if reset=True. Colors can be a name, an int 0-255 (8-bit), or an RGB tuple/list.
  - Edge case: bold=False and dim=False both emit 22
  - Edge case: reset=False allows composing styles
  - Edge case: bool colors are rejected
  - Raises: `ValueError`
- **`unstyle`** (`src/click/termui.py:768-777`)
  - Signature: `def unstyle(text: str) -> str`
  - Behavior: Returns strip_ansi(text) with ANSI codes removed.
- **`secho`** (`src/click/termui.py:780-811`)
  - Signature: `def secho(message: t.Any | None=None, file: t.IO[t.AnyStr] | None=None, nl: bool=True, err: bool=False, color: bool | None=None, **styles: t.Any) -> None`
  - Behavior: Calls style(message, **styles) unless message is None or bytes/bytearray, then echo(message, file, nl, err, color). Bytes skip styling. Style kwargs are forwarded to style, so a bad kwarg raises TypeError and a bad color raises ValueError.
  - Edge case: None message goes to echo unstyled (prints a blank line)
  - Edge case: unknown style kwarg raises TypeError from style()
  - Raises (unconfirmed, likely via a helper): `ValueError`, `TypeError`
- **`edit`** (`src/click/termui.py:848-920`)
  - Signature: `def edit(text: str | bytes | bytearray | None=None, editor: str | None=None, env: cabc.Mapping[str, str] | None=None, require_save: bool=True, extension: str='.txt', filename: str | os.PathLike[str] | cabc.Iterable[str | os.PathLike[str]] | None=None) -> str | bytes | bytearray | None`
  - Behavior: Builds _termui_impl.Editor(editor, env, require_save, extension). With filename=None it returns ed.edit(text). Otherwise a str or PathLike is wrapped in a tuple and ed.edit_files is called, returning None. The overloads give require_save default False for bytes and True for str. Per the docstring, a UsageError is raised if the editor cannot be opened (raised inside Editor, not read here).
  - Edge case: returns None if unchanged and require_save
  - Edge case: filename makes text, require_save and extension irrelevant
- **`launch`** (`src/click/termui.py:923-949`)
  - Signature: `def launch(url: str, wait: bool=False, locate: bool=False) -> int`
  - Behavior: Delegates to _termui_impl.open_url(url, wait, locate) and returns the exit code (0 usually means success). locate=True opens a file manager at the file.
  - Edge case: xdg-open does not block even with wait=True
- **`getchar`** (`src/click/termui.py:957-984`)
  - Signature: `def getchar(echo: bool=False) -> str`
  - Behavior: Lazily imports and caches _termui_impl.getchar in the module global _getchar, then calls it with echo (default False). Tests set click.termui._getchar to override it.
  - Edge case: may return more than one character
  - Edge case: reads from the terminal even if stdin is piped
- **`raw_terminal`** (`src/click/termui.py:987-990`)
  - Signature: `def raw_terminal() -> AbstractContextManager[int]`
  - Behavior: Returns the context manager from _termui_impl.raw_terminal() (yields an int). It has no docstring.
- **`pause`** (`src/click/termui.py:993-1024`)
  - Signature: `def pause(info: str | None=None, err: bool=False) -> None`
  - Behavior: Returns immediately unless both stdin and stdout are TTYs. Default info is 'Press any key to continue...'. Echoes the info with nl=False, calls getchar(), and swallows KeyboardInterrupt/EOFError. In a finally block it echoes a newline if info is truthy. info='' prints nothing.
  - Edge case: no-op when not interactive
  - Edge case: empty info means no message and no newline
- **`_readline_prompt`** (`src/click/termui.py:85-105`)
  - Signature: `def _readline_prompt(func: t.Callable[[str], str], text: str, err: bool) -> str`
  - Behavior: Private helper that picks stderr or stdout. It strips ANSI from the text if _compat.should_strip_ansi(stream, resolve_color_default()) is true; this is looked up on the module so CliRunner's patch applies. It calls func(text), wrapped in redirect_stdout(sys.stderr) when err=True.
- **`_build_prompt`** (`src/click/termui.py:108-125`)
  - Signature: `def _build_prompt(text: str, suffix: str, show_default: bool | str=False, default: object | None=None, show_choices: bool=True, type: object | None=None) -> str`
  - Behavior: Private helper that assembles the prompt string from text, choices, a default preview and the suffix. It is also used by confirm with a 'y/n' style pseudo-default.
- **`_mask_hidden_input`** (`src/click/termui.py:61-76`)
  - Signature: `def _mask_hidden_input(message: str, value: str) -> str`
  - Behavior: Replaces repr(value) and the raw value (word-boundary regex, skipped when value is empty) in an error message with "'***'" so hidden input doesn't leak.
  - Edge case: empty value skips the raw pass
- **`_interpret_color`** (`src/click/termui.py:616-638`)
  - Signature: `def _interpret_color(color: int | tuple[int, int, int] | str, offset: int=0) -> str`
  - Behavior: Private helper that maps a color name, int 0-255 or 3-int tuple/list to an SGR parameter string. The offset (10 for bg) is added to named colors and applied to 38 for 8-bit and RGB colors.
  - Edge case: bools rejected
  - Edge case: out-of-range ints and bad tuples raise ValueError
  - Raises: `ValueError`

### Error conventions
Abort is raised for user interrupt/EOF, or for a declined confirm(abort=True). UsageError from type conversion is caught inside prompt and shown as the message 'Error: <message>' (gettext-wrapped), followed by a re-prompt. confirm prints 'Error: invalid input'. The confirmation mismatch message is 'Error: The two entered values do not match.' ValueError('Unknown color {colour!r}') is raised for bad colors. UsageError for editor failures comes from _termui_impl, not this file. Errors are written with echo(err=err).

### Examples
Default round-trips through type (`tests/test_utils/test_prompt.py:11-12`)
```
monkeypatch.setattr(sys, "stdin", StringIO("\n"))
value = click.prompt("value", default="100", type=int)
```
Docstring example of styling (`src/click/termui.py:662-665`)
```
click.echo(click.style('Hello World!', fg='green'))
click.echo(click.style('More colors', fg=(255, 12, 128), bg=117))
```
Manual progress bar update (`src/click/termui.py:495-498`)
```
with progressbar(length=chunks.total_bytes) as bar:
    for chunk in chunks:
        process_chunk(chunk)
        bar.update(chunks.bytes)
```
Test that the full prompt text is passed to the input function (`tests/test_utils/test_prompt.py:81-83`)
```
monkeypatch.setattr("click.termui.visible_prompt_func", capture)
call()
assert received == [expected_prompt]
```

### Tests
- `tests/test_utils/test_prompt.py`: Six tests. Stdin is replaced via monkeypatch with StringIO. Others patch click.termui.visible_prompt_func/hidden_prompt_func to capture the prompt text, and compare it to the expected string with a plain assert. They check that defaults go through type conversion and validation, that Abort is raised on KeyboardInterrupt (output equals '\ninterrupted\n' via capsys), and that EOF gives exit_code 1 through runner.invoke. Some are skipped on Windows.
- `tests/test_termui.py`: Uses the runner fixture with input= and checks result.output/exit_code. Progressbar tests monkeypatch click._termui_impl.isatty and the time function, and compare the rendered output. getchar tests patch msvcrt and reset click.termui._getchar to None. Pager tests use capfd with a real pager command. Option-prompt tests check the output text, for example the choices list or 'file [path]: '.

### Extension points
- **visible_prompt_func** (`src/click/termui.py:34`): Replace input() for custom, testing or doc-tool prompt readers. Its signature is Callable[[str], str].
- **hidden_prompt_func** (`src/click/termui.py:79`): Monkeypatch this to swap the password reader.
- **prompt value_proc / type parameters** (`src/click/termui.py:168`): A custom ParamType or value_proc callable that raises UsageError for validation with retry.
- **_ansi_colors** (`src/click/termui.py:36`): Dict of named colors; new named colors or aliases could be added here and would be accepted by style.
- **_getchar** (`src/click/termui.py:954`): Override hook for getchar (used by tests).
- **progressbar item_show_func/bar_template** (`src/click/termui.py:443`): Custom per-item text and bar layout.
- **get_pager_file** (`src/click/termui.py:348`): Streaming pager writes; custom pager integrations.

### Gaps (model's judgment, not verifiable from code)
- No re-prompt limit or max attempts for prompt/confirm; invalid input loops forever until Abort or EOF. Why plausible: Scripts and tests would benefit from a bounded retry count. Nearest: `prompt`
- confirm has no custom yes/no word sets or localization of accepted answers; it accepts only y/yes/n/no. Why plausible: The error and prompt strings are already gettext-wrapped. Nearest: `confirm`
- style has no named-style or theme registry, and no named 'bright_*' aliases for bg handling beyond the table; there is also no combined 'styles' dict helper. Why plausible: The secho **styles pass-through suggests a reusable style bundle. Nearest: `style`
- No single-choice menu or selection helper (numbered choices) beyond Choice shown in the prompt text. Why plausible: prompt already renders Choice and validates it. Nearest: `prompt`

## Module card: `src/click/exceptions.py`
src/click/exceptions.py defines Click's exception hierarchy. ClickException (exit_code 1) is the base for user-facing errors. It has format_message() and show(). UsageError (exit_code 2) prints usage and a help hint. Its subclasses are BadParameter, MissingParameter, NoSuchOption, NoSuchCommand, BadOptionUsage, BadArgumentUsage and NoArgsIsHelpError. FileError is a direct ClickException subclass. Abort and Exit are NOT ClickExceptions: they derive from RuntimeError and are control-flow signals. Command.main in core.py (about lines 1571-1612) catches them. In standalone mode it calls e.show and sys.exit(e.exit_code). In non-standalone mode it re-raises ClickException and Abort, and returns Exit.exit_code.

### Interfaces
- **`ClickException`** (`src/click/exceptions.py:35-65`)
  - Signature: `class ClickException(Exception)  # __init__(self, message: str)`
  - Behavior: Base class (line 35). __init__(message) calls Exception.__init__, caches show_color = resolve_color_default() at construction (the context is gone by the time show runs), and stores message. Class attribute exit_code = 1. format_message() returns self.message. __str__ returns self.message. show(file=None) writes 'Error: {message}' via echo to file, or to get_text_stderr() if file is None, using the cached show_color.
  - Edge case: file=None means stderr
  - Edge case: message is not validated, so a non-str message would break __str__
- **`ClickException.format_message`** (`src/click/exceptions.py:51-52`)
  - Signature: `def format_message(self) -> str`
  - Behavior: Returns self.message. Subclasses override it to decorate the message. show() uses it.
- **`ClickException.show`** (`src/click/exceptions.py:57-65`)
  - Signature: `def show(self, file: t.IO[t.Any] | None=None) -> None`
  - Behavior: Prints 'Error: <format_message()>' to the given file or to stderr. Color comes from the value cached at construction.
  - Edge case: file None -> stderr
- **`UsageError`** (`src/click/exceptions.py:68-111`)
  - Signature: `class UsageError(ClickException)  # __init__(self, message: str, ctx: Context | None=None)`
  - Behavior: Line 68. exit_code = 2. __init__(message, ctx=None) stores ctx and sets cmd = ctx.command if ctx else None. show() prints, in order: ctx.get_usage(), then a "Try '<command_path> <longest help option name>' for help." line only if the command has a help option, then 'Error: <message>'. Color comes from ctx.color. Without a ctx it prints only the Error line, with color=None.
  - Edge case: ctx None -> no usage and no hint
  - Edge case: help option disabled (get_help_option returns None) -> no hint
  - Edge case: longest help name is chosen with max(key=len)
- **`UsageError.show`** (`src/click/exceptions.py:87-111`)
  - Signature: `def show(self, file: t.IO[t.Any] | None=None) -> None`
  - Behavior: Prints usage, the optional help hint, then 'Error: ...' to file or stderr. Uses ctx.color, not the cached show_color.
  - Edge case: ctx None
  - Edge case: no help option
- **`BadParameter`** (`src/click/exceptions.py:114-156`)
  - Signature: `class BadParameter(UsageError)  # __init__(self, message: str, ctx: Context | None=None, param: Parameter | None=None, param_hint: cabc.Sequence[str] | str | None=None)`
  - Behavior: Line 114. __init__(message, ctx=None, param=None, param_hint=None). format_message() uses param_hint if it is not None. Otherwise it uses param.get_error_hint(ctx). If neither is set it returns 'Invalid value: {message}'. Otherwise it returns 'Invalid value for {hint}: {message}'. A sequence hint is joined with ' / ' with each item repr-quoted (_join_param_hints). A str hint is used as-is.
  - Edge case: both param and param_hint -> param_hint wins
  - Edge case: neither set -> 'Invalid value: msg'
  - Edge case: empty-list hint -> empty string
- **`BadParameter.format_message`** (`src/click/exceptions.py:146-156`)
  - Signature: `def format_message(self) -> str`
  - Behavior: Builds 'Invalid value for X: msg', or 'Invalid value: msg' when there is no hint and no param.
  - Edge case: see BadParameter
- **`MissingParameter`** (`src/click/exceptions.py:159-229`)
  - Signature: `class MissingParameter(BadParameter)  # __init__(self, message: str | None=None, ctx: Context | None=None, param: Parameter | None=None, param_hint: cabc.Sequence[str] | str | None=None, param_type: str | None=None)`
  - Behavior: Line 159. __init__(message=None, ctx=None, param=None, param_hint=None, param_type=None). A None message becomes ''. format_message builds 'Missing {argument|option|parameter|<custom>} {hint}.{ msg}'. param_type falls back to param.param_type_name. If param is set, param.type.get_missing_message(param, ctx) is appended to the message: joined with '. ' if the message is non-empty, used alone otherwise. An unknown param_type is formatted as 'Missing {param_type}'. __str__ returns the message, or 'Missing parameter: {param.name}' if the message is empty.
  - Edge case: empty message -> __str__ uses the param name, which is None if there is no param
  - Edge case: param_type None and no param -> 'Missing None'
  - Edge case: hint omitted -> no hint text
- **`MissingParameter.format_message`** (`src/click/exceptions.py:184-222`)
  - Signature: `def format_message(self) -> str`
  - Behavior: See MissingParameter. Translates the known param types and appends the type's missing message (for example a Choice lists its choices).
  - Edge case: unknown param_type
- **`MissingParameter.__str__`** (`src/click/exceptions.py:224-229`)
  - Signature: `def __str__(self) -> str`
  - Behavior: Returns self.message, or a 'Missing parameter: name' fallback when the message is empty.
  - Edge case: param None -> 'Missing parameter: None'
- **`NoSuchOption`** (`src/click/exceptions.py:232-265`)
  - Signature: `class NoSuchOption(UsageError)  # __init__(self, option_name: str, message: str | None=None, possibilities: cabc.Iterable[str] | None=None, ctx: Context | None=None)`
  - Behavior: Line 232. __init__(option_name, message=None, possibilities=None, ctx=None). The default message is "No such option 'x'." Possibilities are filtered with difflib.get_close_matches(option_name, possibilities) (default n=3, cutoff 0.6). format_message appends a sorted 'Did you mean ...?' suggestion (ngettext singular/plural) when matches exist. Stores option_name and possibilities (None when empty).
  - Edge case: falsy possibilities -> None
  - Edge case: no close match -> empty list, no suggestion
- **`NoSuchCommand`** (`src/click/exceptions.py:268-301`)
  - Signature: `class NoSuchCommand(UsageError)  # __init__(self, command_name: str, message: str | None=None, possibilities: cabc.Iterable[str] | None=None, ctx: Context | None=None)`
  - Behavior: Line 268, added in 8.4.0. Same pattern as NoSuchOption: command_name, default message "No such command 'x'.", fuzzy possibilities via difflib, and the same format_message suggestion.
  - Edge case: same as NoSuchOption
- **`BadOptionUsage`** (`src/click/exceptions.py:304-320`)
  - Signature: `class BadOptionUsage(UsageError)  # __init__(self, option_name: str, message: str, ctx: Context | None=None)`
  - Behavior: Line 304. __init__(option_name, message, ctx=None). A UsageError that stores option_name. It is raised when an option is used incorrectly, such as the wrong number of values.
- **`BadArgumentUsage`** (`src/click/exceptions.py:323-329`)
  - Signature: `class BadArgumentUsage(UsageError)`
  - Behavior: Line 323. UsageError subclass with no overrides. Raised when an argument is used incorrectly, such as the wrong number of values.
- **`NoArgsIsHelpError`** (`src/click/exceptions.py:332-339`)
  - Signature: `class NoArgsIsHelpError(UsageError)  # __init__(self, ctx: Context)`
  - Behavior: Line 332. __init__(ctx) calls super().__init__(ctx.get_help(), ctx=ctx), so the message is the full help text. show() echoes format_message() to stderr (err=True) with ctx.color, without the 'Error:' prefix or usage. It inherits exit_code 2.
  - Edge case: ctx is required
  - Edge case: show ignores a file argument's usage but passes file through to echo; err=True is used when file is None
- **`FileError`** (`src/click/exceptions.py:342-359`)
  - Signature: `class FileError(ClickException)  # __init__(self, filename: str, hint: str | None=None)`
  - Behavior: Line 342. __init__(filename, hint=None). A None hint becomes 'unknown error'. ui_filename = format_filename(filename) (surrogate-safe) and the raw filename is stored. format_message returns "Could not open file {ui_filename!r}: {message}". exit_code is inherited as 1.
  - Edge case: a surrogate filename renders as the replacement char U+FFFD
  - Edge case: hint None -> 'unknown error'
- **`FileError.format_message`** (`src/click/exceptions.py:356-359`)
  - Signature: `def format_message(self) -> str`
  - Behavior: Returns "Could not open file '<ui_filename>': <hint>".
  - Edge case: see FileError
- **`Abort`** (`src/click/exceptions.py:362-363`)
  - Signature: `class Abort(RuntimeError)`
  - Behavior: Line 362. A RuntimeError subclass, not a ClickException, with no custom attributes. In standalone mode, main prints 'Aborted!' (via _echo_aborted) and exits with code 1. In non-standalone mode it re-raises. KeyboardInterrupt and EOFError are converted into Abort in non-standalone mode.
- **`Exit`** (`src/click/exceptions.py:366-378`)
  - Signature: `class Exit(RuntimeError)  # __init__(self, code: int=0)`
  - Behavior: Line 366. A RuntimeError subclass with __slots__ ('exit_code',). __init__(code=0) sets exit_code. It does not call super().__init__. Context.exit raises it (core.py:831). In non-standalone mode main returns e.exit_code. In standalone mode it calls sys.exit(code).
  - Edge case: code is not validated
  - Edge case: default 0
  - Edge case: no message or args, so str(e) is empty

### Error conventions
ClickException subclasses are user-facing errors. main() prints them as 'Error: <msg>' and exits with exit_code. exit_code is 1 for ClickException and FileError, and 2 for UsageError and all its subclasses. UsageError, BadParameter, MissingParameter and the NoSuch*/BadOption* classes also print usage and a help hint when a ctx is attached. Abort and Exit are RuntimeError control-flow signals, not ClickExceptions. Message style is a capitalized sentence, usually ending with a period for the NoSuch* and Missing messages. User-visible strings go through gettext (_ and ngettext). Parameter names are quoted with repr, and multiple hints are joined with ' / '. Core also raises UsageError(message, ctx) from Context.fail (core.py:817) and Exit from Context.exit (core.py:831).

### Examples
Test: FileError message with a surrogate filename (`tests/test_exceptions/test_FileError.py:4-6`)
```
message = click.FileError(filename="\udcff").format_message()
assert message == "Could not open file '�': unknown error"
```
Docs: handling Click exceptions manually in non-standalone mode (`docs/exceptions.md:77-88`)
```
try:
    command.main(["command-name", "args", "go", "here"], standalone_mode=False)
except click.Abort:
    click.echo("Bye!", err=True)
    raise SystemExit(1)
except click.ClickException as e:
    e.show()
    raise SystemExit(e.exit_code)
```
Core dispatch of ClickException in main() (`src/click/core.py:1597-1601`)
```
except ClickException as e:
    if not standalone_mode:
        raise
    report, exit_code = e.show, e.exit_code
```

### Tests
- `tests/test_exceptions/test_FileError.py`: A single test, test_file_error_surrogates. It builds click.FileError(filename='\udcff') and compares format_message() to an exact string with the replacement character and 'unknown error'. Plain assert, no fixtures. This is the only test I read. Other exceptions are probably covered indirectly in tests/test_basic.py, test_arguments.py and similar files, which I did not check.

### Extension points
- **ClickException subclassing (override exit_code / format_message / show)** (`src/click/exceptions.py:35`): Custom user-facing errors: subclass ClickException, set exit_code, override format_message or show. Command.main handles them automatically (core.py:1597).
- **UsageError.show** (`src/click/exceptions.py:87`): Custom usage rendering, such as a different help hint or JSON output.
- **Command.main exception dispatch** (`src/click/core.py:1571`): A new handled exception type, or a global error reporter, added to the except chain.
- **_format_possibilities / difflib suggestions** (`src/click/exceptions.py:26`): Shared suggestion formatting that other 'did you mean' errors could reuse.

### Gaps (model's judgment, not verifiable from code)
- There is no exit-code override on the constructor, so a custom code needs a subclass. Why plausible: Exit already takes a code, so an optional exit_code argument is a small step. Nearest: `ClickException`
- There is no structured or machine-readable output, such as to_dict or JSON, for errors. Why plausible: Errors already carry param, option_name and possibilities as attributes. Nearest: `ClickException.show`
- There is no fuzzy-match tuning (n and cutoff are fixed to the difflib defaults) and no suggestions for BadParameter or Choice errors. Why plausible: NoSuchOption and NoSuchCommand duplicate the same possibilities logic, which could be factored out and parameterized. Nearest: `NoSuchOption`
- Abort carries no message and Exit carries no message, so there is no custom 'Aborted!' text. Why plausible: main prints a fixed 'Aborted!'. Nearest: `Abort`

## Module card: `src/click/formatting.py`
src/click/formatting.py holds click's in-memory help rendering. It has module helpers (measure_table, iter_rows, wrap_text, join_options), the HelpFormatter class, and a module global FORCED_WIDTH that CliRunner sets to 80 during invoke. wrap_text delegates to click._textwrap.TextWrapper and is ANSI-aware via term_len. HelpFormatter buffers strings and exposes write_usage, write_heading, write_text, write_dl and the section/indentation context managers. Context.make_formatter (core.py:638) builds it from terminal_width and max_content_width, and Context.formatter_class (core.py:315) is the subclass hook.

### Interfaces
- **`wrap_text`** (`src/click/formatting.py:31-107`)
  - Signature: `def wrap_text(text: str, width: int=78, initial_indent: str='', subsequent_indent: str='', preserve_paragraphs: bool=False) -> str`
  - Behavior: Expands tabs, then wraps with click._textwrap.TextWrapper (replace_whitespace=False). Defaults: width=78, no indents, preserve_paragraphs=False (single-paragraph wrap via wrapper.fill). With preserve_paragraphs=True, lines are grouped into paragraphs split on empty lines. The first line's leading indent (measured with term_len) is kept as an extra indent for the paragraph. A paragraph whose first line is just '\b' is emitted unwrapped via indent_only, with the \b line dropped. Other paragraphs have their lines joined with spaces and are filled. Paragraphs are joined with '\n\n'. Width is measured in visible characters, so ANSI escapes are ignored (versionchanged 8.4.0).
  - Edge case: empty text with preserve_paragraphs=True returns ''
  - Edge case: tabs expanded to 8 columns
  - Edge case: a '\b' paragraph keeps its internal newlines and relative indentation
  - Edge case: empty text without preserve_paragraphs returns '' and drops initial_indent (see the test comment at tests/test_formatting.py:520-522)
- **`measure_table`** (`src/click/formatting.py:14-21`)
  - Signature: `def measure_table(rows: cabc.Iterable[tuple[str, str]]) -> tuple[int, ...]`
  - Behavior: Takes an iterable of row tuples. Returns a tuple of the maximum term_len per column index, in column order.
  - Edge case: empty rows give ()
  - Edge case: rows of unequal length are handled per index
- **`iter_rows`** (`src/click/formatting.py:24-28`)
  - Signature: `def iter_rows(rows: cabc.Iterable[tuple[str, str]], col_count: int) -> cabc.Iterator[tuple[str, ...]]`
  - Behavior: Yields each row right-padded with '' up to col_count columns.
  - Edge case: rows already at col_count are unchanged
  - Edge case: rows longer than col_count are not truncated
- **`HelpFormatter`** (`src/click/formatting.py:110-299`)
  - Signature: `class HelpFormatter  # __init__(self, indent_increment: int=2, width: int | None=None, max_width: int | None=None)`
  - Behavior: Buffering formatter. __init__(indent_increment=2, width=None, max_width=None). max_width defaults to 80. If width is None it uses module FORCED_WIDTH, else max(min(terminal columns, max_width) - 2, 50). Starts with current_indent=0 and an empty buffer list.
  - Edge case: an explicit width bypasses the 50 minimum and FORCED_WIDTH
  - Edge case: the shutil import is lazy
- **`HelpFormatter.write`** (`src/click/formatting.py:146-148`)
  - Signature: `def write(self, string: str) -> None`
  - Behavior: Appends a raw string to self.buffer with no processing.
- **`HelpFormatter.indent`** (`src/click/formatting.py:150-152`)
  - Signature: `def indent(self) -> None`
  - Behavior: Adds indent_increment to current_indent.
- **`HelpFormatter.dedent`** (`src/click/formatting.py:154-156`)
  - Signature: `def dedent(self) -> None`
  - Behavior: Subtracts indent_increment from current_indent. There is no floor at 0.
  - Edge case: unbalanced dedent can make current_indent negative
- **`HelpFormatter.write_usage`** (`src/click/formatting.py:158-202`)
  - Signature: `def write_usage(self, prog: str, args: str='', prefix: str | None=None) -> None`
  - Behavior: Writes the usage line. The default prefix is gettext('Usage:') + ' '. The prefix is right-aligned in a field of current_indent characters, followed by 'prog '. If args is empty, only the prefix and prog are written with trailing spaces stripped, then '\n'. If text_width (width - current_indent) >= term_len(usage_prefix) + 20, args are wrapped to the right of the prefix with a hanging indent. Otherwise the prefix line is written alone and args go on following lines indented by max(current_indent, term_len(prefix)) + 4.
  - Edge case: empty args gives 'Usage: Program\n'
  - Edge case: a styled prefix is measured with term_len
  - Edge case: an explicit prefix='' is honoured because the check is `is None`
- **`HelpFormatter.write_heading`** (`src/click/formatting.py:204-206`)
  - Signature: `def write_heading(self, heading: str) -> None`
  - Behavior: Writes current_indent spaces, the heading, ':' and a newline.
  - Edge case: the colon is always appended
  - Edge case: the heading is not translated or wrapped
- **`HelpFormatter.write_paragraph`** (`src/click/formatting.py:208-211`)
  - Signature: `def write_paragraph(self) -> None`
  - Behavior: Writes '\n' only if the buffer is non-empty, so a blank line is never emitted first.
  - Edge case: no-op on an empty buffer
- **`HelpFormatter.write_text`** (`src/click/formatting.py:213-227`)
  - Signature: `def write_text(self, text: str) -> None`
  - Behavior: Wraps text at self.width with initial and subsequent indent equal to current_indent spaces, with preserve_paragraphs=True (so \b blocks work), then writes a trailing newline.
  - Edge case: empty text writes '\n' only, or the indent plus newline depending on wrapper behaviour
- **`HelpFormatter.write_dl`** (`src/click/formatting.py:229-271`)
  - Signature: `def write_dl(self, rows: cabc.Iterable[tuple[str, str]], col_max: int=30, col_spacing: int=2) -> None`
  - Behavior: Writes a definition list. col_max=30 and col_spacing=2 are the defaults. rows is materialised with list(). The first column width is min(max term_len, col_max) + col_spacing. If the term fits it is padded, otherwise the description starts on the next line at first_col + current_indent. The description is wrapped at max(width - first_col - 2, 10) with preserve_paragraphs=True. Continuation lines are indented by first_col + current_indent. A row with an empty second item writes only the term and a newline.
  - Edge case: empty rows: widths is () so len != 2, which raises TypeError
  - Edge case: a term wider than col_max pushes the description to the next line
  - Edge case: an empty wrapped result writes '\n'
  - Edge case: a row with an empty description is still counted as 2 columns
  - Raises: `TypeError`
- **`HelpFormatter.section`** (`src/click/formatting.py:274-286`)
  - Signature: `def section(self, name: str) -> cabc.Generator[None]`
  - Behavior: Context manager that calls write_paragraph, then write_heading(name), then indent(). It dedents in a finally block.
  - Edge case: dedent runs even if the body raises
- **`HelpFormatter.indentation`** (`src/click/formatting.py:289-295`)
  - Signature: `def indentation(self) -> cabc.Generator[None]`
  - Behavior: Context manager that indents and dedents in a finally block.
- **`HelpFormatter.getvalue`** (`src/click/formatting.py:297-299`)
  - Signature: `def getvalue(self) -> str`
  - Behavior: Returns ''.join(self.buffer).
  - Edge case: an empty buffer gives ''
- **`join_options`** (`src/click/formatting.py:302-320`)
  - Signature: `def join_options(options: cabc.Iterable[str]) -> tuple[str, bool]`
  - Behavior: Takes option strings and returns (', '.join(sorted opts), any_prefix_is_slash). Sorting is stable by the length of the prefix from parser._split_opt, so '-v' comes before '--verbose'. The flag is True if any prefix is '/'.
  - Edge case: an empty iterable gives ('', False)
  - Edge case: options with equal prefix length keep their input order
- **`FORCED_WIDTH`** (`src/click/formatting.py:11-11`)
  - Signature: `FORCED_WIDTH: int | None = None`
  - Behavior: Module global, default None. HelpFormatter uses it as the default width when no width is given. CliRunner.isolation sets it to 80 and restores it afterwards (testing.py:437-438, 592).
  - Edge case: it only applies when width=None

### Error conventions
The module raises only one exception directly: TypeError("Expected two columns for definition list") in write_dl (line 246). The style is a short sentence with no trailing period. There is no ValueError validation of widths or indents. Translatable text goes through gettext (only "Usage:") (line 167).

### Examples
write_text wraps at the given width with the current indent (`tests/test_formatting.py:426-433`)
```
formatter = click.HelpFormatter(width=len("  Lorem ipsum dolor sit amet,"))
formatter.current_indent = 2
formatter.write_text(text)
actual = formatter.getvalue()
# "  Lorem ipsum dolor sit amet,\n  consectetur adipiscing elit\n"
```
Docstring help with a \b block and a fixed terminal width (`tests/test_formatting.py:30-36`)
```
result = runner.invoke(cli, ["--help"], terminal_width=60)
assert not result.exception
assert result.output.splitlines() == [
    "Usage: cli [OPTIONS]",
    "",
    "  First paragraph.",
    ...
```
Customizing the formatter class on a Context (`src/click/core.py:648-650`)
```
return self.formatter_class(
    width=self.terminal_width, max_width=self.max_content_width
)
```
write_usage with a styled prefix and a narrow width (`tests/test_formatting.py:509-511`)
```
formatter = click.HelpFormatter(width=40)
formatter.write_usage("cli", "[OPTIONS]", prefix=styled_prefix)
rendered = formatter.getvalue()
```

### Tests
- `tests/test_formatting.py`: Most tests use the `runner` fixture. They define a click command or group and call runner.invoke(cli, ['--help'], terminal_width=N). They then compare result.output.splitlines() to an exact list of lines. Direct unit tests build click.HelpFormatter(...), set current_indent, call write_usage or write_text, and compare getvalue() to an exact string. Parametrized tests cover write_usage with empty args, a custom prefix and a long prog. wrap_text is checked for styled input: the ANSI-styled output should give the same line layout as the stripped plain input, compared via strip_ansi. The file also covers usage errors, the \b marker, truncating docstrings and show_default.

### Extension points
- **Context.formatter_class** (`src/click/core.py:315`): Set a HelpFormatter subclass to override write_dl, write_heading, write_usage and so on, for example to colorize or reflow output.
- **Context.make_formatter** (`src/click/core.py:638`): Override to construct a formatter with custom arguments.
- **Command.format_help / format_options / format_help_text / format_epilog** (`src/click/core.py:1259`): Override these to call formatter methods in a new layout, such as extra sections via formatter.section().
- **HelpFormatter.write_dl** (`src/click/formatting.py:229`): Subclass to change the column algorithm or the col_max and col_spacing defaults.
- **FORCED_WIDTH** (`src/click/formatting.py:11`): The global width override, used by the test runner.
- **HelpFormatter.section** (`src/click/formatting.py:274`): Context manager that custom format_* methods can use for new help sections.

### Gaps (model's judgment, not verifiable from code)
- write_dl does not validate input rows or support more than two columns, and it raises TypeError on empty rows. Why plausible: Commands with no options would still render an empty section safely, and a graceful empty case is a small change. Nearest: `HelpFormatter.write_dl`
- dedent has no floor at zero and there is no guard against unbalanced indent and dedent calls. Why plausible: A small clamp or assertion would prevent negative indentation producing odd output. Nearest: `HelpFormatter.dedent`
- There is no direct control over the wrapping of the description column, such as hanging indents or a configurable min text width. The minimum of 10 and the 2-column right margin are hard-coded. Why plausible: The numbers could become parameters or class attributes, like col_max and col_spacing already are. Nearest: `HelpFormatter.write_dl`
- There is no option to write to a stream, and no richer output such as a heading style. The formatter always buffers in memory and headings are plain text. Why plausible: Styled headings could be added via a hook in write_heading. Nearest: `HelpFormatter.write_heading`

## Upstream (pinned 8.5.1 (released 2026-11-09 per repo/CHANGES.md:1-3; GitHub releases page shows 06 Nov), latest 8.5.1 released; main is 8.6.0 (unreleased))

### Changes after the pinned commit
- [Drop Python 3.10 (#3920)](https://github.com/pallets/click/pull/3920): 8.6.0 unreleased: Python 3.10 no longer supported.
- [Deprecate non-identifier/keyword/non-lowercase parameter names (#3866)](https://github.com/pallets/click/pull/3866): Warns now; TypeError in Click 9.0.
- [Add Parameter.spec, deprecate human_readable_name (#3877)](https://github.com/pallets/click/pull/3877): spec returns how the user types the parameter. get_help_spec moves to Parameter. Error messages and warnings show the spec (--my-option) rather than the internal name.
- [CliRunner echo_stdin shows ^D / ^Z (#3878)](https://github.com/pallets/click/pull/3878): \x04 and \x1a stdin bytes display as ^D/^Z and are no longer passed to the command.
- [CliRunner.invoke context_settings argument (#3896)](https://github.com/pallets/click/pull/3896): Passes context settings such as color (closes issue 2110).
- [Help pages no longer wrap inside hyphenated words (#3902)](https://github.com/pallets/click/pull/3902): Also covers long words (issue 3362).
- [Docs: Nuitka standalone guide (#3897), catch_exceptions testing docs (#3917), Click UI scope (#3898)](https://github.com/pallets/click/pulls?q=is%3Apr+is%3Amerged): Documentation-only merges after the pin.
- [Python 3.15 added to test matrix (#3909)](https://github.com/pallets/click/pull/3909): CI change.

### Open or planned
- [#3880 Split PAGER/EDITOR with Windows-specific shlex equivalent](https://github.com/pallets/click/pull/3880): Open PR.
- [#3827 Require parameter name to be a non-keyword Python identifier](https://github.com/pallets/click/pull/3827): Open PR.
- [#3921 Python 3.11 cleanups](https://github.com/pallets/click/pull/3921): Open PR.
- [#3859 / #3412 Add pyrefly type checking](https://github.com/pallets/click/pull/3859): Open PRs.
- [#2880 PromptBuilder format customization for prompt/confirm](https://github.com/pallets/click/pull/2880): Open PR.
- [#2864 Improve internationalization](https://github.com/pallets/click/pull/2864): Open PR.
- [#2784 Allow adding dynamic parameters to every Context](https://github.com/pallets/click/pull/2784): Open PR.
- [#3097 WIP help page customization low-level API](https://github.com/pallets/click/pull/3097): Open WIP PR.
- [#3154 Click 9.0 / #3156 remove deprecated code for 9.0](https://github.com/pallets/click/issues/3154): Planned major release.
- [#3652 Append ellipsis to metavars when multiple=True](https://github.com/pallets/click/issues/3652): Open feature request.
- [#3036 Support set/frozenset/dict as native types](https://github.com/pallets/click/issues/3036): Open feature request.
- [#2992 Add get_usage() output to get_info_dict()](https://github.com/pallets/click/issues/2992): Open feature request.
- [#2676 Automatically parse negative-number arguments](https://github.com/pallets/click/issues/2676): Open feature request.
- [#944 Color support for exceptions](https://github.com/pallets/click/issues/944): Open feature request.
- [#3915 PowerShell completion mangles Windows paths](https://github.com/pallets/click/issues/3915): Open bug.
- [#3914 show_envvar drops envvar in errors with auto_envvar_prefix](https://github.com/pallets/click/issues/3914): Open bug.
- [#3406 Migrate sentinels to PEP 661](https://github.com/pallets/click/issues/3406): Open issue.

### Do not propose
- PowerShell shell completion (in 8.5.0)
- Argument(help=...) and Positional arguments help section (8.5.0/8.5.1)
- Parameter-level help argument; Option.get_help_spec (8.5.1)
- Parameter.spec / human-readable parameter spec in errors (merged, 8.6.0)
- CliRunner.invoke context_settings (merged)
- CliRunner capture='fd' mode (8.4.0)
- NoSuchCommand with misspelled-command suggestions (8.4.0)
- custom_version_option (8.5.0)
- get_pager_file and incremental echo_via_pager (8.4.x)
- deepcopy/pickle support for Parameter and Command (8.5.1)
- Hyphen-safe help wrapping (merged)
- Deprecation of invalid/non-lowercase parameter names (merged)
- Python 3.10 drop (merged)
- Smarter short-help sentence detection (8.5.1)
- show_envvar for envvar sequences (8.5.1)
- PromptBuilder prompt customization, i18n improvements, dynamic Context params, pyrefly, help-page customization API (open PRs)

### Upstream limitations
- Could not load the repo's CHANGES.rst; the file is CHANGES.md. Used that.
- Upstream CHANGES.md on HEAD was read via summarizing fetch; only the 8.6.0 section was seen.
- Release date mismatch: repo says 2026-11-09, releases page says 06 Nov.
- GitHub list pages were summarized, so only 25 of 74 open issues were seen and the merged-PR list shows page 1 only.
- The git index reported a non-monotonic pack error, but describe still worked.
- Did not verify pinned code line-by-line; this report covers upstream state only.

## Verification
### Dropped claims
- (none)

### Notes
- src/click/types.py: gap 'BoolParamType.bool_states is not configurable per instance, as its own docstring ...' names a nearest interface `BoolParamType.bool_states` that is not in this file

## Open questions
- The checkout is commit cf19179. I did not confirm that the 8.5.1 tag points to it. The pyproject version and the CHANGES.md section both say 8.5.1.
- I did not read the bodies of decorators.py, types.py, parser.py, shell_completion.py, _termui_impl.py or the individual tests. The coverage mapping comes from file names and one-line module roles.
- I did not check whether a runtime dependency exists on Windows (for example colorama). The pyproject [project] table shows no dependencies key.
- Docs and examples were not mapped in detail.

## Limitations
- Read-only pass. No code or tests were run, so every command has verified=false.
- Many macOS `._*` AppleDouble files are present in the clone. I ignored them as noise.
- Some key module paths are cited at line 1 or at declaration lines only, and only the sections named above were read.
- `src/click/core.py`: Environment variables are always strings and are split via type.split_envvar_value for nargs != 1. An empty env var counts as unset.
- `src/click/core.py`: Options do not support nargs=-1 (TypeError), and Arguments do not support multiple.
- `src/click/core.py`: Chain-mode groups cannot contain nested Groups or optional Arguments (RuntimeError).
- `src/click/core.py`: A default_map key that is present with value None blocks the parameter's own default.
- `src/click/core.py`: Many constructor validations run only under __debug__, so `python -O` skips them.
- `src/click/core.py`: The UNSET sentinel is internal. User code, callbacks and invoke() see None, but Option.default keeps the raw UNSET.
- `src/click/core.py`: Several methods (consume_value, process_value, handle_parse_result, resolve_envvar_value) are :meta private: and may change.
- `src/click/core.py`: Duplicate-option detection only warns, and only in debug mode.
- `src/click/core.py`: Context.protected_args, BaseCommand and MultiCommand are deprecated, with warnings.
- `src/click/core.py`: In chain mode every subcommand is parsed before any runs, and ctx.invoked_subcommand is only '*'.
- `src/click/core.py`: I did not read lines 1259-1325 (help formatting) or 3352-3500 (Option help and parser bridge) in detail, nor most individual test bodies.
- `src/click/decorators.py`: Wrappers from pass_context and pass_obj do not use ctx.invoke, unlike make_pass_decorator and pass_meta_key.
- `src/click/decorators.py`: The bare form of command/group cannot take cls or attrs (assert).
- `src/click/decorators.py`: version_option's frame-inspection package detection depends on being called directly from the user's module.
- `src/click/decorators.py`: Names are derived from f.__name__ only. The suffix stripping covers four fixed suffixes.
- `src/click/decorators.py`: Decorator order determines the order of parameters, and this is not validated.
- `src/click/decorators.py`: I did not read tests/typing/*.py contents, nor most of test_basic.py beyond the version tests.
- `src/click/types.py`: Choice rebuilds the normalized mapping on every convert, shell_complete-metavar and message call, and takes the first match when normalized values collide.
- `src/click/types.py`: DateTime has no timezone support and relies on strptime. A non-str input raises TypeError instead of BadParameter.
- `src/click/types.py`: BoolParamType.convert raises AttributeError for non-str, non-bool inputs such as int.
- `src/click/types.py`: Tuple.convert needs a sized value and only works with a fixed nargs.
- `src/click/types.py`: Path.convert checks executable against the original value, not the resolved path.
- `src/click/types.py`: convert_type is a closed if-chain, and bool must be checked after int only by identity. UUID is not mapped from the uuid.UUID class.
- `src/click/types.py`: I did not read the docs, and I only grepped the tests rather than reading them in full.
- `src/click/parser.py`: Module and class are internal and deprecated. _OptionParser is marked deprecated since 8.2 and slated for removal in 9.0, and the module docstring plans to remove more.
- `src/click/parser.py`: Only the actions store, store_const, append, append_const and count exist, and they are plain strings validated lazily.
- `src/click/parser.py`: Only one nargs=-1 positional is supported.
- `src/click/parser.py`: The parser does no type conversion, defaults or validation. Those live in core.
- `src/click/parser.py`: Argument parsing is two-phase: all options are processed before positional assignment, so positional nargs cannot influence option parsing.
- `src/click/parser.py`: parse_args mutates the input list.
- `src/click/parser.py`: Tests for this module are minimal; direct unit coverage of parsing behavior is thin.
- `src/click/shell_completion.py`: The shell is parsed with instruction.partition('_'), so registered shell names cannot contain underscores.
- `src/click/shell_completion.py`: The zsh script is frozen for backwards compatibility, so only format_completion can change zsh behavior.
- `src/click/shell_completion.py`: Bash completion requires Bash >= 4.4 (the nosort option). The check only warns on stderr, and the string comparison of versions is buggy for majors >= 10.
- `src/click/shell_completion.py`: The source output has no trailing newline (nl=False). The complete output is utf-8 encoded bytes.
- `src/click/shell_completion.py`: Completion runs with resilient_parsing=True and does not invoke callbacks or prompts. _resolve_context mutates the passed ctx_args.
- `src/click/shell_completion.py`: Options are recognized through ctx._opt_prefixes, a private attribute.
- `src/click/shell_completion.py`: The PowerShell script treats the dir and file types with a Get-ChildItem glob on the prefix and ignores the item's value.
- `src/click/shell_completion.py`: Only the plain, dir and file item types are understood by the built-in scripts.
- `src/click/termui.py`: Behavior of ProgressBar, Editor, open_url, getchar and the pager lives in _termui_impl.py, which I did not read.
- `src/click/termui.py`: prompt return typing is not enforced at runtime; the default goes through value_proc.
- `src/click/termui.py`: pause and clear are no-ops when not on a TTY.
- `src/click/termui.py`: secho can't style bytes.
- `src/click/termui.py`: The test lists were only sampled and not read in full.
- `src/click/exceptions.py`: ClickException.message and show_color are Final, so subclasses cannot reassign them. show_color is captured at construction.
- `src/click/exceptions.py`: Abort and Exit are not ClickExceptions, so `except ClickException` does not catch them.
- `src/click/exceptions.py`: Exit.__init__ does not call super().__init__, so args is empty. Exit is slotted, but it inherits __dict__ from RuntimeError.
- `src/click/exceptions.py`: MissingParameter.__str__ and format_message differ: str gives the raw message or 'Missing parameter: name', while show gives the full formatted text.
- `src/click/exceptions.py`: NoArgsIsHelpError.show uses err=True, so its output goes to stderr only when file is None.
- `src/click/exceptions.py`: The only test for this module that I read covers FileError.format_message; other classes have no dedicated tests in tests/test_exceptions.
- `src/click/formatting.py`: Output is always buffered in memory (class docstring).
- `src/click/formatting.py`: write_dl accepts exactly two columns.
- `src/click/formatting.py`: write_heading appends ':' unconditionally and does not wrap.
- `src/click/formatting.py`: The terminal-width default is clamped to min 50 and max (max_width - 2), with max_width defaulting to 80.
- `src/click/formatting.py`: FORCED_WIDTH is a module-global, so it is not thread-safe.
- `src/click/formatting.py`: The class docstring says width 'clamped to a maximum of 78', while the code uses max_width=80 minus 2, which gives the same result.
