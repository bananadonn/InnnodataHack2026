# Feature plan: pallets/click @ `cf19179e8e2f`

Run `20261114-130238-pallets-click` · designed by `claude-sonnet-5-5` · checked against the repository by the pipeline.

## Variation strategy
Five features hit different layers: cross-parameter validation (core.py Option/Command.parse_args), a type's matching semantics (Choice), interactive input retry policy (termui.prompt), help-layout output (HelpFormatter), and filesystem type validation (Path). Each has its own interacting rule set (explicit-source eligibility, exact-vs-prefix precedence, attempt counting across error kinds, numbering/indent/width, suffix versus existence/dash/bytes).

## 1. Option conflicts_with and requires declarations

- Slug: `option-conflicts-requires` · Category: **cross-parameter validation** · Estimated gold size: ~60 lines
- Attaches at: Option.__init__ stores the attributes; Command.parse_args runs checks after the handle_parse_result loop.
- Gold edits: `src/click/core.py`
- New test file: `tests/test_option_conflicts.py` · Regression: `tests/test_options.py`, `tests/test_commands.py`, `tests/test_info_dict.py`
- Builds on: `src/click/core.py` (Option.__init__, Command.parse_args, Context.get_parameter_source, Context.fail, ParameterSource)

### Problem
Click has no declarative way to say two options are mutually exclusive or that one option needs another. Users hand-write callbacks that cannot tell explicit values from defaults.

### Public interface
- `click.Option.__init__(..., conflicts_with: Sequence[str] = (), requires: Sequence[str] = (), **attrs)`
- `Option.conflicts_with: tuple[str, ...]`
- `Option.requires: tuple[str, ...]`

### Behavior
- conflicts_with and requires are sequences of parameter NAMES (the python names, as in ctx.params). Stored as tuples on the Option.
- A parameter counts as 'explicit' if ctx.get_parameter_source(name) is ParameterSource.COMMANDLINE, ENVIRONMENT or PROMPT. DEFAULT_MAP, DEFAULT and no source are not explicit.
- Checks run in Command.parse_args after every parameter has been processed (before leftover-args check). Params are examined in the order of command.get_params(ctx).
- For each explicit option A and each name B in A.conflicts_with: if B is explicit, ctx.fail("Option 'A' cannot be used together with option 'B'.") where A is A.name and B is the listed name, each in single quotes, e.g. "Option 'json_' cannot be used together with option 'csv'." The first violation found raises.
- For each explicit option A and each name B in A.requires: if B is not explicit, ctx.fail("Option 'A' requires option 'B'."). conflicts_with checks for an option are done before its requires checks.
- Conflicts are symmetric: declaring conflicts_with on only one of the two options is enough to trigger the error.
- Failure is a UsageError (exit code 2) raised through ctx.fail.

### Interaction rules
- Only explicit sources count: an option that conflicts but whose value came from default or default_map does not trigger an error, and a required-by option satisfied only by default still counts as missing.
- When option A both conflicts with C and requires B and both are violated, the conflict error is reported first.
- Under ctx.resilient_parsing (shell completion) no validation is performed.
- Names that match no parameter on the command are treated as non-explicit (so requires fails, conflicts never fires).

### Edge cases and errors
- conflicts_with='json' (a bare str) raises TypeError("'conflicts_with' must be a sequence of names, not a string.") at Option construction; same for requires with "'requires' ...".
- A name appearing in its own conflicts_with raises TypeError("Option 'x' cannot conflict with itself.").
- Flag options with value False given explicitly (--no-x) are still explicit.
- Empty sequences (default) disable the feature entirely.

### Backward compatibility
- Options without these kwargs behave identically; parse_args does no extra work visible to users.
- Option.to_info_dict is unchanged (does not include the new keys).

### Examples
```python
@click.command()
@click.option('--json','json_', is_flag=True, conflicts_with=['csv'])
@click.option('--csv', is_flag=True)
def cli(json_, csv): pass
runner.invoke(cli, ['--json','--csv'])
```
Expected: exit_code 2; stderr contains "Error: Option 'json_' cannot be used together with option 'csv'."

```python
@click.option('--user', requires=['password'])
@click.option('--password')
runner.invoke(cli, ['--user','a'])
```
Expected: exit_code 2; output contains "Option 'user' requires option 'password'."

