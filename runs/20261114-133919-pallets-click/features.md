# Feature plan: pallets/click @ `cf19179e8e2f`

Run `20261114-133919-pallets-click` · designed by `claude-sonnet-5-5` · checked against the repository by the pipeline.

## Variation strategy
Five features touch five different areas: post-parse option validation (core Option/Command), subcommand resolution (core Group), type conversion (types.Choice), interactive prompting (termui), and shell-completion post-processing (shell_completion). Each combines several interacting rules: sources and ordering, exact/alias/prefix precedence, exact-vs-prefix matching, attempt counting across failure kinds, and dedupe/sort/truncate ordering.

## 1. Option requires= and conflicts_with= constraints based on parameter source

- Slug: `option-requires-conflicts` · Category: **cross-parameter validation** · Estimated gold size: ~60 lines
- Attaches at: New kwargs in Option.__init__ (core.py:2983) and a validation pass at the end of Command.parse_args (core.py:1374-1385) before the extra-args check.
- Gold edits: `src/click/core.py`
- New test file: `tests/test_option_constraints.py` · Regression: `tests/test_options.py`, `tests/test_basic.py`, `tests/test_info_dict.py`
- Builds on: `src/click/core.py` (Option.__init__, Command.parse_args, Context.get_parameter_source, ParameterSource, Context.fail)

### Problem
Click has no way to say that one option needs another or excludes another. Users hand-write checks in callbacks. A built-in constraint that understands where each value came from lets defaults and default_map values be ignored correctly.

### Public interface
- `Option.__init__(..., requires: Sequence[str] | None = None, conflicts_with: Sequence[str] | None = None, ...)`
- `Both hold parameter NAMES (e.g. 'beta'), not option strings; stored as tuples on Option.requires and Option.conflicts_with (empty tuple by default)`
- `Command.parse_args runs the check after all handle_parse_result calls`

### Behavior
- An option is 'explicit' when ctx.get_parameter_source(name) is COMMANDLINE, ENVIRONMENT or PROMPT (i.e. ParameterSource < DEFAULT_MAP). DEFAULT and DEFAULT_MAP are not explicit.
- After all parameters are processed in Command.parse_args, params are visited in get_params order (declaration order). For each explicit Option that has constraints, first every name in conflicts_with is checked, then every name in requires, each in the listed order.
- If a conflicts_with name is also explicit, raise UsageError (via ctx.fail) with message "Option '--alpha' cannot be used with '--beta'."
- If a requires name is not explicit, raise UsageError with message "Option '--alpha' requires '--beta'."
- The displayed option string is the longest string in the param's opts (first one on a tie). Exit code is 2 under CliRunner and the output contains 'Error: ' followed by the message.
- The first violation found stops the check; only one error is reported.

### Interaction rules
- Conflicts are checked before requires on the same option, so an option that both conflicts with and requires 'b' reports the conflict when b is explicit.
- A constraint declared on option A is only enforced when A is explicit; an explicit B that A requires does not impose anything on A.
- A value that comes only from default or default_map never triggers a constraint and never satisfies a requires.
- With ctx.resilient_parsing=True (e.g. shell completion) no constraint check runs.

