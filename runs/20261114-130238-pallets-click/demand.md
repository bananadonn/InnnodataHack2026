# User demand: pallets/click @ `cf19179e8e2f`

Mined by `claude-sonnet-5-5` with web access. Every URL was checked against the agent's real web calls.

| Request | Source | Status | Maintainers | Still missing | Area |
|---|---|---|---|---|---|
| [Basic async support (async def commands)](https://github.com/pallets/click/issues/2033) | issue | open | unclear | yes | src/click/core.py |
| [Equivalent of argparse add_argument_group: help sections](https://github.com/pallets/click/issues/373) | issue | open | unclear | yes | src/click/core.py (Command.format_options) |
| [Allow checking for path non-existence (click.Path)](https://github.com/pallets/click/issues/1428) | issue | open | unclear | yes | src/click/types.py (Path) |
| [Allow hiding range values for IntRange in --help](https://github.com/pallets/click/issues/2679) | issue | open | receptive | yes | src/click/types.py (_NumberRangeBase._describe_range) |
| [Support @click.argument(hidden=True)](https://github.com/pallets/click/issues/3788) | issue | closed-not-planned | declined | yes | src/click/core.py (Argument) |
| [Support redirecting --help to a man page](https://github.com/pallets/click/issues/3882) | issue | closed-not-planned | declined | yes | src/click/core.py (Command.get_help_option) |
| [Env var support for _FILE (Docker-secrets style)](https://github.com/pallets/click/issues/3258) | issue | closed-not-planned | declined | yes | src/click/core.py (Option envvar resolution) |
| [Toggle JSON-formatted error output](https://github.com/pallets/click/issues/3205) | issue | closed-not-planned | declined | yes | src/click/exceptions.py (ClickException.show) |
| [Support shell completion for nushell](https://github.com/pallets/click/issues/2888) | issue | closed-not-planned | declined | yes | src/click/shell_completion.py |
| [Navigable choice menu within click.prompt()](https://github.com/pallets/click/issues/2795) | issue | closed-not-planned | declined | yes | src/click/termui.py (prompt) |
| [Opposite of is_eager: always process a parameter last](https://github.com/pallets/click/issues/2963) | issue | closed-not-planned | declined | yes | src/click/core.py (parameter processing order) |
| [Color/style support for exceptions](https://github.com/pallets/click/issues/944) | issue | open | receptive | yes | src/click/exceptions.py |
| [Allow nargs=-1 in options with a separator](https://github.com/pallets/click/issues/2771) | issue | open | unclear | yes | src/click/parser.py and core.py (Option nargs) |
| [Mutually exclusive options](https://gist.github.com/thebopshoobop/51c4b6dce31017e797699030e3975dbf) | other | n/a | none | yes | src/click/core.py (Command.parse_args / Parameter.handle_parse_result) |
| [Option groups: titled sections in --help](https://github.com/click-contrib/click-option-group) | addon | n/a | none | yes | src/click/core.py (Command.format_options), src/click/formatting.py |
| [Conditional and parametric parameter constraints (all_or_none, require_one, If)](https://cloup.readthedocs.io/en/latest/pages/constraints.html) | addon | n/a | none | yes | src/click/core.py (Command.invoke / parse_args hook) |
| [Subcommand aliases (multiple names for one command)](https://github.com/click-contrib/click-aliases) | addon | n/a | none | yes | src/click/core.py (Group.get_command, Group.resolve_command, Group.format_commands) |
| [Default subcommand when none is given](https://github.com/click-contrib/click-default-group) | addon | n/a | none | yes | src/click/core.py (Group.parse_args, Group.invoke, Group.resolve_command) |
| [Multiple help sections for subcommands](https://cloup.readthedocs.io/en/latest/) | addon | n/a | none | yes | src/click/core.py (Group.format_commands), src/click/formatting.py |
| [Loading option defaults from a config file](https://gist.github.com/jwodder/8ce218892331229c9116ed6c3e16a5bb) | other | n/a | none | yes | src/click/decorators.py, src/click/core.py (Context.default_map) |
| [Config file as a distinct ParameterSource, and config awareness in groups](https://kdeldycke.github.io/click-extra/config.html) | addon | n/a | none | yes | src/click/core.py (ParameterSource at lines 174-210) |
| [Enum choice matched by value, with aliases and case-insensitive matching](https://github.com/kdeldycke/click-extra) | addon | n/a | none | yes | src/click/types.py (Choice.normalize_choice, line 406) |
| [Missing parameter types: comma-separated MultiChoice and Duration/timedelta](https://kdeldycke.github.io/click-extra/types.html) | addon | n/a | none | yes | src/click/types.py |
| [Colorized help output](https://github.com/click-contrib/click-help-colors) | addon | n/a | none | yes | src/click/formatting.py (HelpFormatter), src/click/core.py (Command.format_help) |
| [NO_COLOR / FORCE_COLOR support and a tri-state --color option](https://kdeldycke.github.io/click-extra/colorize.html) | addon | n/a | none | yes | src/click/_compat.py (should_strip_ansi, lines 502-513), src/click/utils.py (echo) |
| [Built-in interactive REPL for a click app](https://github.com/click-contrib/click-repl) | addon | n/a | none | yes | src/click/core.py, src/click/shell_completion.py |

## Basic async support (async def commands)

- URL: https://github.com/pallets/click/issues/2033
- Need: Declare commands as `async def` and have Click start the event loop, instead of wrapping each coroutine in asyncio.run; users hit 'coroutine was never awaited'.
- Demand signal: Original post shows about 53 thumbs-up and 17 rockets; 23 comments.
- Workaround: asyncclick fork; custom decorator calling asyncio.run; Context.invoke override.
- Maintainers: unclear: davidism: full async is hard and would break subclasses; asked for a concrete use case; said auto-starting an event loop for async callbacks is the most likely addition. Nothing committed.
- Still missing at the pin: yes (Grepped src for iscoroutine/asyncio and found no matches. core.py only imports inspect for cleandoc and isfunction.)

## Equivalent of argparse add_argument_group: help sections

- URL: https://github.com/pallets/click/issues/373
- Need: Group options, arguments or subcommands into labelled sections in --help, as argparse add_argument_group does.
- Demand signal: 28 comments; the section-API proposal has about 7 thumbs-up; several users asked for it in core.
- Workaround: Subclass Command and override format_options; cloup, click-option-group, rich-click.
- Maintainers: unclear: Early maintainer untitaker said it was sensible but could be a third-party extension. A 2019 contributor was unsure it belongs in core. davidism removed the enhancement label in 2020.
- Still missing at the pin: yes (Grepped src for help_group and found no matches. The command help formatter at core.py around line 1436 lists options in one flat group.)

## Allow checking for path non-existence (click.Path)

- URL: https://github.com/pallets/click/issues/1428
- Need: Require that a path does not exist, for example when creating a file without overwriting; exists=False does not enforce this.
- Demand signal: Original post has about 8 thumbs-up; other comments have 4 and 5; several users commented in 2024.
- Workaround: Custom ParamType or callback.
- Maintainers: unclear: davidism prefers a custom type or callback. If added, he would use a tri-state exists=None/True/False rather than extra flags.
- Still missing at the pin: yes (types.py:1097 and :1109 define `exists: bool = False`. The check at line 1179 (`if not self.exists`) only skips the missing-path case, so there is no must-not-exist mode.)

## Allow hiding range values for IntRange in --help

- URL: https://github.com/pallets/click/issues/2679
- Need: Add show_range=False so a count=True verbosity option with IntRange does not print the range in help.
- Demand signal: Small: one thumbs-up, 4 comments, a related issue #1525, and a fork commit by gar1t.
- Workaround: Subclass IntRange and override _describe_range.
- Maintainers: receptive: davidism: 'Eventually, sure', but it should wait for the help formatter refactor so options can collect extra display fields from their param type.
- Still missing at the pin: yes (types.py:717-729 _describe_range always returns the range text and has no toggle.)

## Support @click.argument(hidden=True)

- URL: https://github.com/pallets/click/issues/3788
- Need: Hide an argument from help, as options can be hidden.
- Demand signal: Single requester; no reactions visible.
- Workaround: Make the argument optional, or use nargs=-1 and process in the command.
- Maintainers: declined: davidism: arguments are required or affect parsing of other arguments, so a hidden argument consuming input would be very hard to understand. He suggested making it optional or consuming the remaining input.
- Still missing at the pin: yes (core.py:2934 and :2998 show hidden only on Option. A comment at core.py:3786 says an argument cannot be hidden.)

## Support redirecting --help to a man page

- URL: https://github.com/pallets/click/issues/3882
- Need: Make --help open a man page or external docs, like `git cmd --help`, while keeping short help available.
- Demand signal: Single requester; no reactions visible.
- Workaround: Define a custom help option with a callback.
- Maintainers: declined: davidism: for something this custom, disable the built-in help option and write your own.
- Still missing at the pin: yes (Grepped src for 'man page' and found no matches. The help option only prints formatted help, so there is no hook for an external viewer.)

## Env var support for _FILE (Docker-secrets style)

- URL: https://github.com/pallets/click/issues/3258
- Need: env_var_file=True so an option reads its value from the path in {ENV}_FILE when the env var is not set.
- Demand signal: Single requester who offered a PR; no reactions visible.
- Workaround: Read the _FILE variable in a callback or default function.
- Maintainers: declined: davidism suggested Docker --env-file/Compose env_file or python-dotenv. The author replied that this does not cover Docker secrets.
- Still missing at the pin: yes (Grepped src for `_FILE`; the only hits were unrelated variable names like binary_file and ui_filename.)

## Toggle JSON-formatted error output

- URL: https://github.com/pallets/click/issues/3205
- Need: A built-in way (for example a --format json flag) to emit Click errors and help as JSON for CI and logging.
- Demand signal: Single requester; no reactions visible.
- Workaround: Override ClickException.show or catch exceptions in standalone mode.
- Maintainers: declined: ThiefMaster: a global flag would be backwards-incompatible with CLIs that already define that option, and he had not seen other tools do this.
- Still missing at the pin: yes (exceptions.py:57-65 show() only echoes 'Error: message' text, with no structured format.)

## Support shell completion for nushell

- URL: https://github.com/pallets/click/issues/2888
- Need: Generate completions for nushell, which uses static extern definitions.
- Demand signal: One thumbs-up; the author planned an extension.
- Workaround: Third-party extension via the pluggable ShellComplete classes.
- Maintainers: declined: davidism: Click will not maintain more shells and suggested a separate click-nushell extension, since completion is pluggable. Rowlando13 said completion cannot be tested currently.
- Still missing at the pin: yes (shell_completion.py defines only BashComplete (line 388), ZshComplete (447) and FishComplete (479), and no nushell class.)

## Navigable choice menu within click.prompt()

- URL: https://github.com/pallets/click/issues/2795
- Need: Pick a choice with arrow or vim keys in prompt, built on getchar, to avoid typos.
- Demand signal: One reaction.
- Workaround: prompt-toolkit, Textual or other libraries.
- Maintainers: declined: davidism: 'I don't plan to add more complex UI elements to Click at this time'; suggested prompt-toolkit or Textual.
- Still missing at the pin: yes (termui.py prompt (around lines 146-260) is a line-based input with a Choice type check, with no key-navigated menu.)

## Opposite of is_eager: always process a parameter last

- URL: https://github.com/pallets/click/issues/2963
- Need: Run a callback (such as an interactive --ui option) after all other options are parsed, whatever the command-line order.
- Demand signal: Single requester; no reactions visible.
- Workaround: Do the work in the command function.
- Maintainers: declined: davidism: move the callback logic into the command body, which runs after all options.
- Still missing at the pin: yes (Grepped core.py and found only is_eager as an ordering control. No 'process last' parameter was found.)

## Color/style support for exceptions

- URL: https://github.com/pallets/click/issues/944
- Need: Let ClickException messages be styled (for example red errors) through a style attribute or global setting.
- Demand signal: Original post has 3 thumbs-up; a 2020 comment has 2; 6 comments.
- Workaround: Override show() in a ClickException subclass.
- Maintainers: receptive: davidism (2020) proposed calling style() on the message and a style_args attribute. A contributor hit a circular import between termui and exceptions.
- Still missing at the pin: yes (exceptions.py:57-65 show() echoes the plain message. Grepped exceptions.py for style and found no styling hooks.)

## Allow nargs=-1 in options with a separator

- URL: https://github.com/pallets/click/issues/2771
- Need: Let one option take several values, such as --option 1,2,3 or --option 1 2 3, without repeating the flag.
- Demand signal: 7 comments from several users; a Typer PR implements a variant.
- Workaround: Callback that splits on the separator; Click Extra MultiChoice; repeated flags with multiple=True.
- Maintainers: unclear: davidism said the parser only sees shell-split tokens, so separators with spaces need significant parser complexity. He offered a callback workaround; the milestone was removed.
- Still missing at the pin: yes (Grepped core.py/parser.py for nargs and found no separator parameter. The issue was open as of the fetched page.)

## Mutually exclusive options

- URL: https://gist.github.com/thebopshoobop/51c4b6dce31017e797699030e3975dbf
- Need: Make conflicting flags unusable together. Users have to write their own helper that counts the set flags and raises UsageError.
- Demand signal: Gist has 3 stars and 1 fork. A search also surfaced other mutual-exclusion gists and a Stack Overflow thread (37310718), which I could not open.
- Workaround: A custom exclusive() helper that raises click.UsageError. The gist warns it breaks if option names are reused across contexts. Cloup and click-option-group are alternatives.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'mutually' in repo/src/click returned no matches. Option and Command have no exclusivity or constraint parameter.)

## Option groups: titled sections in --help

- URL: https://github.com/click-contrib/click-option-group
- Need: Group related options under titled sections in help output and give the group a relationship. click-option-group describes itself as 'a Click-extension package that adds option groups missing in Click'.
- Demand signal: Two separate add-ons implement it: click-option-group and cloup. rich-click also offers panels.
- Workaround: Use click-option-group or cloup.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'option_group|OptionGroup' in repo/src/click returned nothing. Command.format_options writes a single 'Options' section.)

## Conditional and parametric parameter constraints (all_or_none, require_one, If)

- URL: https://cloup.readthedocs.io/en/latest/pages/constraints.html
- Need: Declare rules over sets of parameters (RequireExactly, RequireAtLeast, all_or_none, require_any) and conditional rules (If(IsSet(...), then, else_)). In plain click these are hand-written checks.
- Demand signal: Cloup implements a full constraint system. click-constrained-option is a separate package for the same need, seen only in search results.
- Workaround: Cloup's ConstraintMixin and @constraint. The docs say it needs cloup.Command and does not work with plain click.Command.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'mutually|constraint' in repo/src/click found no constraint API.)

## Subcommand aliases (multiple names for one command)

- URL: https://github.com/click-contrib/click-aliases
- Need: Give a command or group more than one name, such as `ci` for `commit`, and show the aliases in help. The README says 'Add (multiple) aliases to a click_ group or command.'
- Demand signal: Several independent add-ons implement it: click-aliases and cloup, plus click-with-aliasing and click-supercharged seen in search results.
- Workaround: ClickAliasedGroup, or subclass Group and override get_command, as in click's own examples/aliases.
- Maintainers: none
- Still missing at the pin: yes (Grep 'alias' over repo found no alias feature in Group. The only non-test hit is repo/examples/aliases/aliases.py, a Group subclass example. There is no 'aliases' parameter on Command or Group.)

## Default subcommand when none is given

- URL: https://github.com/click-contrib/click-default-group
- Need: Run a chosen subcommand when no subcommand is named, instead of showing help. The project says it extends click.Group 'to invoke a command without explicit subcommand name'.
- Demand signal: A dedicated click-contrib package exists. click-extra also mentions patching Group.parse_args for default subcommands.
- Workaround: DefaultGroup with default='foo', default_if_no_args=True.
- Maintainers: none
- Still missing at the pin: yes (core.py:1736-1767 and 2027 show Group only has invoke_without_command and no_args_is_help. There is no default-command parameter.)

## Multiple help sections for subcommands

- URL: https://cloup.readthedocs.io/en/latest/
- Need: Organize a Group's subcommands into several labeled help sections instead of one flat 'Commands' list. rich-click offers 'panels' for the same purpose.
- Demand signal: Two libraries (cloup, rich-click) independently implement it.
- Workaround: Cloup subcommand sections or rich-click panels.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'sections|panel' in repo/src/click/core.py found no relevant feature. Group.format_commands is the single-list implementation.)

## Loading option defaults from a config file

- URL: https://gist.github.com/jwodder/8ce218892331229c9116ed6c3e16a5bb
- Need: Let users set option defaults in a config file and point to it with `--config`. Click only offers the low-level default_map.
- Demand signal: Gist has 0 stars. The author also wrote a blog post on it, and click-extra has a config_option.
- Workaround: An eager --config option whose callback fills ctx.default_map from ConfigParser. Limitation: a subcommand cannot share a name with one of its parameters.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'config|toml|json5|.ini' in repo/src/click found no config-file loader. It only has utils.get_app_dir and Context.default_map.)

## Config file as a distinct ParameterSource, and config awareness in groups

- URL: https://kdeldycke.github.io/click-extra/config.html
- Need: Distinguish values that came from a config file from values from default_map. click-extra also needs to patch Group.parse_args to read config before a bare invocation shows help.
- Demand signal: Single source: click-extra's own docs.
- Workaround: click-extra's @config_option. Its docs say it works with vanilla click and that file values show as DEFAULT_MAP.
- Maintainers: none
- Still missing at the pin: yes (core.py:201-210 shows ParameterSource members PROMPT, COMMANDLINE, ENVIRONMENT, DEFAULT_MAP and DEFAULT. There is no config-file member.)

## Enum choice matched by value, with aliases and case-insensitive matching

- URL: https://github.com/kdeldycke/click-extra
- Need: Use an Enum as a choice and accept member values or friendly strings. click.Choice matches only Enum.name, so a user must type 'TEXT' rather than the value 'text' (per click-extra's types docs).
- Demand signal: click-extra's README lists EnumChoice. A PyPI 'enumchoice' package and Typer's enum handling also showed up in search results.
- Workaround: click-extra EnumChoice, or subclass click.Choice.
- Maintainers: none
- Still missing at the pin: yes (types.py:416 uses `choice.name if isinstance(choice, enum.Enum)`. Matching is by name only, though case_sensitive=False is supported. There is no option to match by value or add aliases.)

## Missing parameter types: comma-separated MultiChoice and Duration/timedelta

- URL: https://kdeldycke.github.io/click-extra/types.html
- Need: Accept `--tags alpha,gamma` as one token (the page says click ships no equivalent) and parse `7 days`, `12h` or `P7D` into a timedelta (the page says 'Click has no type for time quantities').
- Demand signal: Single source: click-extra docs.
- Workaround: click-extra MultiChoice and Duration, or hand-written ParamTypes or callbacks.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'timedelta' in repo/src/click returned no matches. types.py has no comma-splitting type. envvar_list_splitter (lines 106, 946, 1095) applies only to environment variables.)

## Colorized help output

- URL: https://github.com/click-contrib/click-help-colors
- Need: Color section headings and option names in --help. click-help-colors describes itself as 'Colorization of help messages in Click'. click-extra and rich-click do the same, plus theming.
- Demand signal: Three libraries implement it (click-help-colors, click-extra, rich-click).
- Workaround: HelpColorsGroup / HelpColorsCommand, click-extra, or rich-click.
- Maintainers: none
- Still missing at the pin: yes (HelpFormatter in formatting.py has no style or theme hooks. The only style() calls in core.py are for red error messages (core.py:1411, 2807).)

## NO_COLOR / FORCE_COLOR support and a tri-state --color option

- URL: https://kdeldycke.github.io/click-extra/colorize.html
- Need: A standard `--color[=WHEN]` flag, plus respect for NO_COLOR and FORCE_COLOR. The page says Click manages neither.
- Demand signal: Single source: click-extra docs.
- Workaround: click-extra's color option, or manually passing color= to echo.
- Maintainers: none
- Still missing at the pin: yes (Grep for 'NO_COLOR|FORCE_COLOR' in repo/src/click returned no matches. should_strip_ansi at _compat.py:502-513 only checks isatty and the explicit color argument.)

## Built-in interactive REPL for a click app

- URL: https://github.com/click-contrib/click-repl
- Need: Run subcommands one after another without retyping the program name, with a persistent ctx.obj, shell escapes and tab completion.
- Demand signal: A click-contrib package exists. The README claims a large performance gain from reusing ctx.obj.
- Workaround: register_repl(cli) from click-repl, which needs prompt_toolkit.
- Maintainers: none
- Still missing at the pin: yes (A case-insensitive grep for 'repl|interactive shell|shell mode' in repo/src/click found only unrelated 'replace' hits. There is no REPL feature.)

## Limitations
- demand:project: Reaction counts come from the fetch tool's summaries of the pages, not from the raw HTML, and some pages showed none.
- demand:project: The not-planned list was sampled over 3 of about 6 pages.
- demand:project: Repo checks were mostly keyword greps plus a few reads of the relevant files, not exhaustive reads.
- demand:project: The label-filtered issue searches returned nothing, so the issue list came from reaction- and comment-sorted views.
- demand:project: Where the ./repo checks cite specific line numbers, they come from the greps and reads I actually ran.
- demand:community: stackoverflow.com could not be fetched, and PyPI and several GitHub docs paths returned errors. I found no Stack Overflow vote counts or accepted answers I could verify. Thread numbers like 37310718 appear only in search results.
- demand:community: Most demand evidence is the existence of add-ons, not votes or comment counts. The only quantitative signals were gist stars (3 and 0).
- demand:community: Several items rest on a single add-on's documentation, so demand for them is weak. MultiChoice and Duration were merged into one item to keep URLs distinct.
- demand:community: Add-on descriptions come from tool summaries of README or docs pages, not full pages. The repo checks are Grep-based plus targeted reads of types.py, core.py and _compat.py.
- demand:community: Maintainer positions are all 'none' because I did not read click's own tracker, per the instructions.
- demand:community: Aliases are listed as missing from the library API even though click ships an examples/aliases recipe.