```python
@click.option('--a', default='x', conflicts_with=['b'])
@click.option('--b')
runner.invoke(cli, ['--b','1'])
```
Expected: exit_code 0 because a came from DEFAULT

### Acceptance criteria
- Two conflicting explicit options exit 2 with the exact conflict message.
- requires missing option fails with exact message; supplying it via environment variable satisfies it.
- Defaults do not count as explicit.
- Bare string argument raises TypeError with exact message.
- Conflict reported before requires failure; no validation when resilient_parsing.

### Why it is novel
The report lists cross-parameter validation as a gap; nothing in the repo or upstream-do-not-propose list covers it.

### Why it is hard
Eligibility depends on parameter sources, ordering of checks, and name vs. declaration-string confusion (python name, not flag).

## 2. Choice allow_prefix unambiguous abbreviation

- Slug: `choice-prefix-matching` · Category: **type conversion** · Estimated gold size: ~45 lines
- Attaches at: Choice.__init__ and Choice.convert fallback after exact-match failure.
- Gold edits: `src/click/types.py`
- New test file: `tests/test_types/test_Choice_prefix.py` · Regression: `tests/test_types/test_Choice.py`, `tests/test_info_dict.py`, `tests/test_options.py`
- Builds on: `src/click/types.py` (Choice, Choice.normalize_choice, Choice.get_invalid_choice_message, ParamType.fail)

### Problem
Choice requires full values. CLIs often want 'pro' to resolve to 'production' when unambiguous.

### Public interface
- `click.Choice.__init__(self, choices, case_sensitive=True, allow_prefix=False)`
- `Choice.allow_prefix: bool`

### Behavior
- With allow_prefix=True, convert first tries the existing exact match (using normalize_choice, honoring case_sensitive and token_normalize_func); an exact match always wins.
- If no exact match, the normalized input is compared with str.startswith against each normalized choice. Exactly one match returns the ORIGINAL choice object (e.g. the Enum member or int).
- Zero matches fail with the existing get_invalid_choice_message.
- Two or more matches fail with BadParameter message "{value!r} is ambiguous; it could be one of {matches}." where value is the raw input and matches is ', '.join(repr(m)) of the normalized matching choices in declaration order, e.g. "'pr' is ambiguous; it could be one of 'prod', 'prof'."
- An empty string never prefix-matches (it is only valid if an exact normalized '' choice exists).
- shell_complete is unchanged.

### Interaction rules
- Exact match beats prefix: choices ['pro','prod'] with value 'pro' returns 'pro'.
- With case_sensitive=False, prefix comparison uses the casefolded normalized forms, so 'PR' matches 'production'.
- Duplicate normalized choices that match the prefix are deduplicated by normalized value (preserving order) before the ambiguity decision.

### Edge cases and errors
- allow_prefix=True with a single choice: prefix still resolves, invalid values still use singular invalid-choice message.
- Value that is not str (e.g. int 1 with choices [10, 11]) is normalized via str() so '1' prefix matches 10 and 11 -> ambiguous.
- allow_prefix non-bool is not validated.
- ctx=None is tolerated.

### Backward compatibility
- Default allow_prefix=False leaves all conversion identical.
- to_info_dict output of Choice is unchanged by default; tests/test_info_dict stays valid.

### Examples
```python
click.Choice(['production','staging'], allow_prefix=True).convert('pro', None, None)
```
Expected: 'production'

```python
click.Choice(['prod','prof'], allow_prefix=True).convert('pr', None, None)
```
Expected: BadParameter: "'pr' is ambiguous; it could be one of 'prod', 'prof'."

```python
click.Choice(['Alpha','beta'], case_sensitive=False, allow_prefix=True).convert('AL', None, None)
```
Expected: 'Alpha'

### Acceptance criteria
- Unique prefix returns original choice.
- Ambiguous prefix raises BadParameter with exact message.
- Exact match wins over longer prefix match.
- Case-insensitive prefix works and returns original casing.
- Default behaviour rejects prefixes with the old message.

### Why it is novel
Choice has no abbreviation support; NoSuchCommand suggestions are different and listed upstream.

### Why it is hard
Precedence of exact vs. prefix, normalization and case folding, and returning original objects.

## 3. prompt max_attempts retry limit