### Edge cases and errors
- A name in requires/conflicts_with that matches no parameter of the command raises TypeError("Option 'alpha' refers to unknown parameter 'zzz'.") at parse time when the owning option is explicit (the first quoted name is the owning option's name).
- Passing a plain str instead of a sequence raises TypeError("'requires' must be a sequence of parameter names, not a string.") from Option.__init__ (same wording with 'conflicts_with' for that argument).
- An option that lists its own name raises ValueError("Option 'alpha' cannot refer to itself.") from Option.__init__.
- A value supplied by envvar counts as explicit; a prompted value counts as explicit.
- A flag given as --no-x is explicit as well, as its source is COMMANDLINE.

### Backward compatibility
- Options without requires/conflicts_with behave exactly as before; Option.to_info_dict is unchanged.
- The new keyword args default to None, so existing positional/keyword usage and subclasses keep working.

### Examples
```python
@click.command()
@click.option('--alpha', requires=['beta'])
@click.option('--beta')
def cli(alpha, beta): pass
runner.invoke(cli, ['--alpha', '1'])
```
Expected: exit_code 2; output contains "Error: Option '--alpha' requires '--beta'."

```python
@click.command()
@click.option('--json', 'as_json', is_flag=True, conflicts_with=['as_csv'])
@click.option('--csv', 'as_csv', is_flag=True)
def cli(as_json, as_csv): pass
runner.invoke(cli, ['--json', '--csv'])
```
Expected: exit_code 2; output contains "Error: Option '--json' cannot be used with '--csv'."

```python
@click.option('--alpha', requires=['beta'], default='x')
@click.option('--beta')
...
runner.invoke(cli, [])
```
Expected: exit_code 0 (alpha comes from DEFAULT so no constraint applies)

### Acceptance criteria
- requires with missing target fails with the exact message and exit code 2
- conflicts_with with both explicit fails with the exact message
- defaults and default_map values never trigger or satisfy constraints
- an envvar-provided value counts as explicit
- unknown target name raises TypeError with the exact message
- string argument raises TypeError, self reference raises ValueError
- constraint-free commands are unaffected

### Why it is novel
Not in the repo or the upstream lists; the report lists mutually exclusive/required-together constraints only as a gap. The design (source-aware, name-based, fixed ordering) is specific to this repo's ParameterSource.

### Why it is hard
Solver must decide where to hook, use sources rather than values, honor ordering between conflicts and requires, and skip under resilient parsing.

## 2. Group command aliases and unambiguous prefix matching

- Slug: `group-alias-prefix-resolve` · Category: **subcommand resolution** · Estimated gold size: ~55 lines
- Attaches at: Group.resolve_command (core.py:2088-2112) and Group.__init__ (core.py:1730).
- Gold edits: `src/click/core.py`
- New test file: `tests/test_group_aliases.py` · Regression: `tests/test_commands.py`, `tests/test_chain.py`, `tests/test_basic.py`
- Builds on: `src/click/core.py` (Group.resolve_command, Group.get_command, Group.list_commands, Group.__init__); `src/click/exceptions.py` (NoSuchCommand)

### Problem
Group.resolve_command only does exact lookup. Users want short aliases ('st' for 'status') and git-style abbreviations without writing custom Group subclasses.

### Public interface
- `Group.__init__(..., allow_prefix_match: bool = False, **kwargs) stored as self.allow_prefix_match`
- `Group.add_alias(self, alias: str, target: str) -> None`
- `Group.resolve_command is extended (same signature)`

### Behavior
- Resolution order for args[0] (after make_str): 1) exact get_command match; 2) alias match; 3) the existing token_normalize_func retry (which then repeats steps 1 and 2 on the normalized token); 4) unique prefix match if allow_prefix_match.
- An alias maps to a target command name via add_alias; resolution returns the CANONICAL target name as the first tuple element, so the sub-context info_name and invoked_subcommand are the canonical name.
- Prefix matching considers names from list_commands(ctx) for which get_command(ctx, name) is not None and cmd.hidden is False, and that start with the token. Exactly one match resolves to it (returning that canonical name). Aliases are not considered in prefix matching.
- With several matches raise NoSuchCommand(token, message="Ambiguous command 'sta'. Could be: start, status.", ctx=ctx) listing matches sorted, joined by ', '.
- With zero matches the existing NoSuchCommand with suggestions is raised.
- An exact name or an alias always beats a prefix that would be ambiguous or would match something else.

### Interaction rules
- Exact command name beats an alias of the same spelling; add_alias for a spelling that already is a command name is allowed but never used.
- An empty token never prefix-matches.
- When ctx.resilient_parsing is true, no NoSuchCommand (including the ambiguity error) is raised; the existing (None, None, rest) result is returned.
- Hidden commands are reachable by exact name or alias but never by prefix.

### Edge cases and errors
- add_alias with a target that is not a registered command name at call time raises KeyError(target).
- add_alias with an empty alias raises ValueError("Alias must not be empty.").
- If an alias target is later removed from group.commands, resolution of the alias falls through to later steps as if the alias did not exist.
- A token that looks like an option (starts with a prefix) keeps the existing parse_args behaviour when nothing matches; it is not prefix-matched.

### Backward compatibility
- allow_prefix_match defaults to False and no aliases exist by default, so resolution is identical to before.
- CommandCollection and subclass overrides of get_command/list_commands keep working since lookup uses those hooks.

### Examples
```python
g = click.Group('g', allow_prefix_match=True)
@g.command()
def status(): click.echo('s')
@g.command()
def start(): click.echo('t')
runner.invoke(g, ['sta'])
```
Expected: exit_code 2; output contains "Ambiguous command 'sta'. Could be: start, status."

```python
g.add_alias('st', 'status'); runner.invoke(g, ['st'])
```
Expected: exit_code 0, output 's\n'

```python
runner.invoke(g, ['stat'])
```
Expected: exit_code 0, output 's\n' ('stat' is a prefix of only status)

### Acceptance criteria
- alias resolves and ctx.invoked_subcommand is the canonical name
- unique prefix resolves when allow_prefix_match=True
- ambiguous prefix yields the exact message
- prefix matching off by default gives the normal No such command error
- hidden commands are not prefix-matched but alias works
- bad alias target raises KeyError, empty alias ValueError

### Why it is novel
The report lists aliases and prefix matching as a gap not present in core; only a docs recipe exists. This design adds ordering and hidden/ambiguity rules.

### Why it is hard
Several precedence rules (exact, alias, normalize, prefix), hidden filtering and exact error text must all be honored together.

## 3. Choice prefix_match option with ambiguity detection

- Slug: `choice-prefix-match` · Category: **type conversion** · Estimated gold size: ~35 lines
- Attaches at: Choice.__init__ and Choice.convert (types.py:454-476).
- Gold edits: `src/click/types.py`
- New test file: `tests/test_types/test_Choice_prefix.py` · Regression: `tests/test_types/test_Choice.py`, `tests/test_info_dict.py`, `tests/test_options.py`
- Builds on: `src/click/types.py` (Choice, Choice.convert, Choice.normalize_choice, Choice.get_invalid_choice_message, ParamType.fail)

### Problem
Choice requires full values. CLIs with many enumerated values want unambiguous abbreviations ('--fmt y' for 'yaml').

### Public interface
- `Choice.__init__(self, choices, case_sensitive: bool = True, prefix_match: bool = False)`
- `Choice.prefix_match attribute`

### Behavior
- Conversion first normalizes the input with normalize_choice (so case_sensitive=False and token_normalize_func apply) and looks for an exact normalized match; if found it returns the original choice exactly as before, even when it is also a prefix of other choices.
- If no exact match and prefix_match is True and the normalized input is non-empty, collect the choices whose normalized form starts with it, in choice order.
- Exactly one candidate: return that original choice object (not the string).
- More than one candidate: self.fail("'js' is ambiguous: matches 'json', 'jsonl'.") using the raw input in single quotes and the normalized candidate forms in repr, in choice order joined by ', '.
- No candidate: the usual get_invalid_choice_message failure.

### Interaction rules
- Exact match beats prefix matching.
- With case_sensitive=False the prefix comparison happens on the casefolded values.
- With enum choices, prefixes compare against member names.
- prefix_match never applies to an empty string, which gives the normal invalid-choice error.

### Edge cases and errors
- The ambiguity failure is a BadParameter with ctx and param attached; through a CLI it exits with code 2 and reads "Invalid value for '--x': 'js' is ambiguous: matches 'json', 'jsonl'."
- Candidates are counted per original choice; if two original choices normalize to the same matching string both are listed and the result is ambiguous.
- Non-str input values are normalized with str() and then prefix-matched.
- get_metavar, shell_complete and get_missing_message are unchanged.