- Slug: `prompt-max-attempts` · Category: **interactive input** · Estimated gold size: ~25 lines
- Attaches at: Outer while loop in prompt around value_proc and confirmation comparison (termui.py ~260-286).
- Gold edits: `src/click/termui.py`
- New test file: `tests/test_utils/test_prompt_attempts.py` · Regression: `tests/test_utils/test_prompt.py`, `tests/test_termui.py`
- Builds on: `src/click/termui.py` (prompt)

### Problem
click.prompt loops forever on invalid input, which hangs scripted sessions.

### Public interface
- `click.prompt(text, ..., show_choices=True, max_attempts: int | None = None)`

### Behavior
- max_attempts=None keeps infinite retry.
- An 'attempt' is one full pass of the outer loop that fails: a UsageError from value_proc, or a confirmation mismatch. Empty input with default=None (inner loop re-ask) does not count.
- After the Nth failed attempt (N=max_attempts) the usual 'Error: ...' message is echoed and then Abort is raised instead of reprompting.
- A successful attempt returns normally even on the last allowed try.
- Error message echoing for the failing attempts is unchanged (including hide_input masking).

### Interaction rules
- Failed attempts from value_proc errors and from confirmation mismatch share one counter.
- The default value is also run through value_proc; if it fails it counts as an attempt.
- Aborts from KeyboardInterrupt/EOFError are unaffected.

### Edge cases and errors
- max_attempts=0 or negative raises ValueError('max_attempts must be at least 1.') before any prompting.
- max_attempts=1 with a valid first answer returns it.
- Non-int values such as 1.5 are not specified.
- With confirmation_prompt and max_attempts=1, a mismatch echoes 'Error: The two entered values do not match.' then raises Abort.

### Backward compatibility
- All existing calls behave identically with max_attempts omitted.
- Positional argument order of existing parameters unchanged (new kwarg last).

### Examples
```python
monkeypatch stdin 'x\ny\nz\n'; click.prompt('n', type=int, max_attempts=2)
```
Expected: outputs "Error: 'x' is not a valid integer." twice then raises Abort

```python
stdin 'x\n5\n'; click.prompt('n', type=int, max_attempts=2)
```
Expected: 5

```python
click.prompt('n', max_attempts=0)
```
Expected: ValueError: max_attempts must be at least 1.

### Acceptance criteria
- Abort after N failures.
- Success on last attempt returns value.
- ValueError for <1 with exact message and no input read.
- Mismatches count toward the limit.
- Default behavior unchanged.

### Why it is novel
Report names a missing retry limit as a gap; not in upstream lists (PromptBuilder is formatting only).

### Why it is hard
Which events count as attempts, ordering of echo versus Abort, and validation before I/O.

## 4. HelpFormatter.write_list bulleted and numbered lists

- Slug: `formatter-write-list` · Category: **help layout** · Estimated gold size: ~40 lines
- Attaches at: New method next to HelpFormatter.write_text.
- Gold edits: `src/click/formatting.py`
- New test file: `tests/test_formatter_list.py` · Regression: `tests/test_formatting.py`
- Builds on: `src/click/formatting.py` (HelpFormatter, HelpFormatter.write, wrap_text, HelpFormatter.indentation)

### Problem
Help text lists need hanging indents; only the \b marker preserves layout and does not wrap.

### Public interface
- `HelpFormatter.write_list(self, items: Iterable[str], bullet: str | None = '*', start: int | None = None) -> None`

### Behavior
- Each item is written as one wrapped block with a hanging indent; the marker is followed by one space.
- Marker for bullet style is `bullet`; if start is not None, items are numbered 'start.', 'start+1.', ... and bullet is ignored.
- The marker starts at self.current_indent spaces; continuation lines are indented to current_indent + len(marker) + 1.
- Wrapping uses wrap_text(item, self.width, initial_indent=marker_prefix, subsequent_indent=hanging) so width counts the full line; each item ends with '\n'.
- Numbered markers are right-aligned to the widest marker in the list so text columns align, e.g. ' 9.' and '10.'.
- An empty items iterable writes nothing.

### Interaction rules
- Respects indent()/dedent() and section(): inside a section the list is indented by indent_increment.
- bullet=None with start=None writes items with no marker and hanging indent of current_indent only (plain indented blocks).

### Edge cases and errors
- start negative raises ValueError('start must be non-negative.').
- Empty bullet string '' behaves like bullet=None.
- An empty item string writes just the marker (rstripped) and newline.
- Non-str items raise whatever wrap_text raises (not specified).