### Backward compatibility
- Default prefix_match=False keeps all conversion results and messages identical.
- to_info_dict output is unchanged (no new key), so existing info-dict tests pass.

### Examples
```python
c = click.Choice(['json','jsonl','yaml'], prefix_match=True)
c.convert('y', None, None)
```
Expected: 'yaml'

```python
c.convert('js', None, None)
```
Expected: raises BadParameter with message "'js' is ambiguous: matches 'json', 'jsonl'."

```python
c.convert('json', None, None)
```
Expected: 'json' (exact beats prefix)

### Acceptance criteria
- unique prefix returns original choice
- ambiguous prefix raises BadParameter with exact message
- exact match wins over longer choices
- case-insensitive prefix works with case_sensitive=False
- empty string is invalid
- default behaviour without prefix_match unchanged
- works end to end through an option via CliRunner

### Why it is novel
The report lists prefix matching for Choice as an unaddressed gap, absent from upstream lists.

### Why it is hard
Exact-vs-prefix precedence, normalization interplay, ordering of candidates, and exact message formatting.

## 4. max_attempts limit for prompt() and confirm()

- Slug: `prompt-max-attempts` · Category: **interactive input** · Estimated gold size: ~40 lines
- Attaches at: The while True loops in prompt (termui.py:168-286) and confirm (termui.py:328-342).
- Gold edits: `src/click/termui.py`
- New test file: `tests/test_utils/test_prompt_attempts.py` · Regression: `tests/test_utils/test_prompt.py`, `tests/test_termui.py`
- Builds on: `src/click/termui.py` (prompt, confirm, _build_prompt, _readline_prompt)

### Problem
prompt() and confirm() re-ask forever on invalid input, which can hang scripted sessions. A bounded retry count is wanted.

### Public interface
- `prompt(..., max_attempts: int | None = None) appended as last keyword`
- `confirm(..., max_attempts: int | None = None) appended as last keyword`

### Behavior
- max_attempts=None keeps unlimited retries.
- An attempt fails when: for prompt, value_proc raises UsageError, the answer is empty and default is None, or a confirmation mismatch occurs; for confirm, the answer is not y/yes/n/no (an empty answer with default None also counts).
- The normal error line is still echoed for a failed attempt (e.g. 'Error: invalid input'); when the number of failed attempts reaches max_attempts the function raises Abort instead of asking again.
- A valid answer on any attempt up to and including the max_attempts-th returns normally.
- confirm(abort=True) with a valid 'n' still raises Abort as before; a valid answer is never counted as a failed attempt.

### Interaction rules
- An empty answer accepted via default is a success and does not count.
- In prompt with confirmation_prompt, a mismatch counts as one failed attempt and the sequence restarts from the first question.
- KeyboardInterrupt/EOFError still raise Abort immediately regardless of attempts left.

### Edge cases and errors
- max_attempts < 1 (including 0 and negatives) raises ValueError("max_attempts must be at least 1.") before any input is read.
- max_attempts=1 with one bad answer echoes the error line then raises Abort.
- A bool max_attempts follows int semantics (True == 1).
- With hide_input the masked error line is still printed on the final failure before Abort.

### Backward compatibility
- Both functions keep their existing positional parameter order; the new keyword is last and defaults to None.
- Option prompts (Option.prompt_for_value) are unchanged and still unlimited.

### Examples
```python
stdin 'x\ny\n'; click.confirm('ok?', max_attempts=2)
```
Expected: returns True; output shows one 'Error: invalid input' line

```python
click.prompt('n', type=int, max_attempts=3) with stdin 'a\nb\n5\n'
```
Expected: returns 5

```python
click.prompt('n', type=int, max_attempts=2) with stdin 'a\nb\n5\n'
```
Expected: raises click.Abort after two 'Error: ...' lines