### Backward compatibility
- No existing method changes; write_dl/write_text output unchanged.
- HelpFormatter subclasses overriding write still intercept the output since write_list uses self.write.

### Examples
```python
f=click.HelpFormatter(width=20); f.write_list(['one','two words here and more'])
f.getvalue()
```
Expected: '* one\n* two words here and\n  more\n'

```python
f=click.HelpFormatter(width=40); f.write_list(['a']*10, start=1) ; first two lines
```
Expected: ' 1. a' then ' 2. a' ... '10. a' lines

```python
f=click.HelpFormatter(width=40); f.indent(); f.write_list(['x'], bullet='-')
f.getvalue()
```
Expected: '  - x\n'

### Acceptance criteria
- Bullet wrapping hanging indent exact.
- Numbered alignment for 9->10 crossing.
- Indent respected.
- Empty list writes nothing.
- Negative start raises ValueError.

### Why it is novel
Hanging-indent list helpers are listed as a gap in formatting.py and absent from the repo.

### Why it is hard
Alignment arithmetic, hanging indent widths and interaction with current_indent.

## 5. Path suffixes check

- Slug: `path-suffix-validation` · Category: **filesystem validation** · Estimated gold size: ~40 lines
- Attaches at: Path.__init__ and start of the non-dash branch in Path.convert (types.py ~1172).
- Gold edits: `src/click/types.py`
- New test file: `tests/test_types/test_Path_suffixes.py` · Regression: `tests/test_types/test_Path.py`, `tests/test_info_dict.py`
- Builds on: `src/click/types.py` (Path, Path.convert, ParamType.fail, Path.coerce_path_result)

### Problem
click.Path cannot restrict file extensions, so users validate in callbacks.

### Public interface
- `click.Path.__init__(..., executable=False, suffixes: Sequence[str] | None = None)`
- `Path.suffixes: tuple[str, ...] | None`

### Behavior
- suffixes is a sequence of extensions including the dot, e.g. ('.txt','.md'). Stored lower-cased as a tuple, or None.
- In convert, after the dash short-circuit, the final path component of the ORIGINAL value (os.fsdecode, os.path.basename) lower-cased must end with one of the suffixes; compare via str.endswith, so '.tar.gz' works as a multi-dot suffix.
- Failure: self.fail("{name} {filename!r} must end with one of: .txt, .md.") using name.title() and format_filename(value) like other messages, suffixes joined by ', '.
- The suffix check runs before os.stat, so it applies even when exists=False and the file does not exist.
- Directories are also subject to the check (a directory without a matching suffix fails).

### Interaction rules
- allow_dash with value '-' skips the suffix check like all other checks.
- The suffix check precedes exists/file/dir checks: a missing file with a bad suffix and exists=True reports the suffix error.
- Matching is case-insensitive on the value ('A.TXT' passes for '.txt').
- bytes values are decoded with os.fsdecode for the check.

### Edge cases and errors
- suffixes given as a bare str raises TypeError("'suffixes' must be a sequence of strings, not a string.").
- A suffix not starting with '.' raises ValueError("Suffix 'txt' must start with a dot.").
- Empty sequence is treated as None (no check).
- Basename without extension e.g. 'Makefile' fails.

### Backward compatibility
- suffixes=None default leaves behaviour identical.
- Path.to_info_dict is unchanged.

### Examples
```python
click.Path(suffixes=['.txt']).convert('a.TXT', None, None)
```
Expected: 'a.TXT'

```python
click.Path(suffixes=['.txt','.md']).convert('a.py', None, None)
```
Expected: BadParameter: "Path 'a.py' must end with one of: .txt, .md." (name is 'File' if dir_okay=False)

```python
click.Path(suffixes=['.tar.gz']).convert('x.tar.gz', None, None)
```
Expected: 'x.tar.gz'

### Acceptance criteria
- Allowed suffix case-insensitive passes.
- Rejected suffix raises with exact message.
- Suffix error precedes exists error.
- Dash skips check with allow_dash.
- Bare str and missing dot raise exact errors.

### Why it is novel
The report lists extension checks as a Path gap; not present upstream.

### Why it is hard
Check ordering relative to stat and dash, case folding, multi-dot suffixes, and constructor validation.