### Acceptance criteria
- unlimited by default
- prompt returns on the last allowed attempt
- Abort raised exactly when failures reach max_attempts
- confirm counts invalid input
- confirmation mismatch counts as one
- max_attempts=0 raises ValueError with exact message
- default-accepted empty answer does not count

### Why it is novel
The report lists re-prompt limits as a gap; absent from upstream lists (PromptBuilder PR is about formatting only).

### Why it is hard
Counting must span three different failure kinds in prompt (including the confirmation restart) while not counting accepted defaults.

## 5. ShellComplete completion de-duplication, sorting and truncation

- Slug: `completion-postprocess` · Category: **shell completion** · Estimated gold size: ~40 lines
- Attaches at: ShellComplete.get_completions (shell_completion.py:353-365), after obj.shell_complete returns.
- Gold edits: `src/click/shell_completion.py`
- New test file: `tests/test_shell_completion_postprocess.py` · Regression: `tests/test_shell_completion.py`
- Builds on: `src/click/shell_completion.py` (ShellComplete, ShellComplete.get_completions, ShellComplete.complete, CompletionItem, add_completion_class)

### Problem
get_completions returns whatever items the command tree produced, possibly duplicated (chained groups, repeated names) and unordered, and with no cap. Shell integrations want a controllable post-processing pipeline.

### Public interface
- `ShellComplete.dedupe_completions: bool = False (class attribute)`
- `ShellComplete.sort_completions: bool = False (class attribute)`
- `ShellComplete.max_completions: int | None = None (class attribute)`
- `ShellComplete.get_completions applies the pipeline to the list returned by obj.shell_complete`

### Behavior
- Order of stages: dedupe, then sort, then truncate.
- Dedupe (when True): items with the same (value, type) are collapsed to the first occurrence's position; if the first has help None or empty and a later duplicate has help, the kept item takes that later help text (its value and type unchanged).
- Sort (when True): stable sort by str(value).casefold(); ties keep prior order.
- Truncate (when max_completions is an int): keep only the first max_completions items.
- All three off/None (defaults) returns the list exactly as before.

### Interaction rules
- Truncation happens after sorting, so the kept items are the alphabetically first ones when sorting is enabled.
- Dedupe happens before truncation, so duplicates do not consume the quota.
- Settings are class attributes, so a subclass (e.g. registered via add_completion_class) applies them to its own get_completions and also to complete().

### Edge cases and errors
- max_completions=0 returns an empty list and complete() returns ''.
- A negative max_completions raises ValueError("max_completions must not be negative.") from get_completions.
- Items whose values differ only by case are not duplicates (comparison is exact) but sort adjacently with prior order as tie-break.
- Duplicates with different type (plain vs file) are kept both.

### Backward compatibility
- Defaults leave get_completions output identical for BashComplete, ZshComplete, FishComplete and PowerShellComplete.
- get_completions signature and the CompletionItem class are unchanged.

### Examples
```python
class C(ShellComplete):
    name='x'; source_template=''
    sort_completions=True; max_completions=2
cli = Group('cli', commands=[Command('b'), Command('a'), Command('c')])
[i.value for i in C(cli, {}, 'cli', '_CLI_COMPLETE').get_completions([], '')]
```
Expected: ['a', 'b']

```python
dedupe_completions=True on a chain group where a sibling name appears twice
```
Expected: each value appears once

```python
max_completions=0 with complete()
```
Expected: ''

### Acceptance criteria
- defaults unchanged
- dedupe keeps first position and fills missing help
- sort is casefold stable
- truncate after sort and dedupe
- max_completions=0 yields empty
- negative max_completions raises ValueError with exact message
- different types are not duplicates

### Why it is novel
Not in repo or upstream lists; get_completions is only mentioned as an override point in the report.

### Why it is hard
Stage ordering, help-merging dedupe and stable casefold sort must interact precisely.
