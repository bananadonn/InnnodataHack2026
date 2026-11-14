# Candidate features: pallets/click @ `cf19179e8e2f`

Proposed by `claude-opus-5-5`. Novelty audited by `claude-sonnet-5-5` (web). Value audited by `claude-sonnet-5-5` (web). Difficulty audited by `claude-opus-5-5`. Selection is done by the pipeline, not a model.

## Summary

| Candidate | Category | Novelty | Value | Difficulty | Outcome |
|---|---|---|---|---|---|
| `option-repeat-policy` | option parsing | novel | 2/5 | 3/5 | selected |
| `async-command-callbacks` | command invocation | novel | 3/5 | 4/5 | selected |
| `path-must-not-exist` | parameter type validation | novel | 3/5 | 2/5 | reserve |
| `option-show-range-toggle` | help extras | novel | 3/5 | 2/5 | reserve |
| `command-aliases` | subcommand dispatch | novel | 4/5 | 4/5 | selected |
| `group-default-command` | subcommand dispatch | drop_in | 3/5 | 4/5 | rejected |
| `option-help-sections` | help layout | novel | 4/5 | 2/5 | reserve |
| `command-help-sections` | help layout | novel | 3/5 | 2/5 | reserve |
| `exception-error-style` | error output | novel | 3/5 | 2/5 | reserve |
| `color-option-and-env` | terminal color policy | drop_in | 4/5 | 3/5 | rejected |
| `option-value-separator` | multi-value options | novel | 2/5 | 4/5 | selected |
| `mutually-exclusive-params` | cross-parameter validation | novel | 3/5 | 2/5 | reserve |
| `config-file-option` | configuration | drop_in | 2/5 | 3/5 | rejected |
| `choice-enum-by-value` | parameter types | novel | 3/5 | 2/5 | selected (filler, below the difficulty floor) |
| `help-styles` | help styling | novel | 2/5 | 2/5 | reserve |

## Variation strategy
The 14 candidates cover 11 categories: invocation/async, path validation, help extras, subcommand dispatch (aliases and default command), help layout (option sections and command sections), error output styling, terminal colour policy, multi-value options, cross-parameter validation, config files, enum choices and help styling. Their primary files are core.py, types.py, exceptions.py, decorators.py, formatting.py and _compat.py. They also vary in shape:
- Some are local type tweaks: Path must_not_exist, Choice enum_by_value, show_range.
- Some change the dispatch pipeline and must stay consistent across invoke, completion, default_map/auto-envvar keying and error suggestions: aliases, default_command, async.
- Some change the value pipeline across every source (command line, env var, default_map, default, prompt): separator, config_option, mutually_exclusive.
- Some change rendering across help, usage-in-errors and colour stripping: help sections, help_styles, error_style, color_option.
Every rule is tied either to the cited request or to an existing click convention: ParameterSource explicitness, Context inheritance of color and show_default, Option show_* flags, info_name keying of default_map and auto envvars, and separate write_dl calls per section. Each trap comes from a real collision with existing code, such as CliRunner patching should_strip_ansi, Context resources closing before a coroutine runs, exact-dict info tests, the termui→exceptions import cycle, and prompt input reaching type_cast_value as a bare string.

## `option-repeat-policy`: on_repeat policy for non-multiple options given more than once

**Outcome:** selected: novel, difficulty 3/5, value 2/5; value audit doubts it fits the library

- Category: option parsing · Gold edits: `src/click/parser.py`, `src/click/core.py`
- Problem: When a single-value option is given twice (`--env prod --env dev`), the last value wins silently, which hides mistakes in long command lines. Some CLIs want first-wins or an error.

**Novelty: novel.** Grep of repo/src found no on_repeat. Issue #955 was closed in 2018 as a declined request: davidism said last-wins is intentional. That is demand evidence but no implementation, so the candidate stays novel. No open PR or add-on was found. The PR search for 'repeated option' found only an unrelated, rejected metavar-help PR (#3839). I did not check cloup, click-option-group, click-extra, typer, argparse or docopt directly for this capability.

- Closest existing: Nothing implements it. Issue #955 asked for the same thing (forbid passing an option twice) and was closed without adding it. A workaround is multiple=True plus a manual length check.
- Evidence: [https://github.com/pallets/click/issues/955](https://github.com/pallets/click/issues/955): Closed in 2018 without adding the feature. The maintainer said last-wins is intentional, and an allow_repeat=False flag was proposed and declined.
- Evidence: [https://github.com/pallets/click/pulls?q=repeated+option](https://github.com/pallets/click/pulls?q=repeated+option): No open PR. The only repeated-option PR is #3839, which is about help metavars and was rejected.
- Evidence: [https://github.com/pallets/click/issues?q=forbid+option+passed+multiple+times](https://github.com/pallets/click/issues?q=forbid+option+passed+multiple+times): Shows #955 as the only matching issue.

**Value: 2/5** (fits the library: no). I found no pallets/click issue asking for this. My issues search for repeated options returned an unrelated PR, and the lightrun page that was meant to cover a GitHub issue returned only a blog index. A search snippet says a 2018 community comment suggested using multiple=True and raising BadOptionUsage. That snippet is the only trace of a Click request, and I could not verify it. The 'first' policy has no stated use case. The change touches the parser internals and the option constructor, so it adds a lot of surface for little shown demand.

- Who benefits: Authors of CLIs with long command lines who want duplicate single-value options rejected. Probably few, and the existing workaround (multiple=True plus a length check) is simple.
- User evidence: [https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/55430668/display-error-when-argument-is-specified-multiple-times](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/55430668/display-error-when-argument-is-specified-multiple-times): A Stack Overflow question about error on repeated argument. It appeared in search results, but I did not open it, so I cannot say whether it concerns argparse or Click.
- User evidence: [https://github.com/astral-sh/uv/issues/3248](https://github.com/astral-sh/uv/issues/3248): A uv issue that appeared in search results. I did not open it. Per the search snippet, it asks for a hard error rather than last-wins, in a different tool.
- Contrived rule (to drop): 'first' with a bool flag that has secondary opts must give the first occurrence's const
- Contrived rule (to drop): Counting per Option object so that feature switches sharing a dest are not repeats
- Contrived rule (to drop): on_repeat other than 'last' with multiple=True or count=True raises TypeError
- Contrived rule (to drop): Three policy values ('last', 'first', 'error') where users mostly ask for an error

**Difficulty: 3/5.** The core is a seen-set keyed by obj plus a policy branch. The traps are real, but once the spec says 'per Option object, including secondary opts', the model only needs `id(self.obj)` in state. The spelling threading touches two call sites. Several rules exist, but they mostly reduce to one well-specified mechanism. One real trap (the shared obj across two _Options) puts this at a solid 3.

- Interacting rules: 4 · Survives an explicit spec: yes
- Likely failure: Tracking repeats per _Option instance or per dest. The first misses `--shout --no-shout`; the second flags `--upper --lower`. A second likely failure: in 'first' mode, skipping `state.order.append` inconsistently, or reporting the first spelling because the opt string isn't threaded through to process.
- Confirmed trap: Bool flags with secondary opts register two _Option objects that share the same `obj` and `dest` (core.py:3336-3346). So repeats have to be tracked by `obj` identity, not by spelling and not by the _Option instance. Tracking per _Option instance misses `--shout --no-shout`.
- Confirmed trap: Feature switches are separate Option objects that share a dest. Keying on `dest` (which is what `state.opts` uses, parser.py:171-173) wrongly flags them as repeats.
- Confirmed trap: For 'first' with a bool flag, `--no-shout --shout` must keep the const of the first occurrence. Each _Option carries its own const (parser.py:162,173), so the second _Option's process must be skipped entirely, not merely prevented from overwriting a value of the same kind.
- Confirmed trap: _Option.process(value, state) never receives the spelling (parser.py:169, called at 388 and 418), so naming the second-occurrence spelling in the error means changing the signature and both call sites, in _match_long_opt and _match_short_opt.
- Confirmed trap: For 'first', the repeated option's value must still be consumed from rargs. `_get_value_from_state` runs before process (parser.py:378, 413). If the skip happens before value consumption, 'b' leaks into positional args.
- Suggested hardening: Define how 'first' interacts with state.order. The skipped occurrence must still be appended to state.order, because eager processing order (`--version` repeated after `--help`) is decided from order (iter_params_for_processing). Also, `-ee` short-opt clusters must count as two occurrences, with the error naming '-e'.

## `async-command-callbacks`: Run async def command callbacks automatically

**Outcome:** selected: novel, difficulty 4/5, value 3/5

- Category: command invocation · Gold edits: `src/click/core.py`
- Problem: Writing a command, group callback or result callback as `async def` today returns an unawaited coroutine. Context.invoke (src/click/core.py:861-911) just calls `callback(*args, **kwargs)` and returns the result, so users see 'coroutine was never awaited' and the body never runs. Users have to wrap every callback in asyncio.run or switch to the asyncclick fork.

**Novelty: novel.** Grep of repo/src found no iscoroutine. Issue #2033 ('Basic async support') is open, which is demand only. PR #3419 'Support async command callbacks' was closed as rejected on May 12, 2026, the day it opened. It carries a 'rejected AI' label and no technical discussion, so it is not in progress. The web search shows stock Click has no native async support. The fork is a separate package, not a drop-in for core.

- Closest existing: The asyncclick fork runs async commands via anyio. Safir's run_with_asyncio decorator is a per-command wrapper. Neither is in pallets/click, and neither has the nested ctx.invoke awaitable semantics in the candidate.
- Evidence: [https://github.com/pallets/click/pulls?q=async](https://github.com/pallets/click/pulls?q=async): PR #3419 'Support async command callbacks' is closed and labeled rejected. There are no open async PRs.
- Evidence: [https://github.com/pallets/click/pull/3419](https://github.com/pallets/click/pull/3419): Closed by davidism the day it was opened. The page shows only a 'rejected AI' label and no technical objections.
- Evidence: [https://github.com/pallets/click/issues?q=async+callback](https://github.com/pallets/click/issues?q=async+callback): Issues #2033 (basic async support) and #2360 (embedding in asyncio apps) are both open.

**Value: 3/5** (fits the library: yes). The demand is real and long-standing, and workarounds are widespread. Maintainers are lukewarm, though: davidism wants a concrete use case and notes that asyncio.run works, and mitsuhiko raised nesting concerns, so this outline's nested-invoke design touches exactly that open question. There is no merged precedent. The idea of auto-running async callbacks has some maintainer backing, but the outline's dual sync/awaitable ctx.invoke is heavy and not something users asked for.

- Who benefits: Developers with asyncio-based application code who write async def commands. Many hit it, and today they use a asyncio.run wrapper, safir's run_with_asyncio, or the asyncclick fork. Typer supports async commands natively.
- User evidence: [https://github.com/pallets/click/issues/2033](https://github.com/pallets/click/issues/2033): Open since 2021 with 23 comments. davidism said auto-starting an event loop for async def callbacks is the most plausible addition, but also doubted the need and noted that asyncio.run already works. mitsuhiko worried about recursive subcommand invocation. Users want Context.with_resource and call_on_close to be async-aware.
- User evidence: [https://github.com/pallets/click/issues?q=async](https://github.com/pallets/click/issues?q=async): PR #3419 'Support async command callbacks' was closed and labeled 'rejected AI'. The page does not show maintainer reasoning, and the label may refer to the PR's AI origin. #2033 and #2360 are still open.
- User evidence: [https://safir.lsst.io/user-guide/click.html](https://safir.lsst.io/user-guide/click.html): Safir ships a run_with_asyncio decorator, which shows downstream projects work around the gap.
- Contrived rule (to drop): Returning an awaitable from ctx.invoke when a loop is already running, and re-entering the sub-context on await. This is a complex dual-mode return type that mitsuhiko's design concern points at.

**Difficulty: 4/5.** The first half (asyncio.run inside the with block, checking the returned value) is easy once spelled out. The nested-loop requirement is the real difficulty: the context must be re-entered when the awaitable is awaited, augment_usage_errors must be preserved, and sync-from-loop behaviour must stay unchanged. The spec states this, but the obvious implementation is subtly wrong, and tests can check get_current_context and resource cleanup inside the nested sub-command. Two interacting execution paths with real traps make this a 4.

- Interacting rules: 5 · Survives an explicit spec: yes
- Likely failure: The asyncio.run path will work. In the running-loop path, the model will most likely return the raw coroutine, or an awaitable that doesn't re-enter the sub-context. The sub-command then sees the parent context, or with_resource files are closed before the body runs. Also likely: using asyncio.get_event_loop() or another wrong running-loop detection, and leaking 'never awaited' warnings.
- Confirmed trap: The coroutine must be driven inside `with augment_usage_errors(self), ctx:` (core.py:910-911). Running it afterwards breaks get_current_context and closes resources too early, because ctx.__exit__ closes the context when depth reaches 0 (core.py:564-568).
- Confirmed trap: Detection has to look at the returned object. pass_context-style wrappers hide coroutine-function-ness.
- Confirmed trap: In the nested case (a loop is already running), the sub-context created by _make_sub_context (core.py:891) gets entered and exited (and closed) by the sync `with` block before the caller awaits. The returned awaitable must re-enter ctx and augment_usage_errors around the await. The callback has to be called before you know whether it is async, because sync callbacks must behave exactly as before. So the callback is called in the sync block, and the returned coroutine is wrapped in an async function that re-enters ctx. Since the first exit already ran close() on an empty stack, resources registered during the body attach to the re-entered context. Getting this right is subtle.
- Confirmed trap: Chain mode collects `sub_ctx.command.invoke(sub_ctx)` results (core.py:2083-2085). This is only correct if the loop runs in Context.invoke, which Command.invoke reaches at core.py:1414.

## `path-must-not-exist`: click.Path(must_not_exist=True): reject paths that already exist

**Outcome:** reserve: novel, difficulty 2/5, value 3/5, not needed for the top 5

- Category: parameter type validation · Gold edits: `src/click/types.py`
- Problem: click.Path can require that a path exists, but it cannot require that a path does not exist. With exists=False, a missing path skips every check (src/click/types.py:1176-1180) and an existing path passes. So a command that creates an output file cannot refuse to overwrite it without a custom type or callback.

**Novelty: novel.** Grep of repo/src found no must_not_exist. Issue #1428 has been open since 2019. No PR for it was found. The PR search for Path exists returned nothing relevant. The web search found no Click release with a must-not-exist mode. The only existing implementation found is a project-specific subclass. cloup types appeared in the search results, but I did not open them, so I can't say whether cloup adds this.

- Closest existing: Issue #1428, 'allow checking for path non-existance', is open with no PR. The LSST Butler MWPath subclass implements a tri-state exists. That is an ad-hoc subclass, not click.Path(must_not_exist=True), and it is not in click or an add-on library.
- Evidence: [https://github.com/pallets/click/issues?q=Path+must_not_exist+OR+%22does+not+exist%22](https://github.com/pallets/click/issues?q=Path+must_not_exist+OR+%22does+not+exist%22): #1428 'allow checking for path non-existance' is open. No related PR was found.
- Evidence: [https://github.com/pallets/click/pulls?q=Path+exists](https://github.com/pallets/click/pulls?q=Path+exists): No open PRs, and no closed PR implements an existence rejection.

**Value: 3/5** (fits the library: yes). The need is evidenced and a downstream subclass exists. The maintainer's stated objection is to the API shape, since a separate boolean allows nonsensical combinations. The outline uses exactly that shape and adds a TypeError for the exists=True combination. The semantics are small and sensible, but the design conflicts with davidism's stated preference.

- Who benefits: Authors of commands that create output files and want to refuse overwrites, such as init or export commands. It is a common need, but many want prompting, --force or appending instead.
- User evidence: [https://github.com/pallets/click/issues/1428](https://github.com/pallets/click/issues/1428): Open since 2019. davidism declined separate flags in 2020 and suggested a custom type or callback, because handling an existing file can mean append, prompt, fail or rename. He said he would prefer exists=None/True/False if it were added. jpmckinney (2024) wanted it. A contributor proposed a 'state' parameter.
- User evidence: [https://pipelines.lsst.io/v/daily/api/lsst.daf.butler.cli.utils.MWPath.html](https://pipelines.lsst.io/v/daily/api/lsst.daf.butler.cli.utils.MWPath.html): LSST Data Butler subclasses click.Path as MWPath, where exists=False means the path must not exist. This is a downstream workaround.
- User evidence: [https://jsr.io/@optique/run/doc/valueparser/~/PathOptionsMustNotExist](https://jsr.io/@optique/run/doc/valueparser/~/PathOptionsMustNotExist): Optique, a Node/Deno parser, has mustNotExist for output files to prevent accidental overwrites. It is a different ecosystem, so it only shows that the idea is useful elsewhere.
- Contrived rule (to drop): Dangling symlinks are rejected via lexists semantics. This is reasonable, but only a few users would ask for it.
- Contrived rule (to drop): Message title-casing by type name and a separate must_not_exist flag. davidism explicitly disfavored a separate flag and wanted exists=None/True/False instead, so the API shape contradicts maintainer preference.

**Difficulty: 2/5.** One early-return branch inside convert. Every trap disappears once the spec says 'use lexists, put the check first, inside the not-dash branch'. The only genuine interaction is resolve_path versus dangling symlinks, which the proposer missed.

- Interacting rules: 4 · Survives an explicit spec: no
- Likely failure: Using the existing os.stat try/except as the existence test, which lets dangling symlinks through. Or checking lexists after realpath when resolve_path=True.
- Confirmed trap: os.stat follows symlinks and raises for dangling links (types.py:1176-1180), so the existence test must use os.path.lexists.
- Confirmed trap: The check must come before the file_okay/dir_okay checks (types.py:1189-1204).
- Confirmed trap: The dash shortcut (types.py:1169-1172) already bypasses everything, as long as the new check is placed inside `if not is_dash`.
- Confirmed trap: Missed by the proposer: with resolve_path=True, os.path.realpath (types.py:1174) resolves a dangling symlink to its nonexistent target, so lexists(resolved) is False and the dangling link slips through. The rule 'check on the resolved path' conflicts with the 'dangling symlinks are rejected' rule, and the spec doesn't settle which wins.
- Rejected trap: Adding the key to to_info_dict is only a trap if the model chooses to add it. The spec says not to, so it's a single explicit instruction rather than an interaction.
- Suggested hardening: Require that with resolve_path=True the dangling-symlink check runs on the original value (lexists(value)) before resolution, while the returned path is still the resolved one. And state that must_not_exist with dir_okay=False rejects an existing directory with the 'already exists' message, not 'is a directory'. This forces explicit ordering between resolution, the lexists check and the type checks.

## `option-show-range-toggle`: show_range on Option and Context to hide range text in help

**Outcome:** reserve: novel, difficulty 2/5, value 3/5, not needed for the top 5

- Category: help extras · Gold edits: `src/click/core.py`
- Problem: Option.get_help_extra always adds the _NumberRangeBase description (core.py:3491-3499), except for count options with the implicit IntRange(min=0). An option such as `-v` with count=True and type=IntRange(0, 3) therefore always shows '[0<=x<=3]', and the only workaround is subclassing the type.

**Novelty: novel.** Grep of repo/src found no show_range. #2679 has no branches or PRs. No PR hides the range in help. The only related PRs, #1586 and #2084, add or fix range display. The maintainer wants a different design, but there is no accepted work under way, so this is not in_progress. The web search found no show_range option.

- Closest existing: Nothing implements it. Issue #2679 is open with no linked PR. davidism wants the fix to come through a planned help-formatter refactor in which options collect extra display fields from their type. A fork commit and a _describe_range override are workarounds only.
- Evidence: [https://github.com/pallets/click/issues/2679](https://github.com/pallets/click/issues/2679): Open request. davidism said 'eventually', tied to a help formatter refactor. No linked PR, and the only code is a fork commit.
- Evidence: [https://github.com/pallets/click/pulls?q=show_range+OR+range+help](https://github.com/pallets/click/pulls?q=show_range+OR+range+help): No PR hides the range. #1586 and #2084 are the only matches and are not about hiding it.

**Value: 3/5** (fits the library: yes). The demand is a single issue, and it has a workable workaround. The maintainer is receptive but explicitly does not want more per-feature special cases, preferring a generic mechanism that collects extras from the type. A show_range boolean on both Option and Context goes against that stated direction. It is useful for the few users it affects.

- Who benefits: Authors with IntRange or FloatRange options, such as clamped -v counters, who find the auto-shown range noisy or misleading. It is a narrow cosmetic need.
- User evidence: [https://github.com/pallets/click/issues/2679](https://github.com/pallets/click/issues/2679): Requested in Feb 2024 for a -v count with a clamped IntRange. davidism said 'eventually' it would be worth doing, but through a planned help-formatter refactor and not another special case. gar1t shared a workaround that subclasses IntRange and overrides the range description. The issue is still open.
- User evidence: [https://github.com/pallets/click/issues?q=IntRange+help+range](https://github.com/pallets/click/issues?q=IntRange+help+range): The range display was added deliberately in PR #1586, merged in 2020. #2679 is the only request I found to hide it.
- Contrived rule (to drop): A Context-level show_range inherited from the parent, mirroring show_default. It adds a context setting that nobody asked for, and the issue only asks for an option-level toggle.
- Contrived rule (to drop): show_range=True does not reveal the implicit count range. This is a special case.

**Difficulty: 2/5.** This copies an existing show_default precedence pattern, in a single file, with three almost independent edits. It's easy for a small model given an explicit spec.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Forgetting parent inheritance in Context.__init__, or writing `self.show_range or ctx.show_range`, which wrongly lets ctx=False override option=True semantics. In practice it is easy to copy the show_default pattern directly.
- Confirmed trap: The range is added in get_help_extra (core.py:3491-3499) and consumed by get_help_record (core.py:3412-3413). Gating it in get_help_extra handles both.
- Confirmed trap: The Context needs parent inheritance mirroring show_default (core.py:504-508).
- Confirmed trap: The implicit count range exclusion (core.py:3494) must stay, even when show_range=True.
- Rejected trap: Changing _describe_range is an unlikely choice when the spec says to decide at the Option level.
- Rejected trap: The info_dict trap is just an explicit 'don't add a key' instruction.
- Suggested hardening: Let show_range also accept a string format template (e.g. show_range='{min} to {max}') that replaces _describe_range output only in help. The error message keeps the canonical form, and a string at the option level overrides a context-level False. This mirrors show_default's str/bool dual semantics (core.py:3456-3468).

## `command-aliases`: aliases= on Command: extra names resolved by every Group

**Outcome:** selected: novel, difficulty 4/5, value 4/5

- Category: subcommand dispatch · Gold edits: `src/click/core.py`
- Problem: A subcommand can only be reached by the single key it is registered under. Group.get_command is a plain dict lookup (core.py:1959-1963). The only alias support is the examples/aliases Group subclass or a third-party group class, and those do not keep default_map, auto envvar prefixes, help and error suggestions consistent.

**Novelty: novel.** Grep of repo/src found no aliases. No open or closed core PR or issue adds alias support; the alias-related PRs (#3398, #3234, #3231) only touch the docs example and were rejected. Several add-ons cover the user-facing theme, but each is a Group subclass the author has to adopt. That differs from the candidate's shape, so it is not drop_in. I did not check cloup or rich-click directly, so I can't say whether either offers aliases.

- Closest existing: click-aliases provides ClickAliasedGroup, with aliases= on command or group and help rendered as 'foo (bar,baz,qux)'. click-with-aliasing and core-extensions give similar alias decorators. The Click docs and example give a prefix-matching AliasedGroup. All of these are custom Group subclasses. The candidate puts aliases on Command and resolves them in every stock Group, canonical-name info_name, CommandCollection and completion. I did not check how these add-ons handle default_map or the env-var prefix.
- Evidence: [https://github.com/click-contrib/click-aliases](https://github.com/click-contrib/click-aliases): The README says 'Add (multiple) aliases to a click group or command'. It is used via the ClickAliasedGroup class, and help shows 'foo (bar,baz,qux)'.
- Evidence: [https://github.com/pallets/click/pulls?q=alias](https://github.com/pallets/click/pulls?q=alias): The only alias PRs are docs-example changes (#3398, #3234, #3231), all closed and rejected. No core aliases PR.
- Evidence: [https://github.com/pallets/click/issues?q=alias](https://github.com/pallets/click/issues?q=alias): No issue explicitly about core command aliases appeared on the first page.

**Value: 4/5** (fits the library: yes). Many independent third-party packages and a Stack Overflow question show persistent demand. The outline fixes real problems that subclasses have, such as default_map, the envvar prefix and completion all using the canonical name. I did not find a pallets/click issue, or a maintainer statement, either accepting or declining built-in aliases, so I cannot say how maintainers would see it. The examples/aliases directory suggests they treat it as a user-land pattern. I did not read the repo to confirm.

- Who benefits: Authors of git-like, multi-command CLIs who want short names such as ci for commit. They currently need click-aliases, click-alias, cloup, core-extensions or a custom Group subclass. Many CLIs hit this.
- User evidence: [https://github.com/click-contrib/click-aliases](https://github.com/click-contrib/click-aliases): click-aliases adds multiple aliases to a group or command. It has 56 stars and 20 forks.
- User evidence: [https://backiee.wasmer.app/https_stackoverflow_com/questions/46765803/python-click-multiple-group-names](https://backiee.wasmer.app/https_stackoverflow_com/questions/46765803/python-click-multiple-group-names): A Stack Overflow question about giving a click group multiple names. It surfaced in search results, and I did not open it. The search snippet says the answer subclasses Group.
- User evidence: [https://pypi.org/project/click-aliases](https://pypi.org/project/click-aliases): One of several separate PyPI packages for the same purpose (click-aliases, click-with-aliasing, click-alias, a click-hotoffthehamster variant). Cloup and core-extensions also ship alias groups.
- Contrived rule (to drop): Lookup order: exact name, then aliases, then normalized name, then aliases after normalization. This is a five-step precedence that few users need.
- Contrived rule (to drop): Short-help truncation width must include the alias suffix. This is a detail, not a user request.

**Difficulty: 4/5.** Several rules genuinely interact: precedence across exact, alias, normalized and normalized-alias lookups; canonical-name propagation into default_map and envvars; display width; suggestions; and CommandCollection sources. They all have to be consistent across resolve_command, get_command and format_commands. Even with a precise spec, a small model will likely miss one of them (most likely CommandCollection or the canonical key).

- Interacting rules: 6 · Survives an explicit spec: yes
- Likely failure: Building an alias map from self.commands only, which breaks CommandCollection sources and lazy groups. Or returning cmd.name, or the alias, as cmd_name. Or getting the normalize-then-alias precedence wrong so that an alias shadows a normalized real name. Plus forgetting to put aliases in the 'Did you mean' possibilities.
- Confirmed trap: resolve_command must return the canonical registered key, not the alias, because the returned cmd_name becomes info_name in make_context (core.py:2052, 2072), and default_map and the envvar prefix derive from it.
- Confirmed trap: format_commands computes limit from len(cmd[0]) (core.py:1995). The displayed term with ' (ci, cm)' must be used for both the row and the width.
- Confirmed trap: Alias lookup must live in resolve_command/get_command so that shell completion and CommandCollection see it.
- Confirmed trap: Missed: the 'canonical name' is the key the command is registered under in the group (or in a source, for CommandCollection; core.py:2173-2188), which can differ from cmd.name. Implementations that return cmd.name break groups that use add_command(cmd, name='x').
- Confirmed trap: Missed: NoSuchCommand currently receives possibilities=self.commands (core.py:2111). For CommandCollection that excludes source commands, and aliases must be added to the possibilities.
- Confirmed trap: Missed: the 4-step lookup order with token_normalize_func (core.py:2098-2100) must be interleaved: exact name, alias, normalized name, normalized alias. Normalizing aliases also means applying the function to each alias before comparing.
- Rejected trap: The info_dict key is just an explicit omission.

## `group-default-command`: Group(default_command=...) runs a subcommand when none is named

**Outcome:** rejected: novelty verdict drop_in (click-default-group (click-contrib): DefaultGroup subclass of click.Group with default=NAME and default_if_no_args=True; runs the default subcommand when none is given, and other subcommands still work. The candidate puts the same behaviour into core as Group(default_command=...) and adds details such as completion and no_args_is_help handling, but the capability and shape are essentially the same.)

- Category: subcommand dispatch · Gold edits: `src/click/core.py`
- Problem: Without a subcommand, a Group either shows help (no_args_is_help), fails with 'Missing command.' (core.py:2034), or runs only its own callback. An unknown first word raises NoSuchCommand (core.py:2108-2111). So 'tool file.txt' can never mean 'tool run file.txt'.

**Novelty: drop_in.** click-default-group's README describes the same capability: invoke a default subcommand instead of showing help when none is passed, with explicit subcommands still dispatching. A search shows its tests cover default= combined with invoke_without_command=True. Click's issue search turned up #1654 'Support default subcommand in a group' (closed). I did not open it, so its outcome is unconfirmed. No open Click PR implements this. I did not grep ./repo.

- Closest existing: click-default-group (click-contrib): DefaultGroup subclass of click.Group with default=NAME and default_if_no_args=True; runs the default subcommand when none is given, and other subcommands still work. The candidate puts the same behaviour into core as Group(default_command=...) and adds details such as completion and no_args_is_help handling, but the capability and shape are essentially the same.
- Evidence: [https://github.com/click-contrib/click-default-group](https://github.com/click-contrib/click-default-group): DefaultGroup subclass of click.Group; default=NAME and default_if_no_args=True invoke the default subcommand when none is passed; explicit subcommands still run.
- Evidence: [https://github.com/pallets/click/issues?q=default+subcommand](https://github.com/pallets/click/issues?q=default+subcommand): Lists #1654 'Support default subcommand in a group' as closed. No open PR for it.
- Evidence: [https://github.com/pallets/click/pulls?q=default+command](https://github.com/pallets/click/pulls?q=default+command): No PR implementing a default command; the results are unrelated or closed AI-spam PRs.

**Value: 3/5** (fits the library: yes). There is real, if modest, demand: a contrib package exists and is used. I found no issue asking for it in core, and the maintainers might say the contrib package is enough. The design is large and touches parse_args, invoke, resolve_command and completion. Implementing it in core is plausible, but demand is moderate.

- Who benefits: Authors of CLIs with one main action plus a few admin subcommands (`tool file.txt` vs `tool run file.txt`). The need is occasional, and a third-party package already covers it.
- User evidence: [https://github.com/click-contrib/click-default-group](https://github.com/click-contrib/click-default-group): click-default-group does this. It has 79 stars and its README describes it as invoking a command without an explicit subcommand name.
- User evidence: [https://github.com/pallets/click/issues?q=default+command+group](https://github.com/pallets/click/issues?q=default+command+group): Only loosely related issues turned up (#3059, #3100 about invoke_without_command). I found no core request for a default command.
- Contrived rule (to drop): Group(chain=True, default_command=...) raises TypeError at construction (a reasonable restriction, but one the outline invented)
- Contrived rule (to drop): no_args_is_help defaults to False when default_command is set (an unusual implicit coupling)

**Difficulty: 4/5.** There are four separate code paths (init defaults, parse_args, both invoke branches, resolve_command), and they interact through no_args_is_help, invoke_without_command, resilient_parsing and the result callback. The proposer missed the args[1:] slicing trap and the resilient_parsing guard, and both are easy to get wrong even with a precise spec.

- Interacting rules: 5 · Survives an explicit spec: yes
- Likely failure: Puts the fallback in resolve_command but returns args[1:] (dropping the first positional), or keeps it inside the `not ctx.resilient_parsing` guard so completion still fails. A second likely failure: the empty-args plus invoke_without_command path runs the group callback twice or gives the result callback the group's value instead of the default command's.
- Confirmed trap: Empty-args path: Group.parse_args only sets _protected_args when rest is non-empty (core.py:2015-2016), so Group.invoke hits ctx.fail('Missing command.') at core.py:2034 unless the no-args branch also dispatches to the default.
- Confirmed trap: no_args_is_help default comes only from invoke_without_command (core.py:1753-1754), and parse_args raises NoArgsIsHelpError for empty args (core.py:2007-2008). Both have to change, and an explicit no_args_is_help=True must still win.
- Confirmed trap: Completion: _resolve_context calls resolve_command and returns early when cmd is None (shell_completion.py:714-717). If the fallback lives only in invoke, completion stops at the group.
- Confirmed trap: Option-looking tokens must still go through the reparse/NoSuchCommand path at core.py:2108-2111.
- Confirmed trap: MISSED: resolve_command returns args[1:] (core.py:2112). For the default fallback it must return the whole arg list, otherwise 'file.txt' is silently dropped. Copying the existing return is the obvious way to get this wrong.
- Confirmed trap: MISSED: resilient_parsing. The current code skips the error branch when ctx.resilient_parsing is set (core.py:2108) and returns (None, None, ...). The default fallback has to run regardless of resilient_parsing, or completion still breaks.
- Confirmed trap: MISSED: ctx.invoked_subcommand must be set to the default's name before super().invoke(ctx) in the no-args branch (cf. core.py:2050-2051), and with invoke_without_command=True the group callback must run exactly once, not once in the invoke_without_command branch and again in the dispatch branch.
- Confirmed trap: subcommand_metavar default must become '[COMMAND] [ARGS]...' (core.py:1767-1770 only checks invoke_without_command).

## `option-help-sections`: help_section= on Option: titled option groups in --help

**Outcome:** reserve: novel, difficulty 2/5, value 4/5, not needed for the top 5

- Category: help layout · Gold edits: `src/click/core.py`, `src/click/decorators.py`
- Problem: Command.format_options writes every option into one 'Options' section (core.py:1296-1306). Commands with many options cannot group them the way argparse's add_argument_group does, unless they override format_options or adopt a third-party command class.

**Novelty: novel.** Issue #373 is open, with no core implementation. Maintainers said a third-party extension was acceptable. Cloup's docs show option groups need OptionGroupMixin or cloup classes, and use a title-based decorator API. The candidate is a core change on plain click, so it does not match their shape. I did not find an open PR. #1589 'Added section to group' (closed, 2020) and #3097 'WIP: Help page customization low level api' (open issue, not a PR) are related but do not implement this. I did not grep ./repo.

- Closest existing: cloup (option_group decorator, Option(group=...), but it requires cloup.Command/Group via OptionGroupMixin) and click-option-group (OptionGroup decorators with its own Command/Group classes); rich-click option panels. None offers a help_section= kwarg on plain click.Option and click.Command.
- Evidence: [https://github.com/pallets/click/issues/373](https://github.com/pallets/click/issues/373): Open since 2015; no core feature; users pointed to cloup, click-option-group and rich-click.
- Evidence: [https://cloup.readthedocs.io/en/latest/pages/option-groups.html](https://cloup.readthedocs.io/en/latest/pages/option-groups.html): Cloup option groups require cloup's OptionGroupMixin, Command or Group, and use @option_group(title, ...).
- Evidence: [https://github.com/pallets/click/pulls?q=option+group](https://github.com/pallets/click/pulls?q=option+group): No open PR adding option help groups.

**Value: 4/5** (fits the library: yes). Long-standing, widely discussed request with several third-party packages built on it. The core maintainers have been ambivalent (preferring subclassing), which is a risk. A simple per-option `help_section` attribute is small and fits Click's design.

- Who benefits: Authors of commands with many options (tens of flags) who want argparse-style headings in --help. Issue #373 has been open since 2015 and has 28 comments. Most CLIs with large option sets run into this.
- User evidence: [https://github.com/pallets/click/issues/373](https://github.com/pallets/click/issues/373): Open since 2015. Requests an equivalent of argparse's add_argument_group. A maintainer was unsure it belonged in core and suggested subclassing, while thedrow favoured adding chrisjsewell's `help_group` approach to core. Workarounds are cloup, click-option-group and rich-click.
- User evidence: [https://github.com/click-contrib/click-option-group](https://github.com/click-contrib/click-option-group): 121 stars. Exists because Click 'has no the functionality for creating option groups' and users asked for it in Click issues.
- User evidence: [https://github.com/pallets/click/issues?q=option+groups+help](https://github.com/pallets/click/issues?q=option+groups+help): Related help-output issues #2437 (closed) and #1112 (closed), plus a WIP PR #3097 on low-level help customization.
- Contrived rule (to drop): Trap rules about sorted vs first-appearance order, and per-section column alignment, are design choices rather than user needs (minor)

**Difficulty: 2/5.** Once the order and empty-section rules are written down, this is a group-by in a single method. The existing guards already handle hidden options and empty sections.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Writing 'Options' as a heading even when every option is grouped, or forgetting that help_option(help_section=...) has to reach Option.__init__ (it already does via **kwargs to option()).
- Confirmed trap: Section order must be first appearance, not sorted. A dict keyed by section in insertion order handles it.
- Confirmed trap: The 'Options' heading must not be written when it would be empty. The existing `if opts:` guard (core.py:1304) already does this if it is applied per section.
- Confirmed trap: Iterating self.params instead of get_params(ctx) drops the help option, which is appended in get_params (core.py:1104-1108).
- Confirmed trap: to_info_dict must not change (Option.to_info_dict at core.py:3211-3219).
- Rejected trap: Hidden handling is close to automatic: get_help_record already returns None for hidden options, and the existing loop skips None records (core.py:1300-1302).
- Rejected trap: The 'Group options before Commands' rule needs no work: Group.format_options already calls super().format_options and then format_commands (core.py:1974-1976).
- Suggested hardening: Require column alignment across all option sections: compute one shared first-column width (capped at write_dl's col_max=30) over every visible option in every section and pass it to each write_dl call, while the 'Positional arguments' section keeps its own width. This interacts with formatter.write_dl's measure_table/col_max logic and with the hidden/empty-section rules.

## `command-help-sections`: help_section= on Command: grouped subcommand listings

**Outcome:** reserve: novel, difficulty 2/5, value 3/5, not needed for the top 5

- Category: help layout · Gold edits: `src/click/core.py`
- Problem: Group.format_commands always writes a single 'Commands' list (core.py:1978-2004). Large CLIs cannot split subcommands into labelled sections such as 'Database' and 'Deployment' without overriding format_commands.

**Novelty: novel.** Cloup provides subcommand sections with its own Group, Section class and a different API. The candidate is a core change on plain click. Issue #373 is still open. The only related PR I saw is #1589 'Added section to group' (closed 2020). No open PR was found. The cloup docs page I tried returned 404, so my cloup details come from a search result summary. I did not grep ./repo.

- Closest existing: cloup Group.section()/add_command(section=) and Section objects, which require cloup.Group; rich-click command panels. The candidate adds help_section= to plain click.Command and click.Group.
- Evidence: [https://github.com/pallets/click/issues/373](https://github.com/pallets/click/issues/373): Open request; no core implementation; cloup and rich-click mentioned as alternatives.
- Evidence: [https://github.com/ewels/rich-click](https://github.com/ewels/rich-click): Advertises 'Group commands and options into named panels' via RichGroup/RichCommand, not plain click.
- Evidence: [https://cloup.readthedocs.io/en/latest/autoapi/cloup/_sections/index.html](https://cloup.readthedocs.io/en/latest/autoapi/cloup/_sections/index.html): Surfaced in the web search results only; I did not open it. Per the search summary, cloup's Section class is used via Group.section()/add_command(section=...).

**Value: 3/5** (fits the library: yes). There is real demand, evidenced by cloup, but the specific issues about command sections were closed and the maintainers' view is that subclassing suffices. The `help_section` attribute on Command is simple. A moderate score reflects the lack of a direct core request and its overlap with option sections.

- Who benefits: Maintainers of CLIs with dozens of subcommands (cloup users, rich-click users). Less common than option groups, but the demand is similar.
- User evidence: [https://github.com/pallets/click/issues/373](https://github.com/pallets/click/issues/373): The thread includes a 2019 workaround for grouping subcommands into sections (jtrakk), and cloup was built for help sections.
- User evidence: [https://cloup.readthedocs.io/en/latest/](https://cloup.readthedocs.io/en/latest/): Cloup ships subcommand sections as a headline feature. The page doesn't say which Click limitation it addresses.
- User evidence: [https://github.com/pallets/click/issues?q=command+sections+help+group](https://github.com/pallets/click/issues?q=command+sections+help+group): #1112 (separate Group subcommands and commands in help) and #2437 (splitting help into group sections) were both closed. #373 is the only matching open issue.
- Contrived rule (to drop): The short-help `limit` must be computed globally across sections (an implementation detail rather than a user need)

**Difficulty: 2/5.** This is a single-method change, and the main trap is spelled out in the spec. The existing structure already computes limit before building rows.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Moving the limit calculation inside the per-section loop. With the spec stating that the limit is global, though, the natural refactor (compute limit once, then bucket rows) is what a model will write.
- Confirmed trap: limit is computed at core.py:1995 from the longest visible command name. It must stay global and not be recomputed per section.
- Confirmed trap: Must keep using list_commands/get_command (core.py:1983-1984) rather than self.commands, or CommandCollection and lazy groups break.
- Confirmed trap: Sections in first-appearance order, not sorted.
- Confirmed trap: Command.to_info_dict (core.py:1080-1089) must stay unchanged.
- Suggested hardening: Add Group(section_order=[...]): named sections in that list come first in the given order (and 'Commands' can appear in the list to change where it goes), while sections not in the list follow by first appearance. A section named in section_order but with no visible commands is still skipped.

## `exception-error-style`: error_style on ClickException to style the 'Error:' line

**Outcome:** reserve: novel, difficulty 2/5, value 3/5, not needed for the top 5

- Category: error output · Gold edits: `src/click/exceptions.py`
- Problem: ClickException.show and UsageError.show echo the 'Error: ...' line as plain text (src/click/exceptions.py:57-65, 87-111). Making errors red needs a subclass that overrides show for every exception type, including the ones Click raises internally.

**Novelty: novel.** #944 is open with the 'help output' label and no linked PR on the main repo. The search found only user-level workarounds that override show(). I found no library offering a class-level error_style attribute on ClickException. I did not grep ./repo.

- Closest existing: Issue #944 (open) discusses a style_args attribute or per-exception style callable. A draft hit a circular import and no PR is linked. The common workaround is subclassing ClickException and overriding show() with secho(fg='red'). rich-click advertises 'well formatted error messages', but that is a separate rendering layer.
- Evidence: [https://github.com/pallets/click/issues/944](https://github.com/pallets/click/issues/944): Open feature request; davidism suggested styling in ClickException.show(); a draft style_args attempt hit a circular import; no PR linked.
- Evidence: [https://github.com/ewels/rich-click](https://github.com/ewels/rich-click): Lists 'Well formatted error messages' as a feature; no class-level error_style attribute on ClickException.

**Value: 3/5** (fits the library: yes). The maintainer himself sketched this approach, so it fits. Evidence of demand is thin: one old issue with 6 comments and scattered override snippets. A class-level global dict attribute is somewhat unusual for Click's API. It is a modest convenience.

- Who benefits: CLI authors who want red 'Error:' output. They currently subclass ClickException and override show(). The need is occasional but the request is old and recurring.
- User evidence: [https://github.com/pallets/click/issues/944](https://github.com/pallets/click/issues/944): Open since 2018. davidism proposed calling style() on the message with style args on ClickException. A later attempt hit a circular import between termui and exceptions. Still open and no design is settled.
- User evidence: [https://github.com/pallets/click/issues?q=error+color+exception+style](https://github.com/pallets/click/issues?q=error+color+exception+style): #944 is the open request. #2193 (ctx.color ignored in ClickException.show) was fixed. #1917 (overriding exception text) is related but different.
- User evidence: [https://hfutils.readthedocs.io/en/stable/_modules/hfutils/entry/base.html](https://hfutils.readthedocs.io/en/stable/_modules/hfutils/entry/base.html): Example of a project subclassing ClickException with a custom show() that uses secho(fg='red'), i.e. the workaround.
- Contrived rule (to drop): Only the 'Error:' line is styled while usage and hint stay unstyled (a deliberate choice rather than a user need)

**Difficulty: 2/5.** Attribute lookup gives the required precedence for free, and echo already handles colour stripping. The rest is two small edits.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Styling only in ClickException.show and forgetting UsageError.show. Once the spec names both paths, that goes away.
- Confirmed trap: Import cycle: termui imports Abort/UsageError from exceptions (termui.py:18-19), so a top-level `from .termui import style` in exceptions.py fails. It fails loudly at import time, though, so the solver will notice and use a local import.
- Confirmed trap: UsageError.show is a separate echo path (exceptions.py:87-111) and does not call ClickException.show (exceptions.py:57-65), so both need the styling.
- Confirmed trap: Only the second echo in UsageError.show (exceptions.py:107-111) should be styled, not the usage+hint echo (exceptions.py:106).
- Rejected trap: 'Styling is removed whenever colour is off' needs no new logic. echo already strips ANSI via should_strip_ansi(file, resolve_color_default(color)) (utils.py:330), using the color the show methods already pass.
- Rejected trap: 'Styling self.message instead of format_message()' is unlikely, because both show methods already format with format_message(); the natural edit wraps that existing expression.
- Suggested hardening: Add a separate hint_style (or a per-part dict {'error':..., 'usage':..., 'hint':...}) that the UsageError hint uses. It falls back to error_style only when hint_style is unset at every level of the MRO, and an explicit None on a subclass disables it. This forces precedence across two attributes and splitting the combined usage+hint echo at exceptions.py:106.

## `color-option-and-env`: click.color_option() plus NO_COLOR / FORCE_COLOR auto-detection

**Outcome:** rejected: novelty verdict drop_in (click-extra colorize: a tri-state eager --color[=auto|always|never] option (plus --no-color) that sets ctx.color, and handling of NO_COLOR, FORCE_COLOR, CLICOLOR and others. The differences are that click-extra's FORCE_COLOR treats falsy values as off, it covers more variables, and it works at the option layer rather than inside click._compat.should_strip_ansi.)

- Category: terminal color policy · Gold edits: `src/click/decorators.py`, `src/click/_compat.py`, `src/click/__init__.py`
- Problem: Colour is decided only by isatty, by an explicit color argument, or by ctx.color (_compat.py:502-513, globals.py:54-67). NO_COLOR and FORCE_COLOR are ignored, and there is no standard `--color [auto|always|never]` option. Each CLI wires ctx.color by hand.

**Novelty: drop_in.** click-extra's docs describe essentially the same capability: an eager --color option with auto/always/never and a default of auto, setting ctx.color, plus NO_COLOR and FORCE_COLOR support with explicit flags overriding the environment. Click issue #3022 (open) asks for the env variables in core. A collaborator, kdeldycke, replied that his click-extra project already provides this. PR #3845, which attempted it, was closed as 'rejected AI' for its origin, not on technical grounds. Earlier issues #2207 and #1498 are closed. No open PR implements it. I did not grep ./repo.

- Closest existing: click-extra colorize: a tri-state eager --color[=auto|always|never] option (plus --no-color) that sets ctx.color, and handling of NO_COLOR, FORCE_COLOR, CLICOLOR and others. The differences are that click-extra's FORCE_COLOR treats falsy values as off, it covers more variables, and it works at the option layer rather than inside click._compat.should_strip_ansi.
- Evidence: [https://kdeldycke.github.io/click-extra/colorize.html](https://kdeldycke.github.io/click-extra/colorize.html): Provides --color[=WHEN] with auto/always/never, an eager option setting ctx.color, and NO_COLOR/FORCE_COLOR support, with explicit flags beating the environment.
- Evidence: [https://github.com/pallets/click/issues/3022](https://github.com/pallets/click/issues/3022): Open feature request for FORCE_COLOR/NO_COLOR in click; a collaborator pointed to click-extra; no linked PR.
- Evidence: [https://github.com/pallets/click/pull/3845](https://github.com/pallets/click/pull/3845): Closed as a rejected AI-origin contribution, not merged.

**Value: 4/5** (fits the library: yes). The most frequently requested of the five, with several issues over years and a current open one. Earlier requests were closed, with the maintainer's reasoning being that the standard was unsettled and the app could pass `color`. That risk remains. Bundling `color_option` with env detection widens scope, but together they address what users ask for.

- Who benefits: Nearly every CLI author who uses colour: users in CI (GitHub Actions, GitLab, Jenkins) want FORCE_COLOR, and users who set NO_COLOR expect it to be honoured. The need recurs across many projects.
- User evidence: [https://github.com/pallets/click/issues/3022](https://github.com/pallets/click/issues/3022): Open since July 2025, labelled Feature. Asks for FORCE_COLOR and NO_COLOR support because CI logs aren't TTYs. A maintainer (kdeldycke) pointed to click-extra. #2781 was marked as a duplicate.
- User evidence: [https://github.com/pallets/click/issues/2207](https://github.com/pallets/click/issues/2207): Closed as a duplicate of #1498 in 2022. davidism doubted NO_COLOR was an accepted standard and suggested reading it in the app and passing it to `color`. He also noted Click has no --color option.
- User evidence: [https://kdeldycke.github.io/click-extra/colorize.html](https://kdeldycke.github.io/click-extra/colorize.html): click-extra ships a `--color` option and NO_COLOR/FORCE_COLOR handling because Click lacks it.
- User evidence: [https://github.com/pallets/click/issues?q=NO_COLOR](https://github.com/pallets/click/issues?q=NO_COLOR): Repeated requests: #1498, #2207, #3022 and PR #3845 (rejected AI).
- Contrived rule (to drop): Treating the empty string as unset is sensible, not contrived
- Contrived rule (to drop): Precedence between NO_COLOR and FORCE_COLOR (NO_COLOR wins) is a choice that other tools make differently

**Difficulty: 3/5.** There are several precedence rules, but the explicit-over-env order falls out of the existing color-is-None branch structure. Once the spec places the env logic in should_strip_ansi, the remaining work is a short ordered if-chain and a boilerplate decorator. One claimed trap (eagerness needed for inheritance) is wrong.

- Interacting rules: 4 · Survives an explicit spec: no
- Likely failure: Putting the env logic in resolve_color_default (which the spec explicitly forbids), or mapping 'auto' to False. With the precedence chain written out, a model is most likely to slip on the empty-string rule or the pager short-circuit ordering.
- Confirmed trap: 'auto' must not touch ctx.color. Context inherits parent.color only when its own color is None (core.py:498-502).
- Confirmed trap: The env checks belong in _compat.should_strip_ansi's color-is-None branch, after the pager short-circuit (_compat.py:505-512). Putting them in resolve_color_default (globals.py:54-65) would change what CliRunner's patched should_strip_ansi sees (testing.py:505-522).
- Confirmed trap: The pager writer short-circuit (hasattr(stream,'color')) has to stay ahead of the env checks.
- Confirmed trap: MISSED: when stream is None the function substitutes sys.stdin (_compat.py:506-507). The env checks must also apply on that path, so they cannot be placed only in the elif branch.
- Confirmed trap: MISSED: NO_COLOR beats FORCE_COLOR, and empty values count as unset. An `os.environ.get('NO_COLOR')` truthiness check gives this; a model checking `'NO_COLOR' in os.environ` gets the empty-string case wrong.
- Rejected trap: 'The option must be eager or subcommands won't inherit' is wrong. Group.invoke creates the sub-context only after the parent has finished parsing and running all parameter callbacks (core.py:2052), so a non-eager callback that sets ctx.color still propagates. Eagerness only matters for `--color always --help` ordering relative to the eager help option (decorators.py:621).
- Suggested hardening: Make FORCE_COLOR values '0'/'false' mean force-off (treated like NO_COLOR), while other non-empty values force colour on. Also make color_option's 'auto' resolve via NO_COLOR/FORCE_COLOR at parse time only when the parent context's color is None, so 'auto' under a parent that has an explicit Context(color=True) keeps True. This adds a three-way env interaction and a parent-inheritance rule.

## `option-value-separator`: separator= on Option: accept --tag a,b,c as several values

**Outcome:** selected: novel, difficulty 4/5, value 2/5; value audit doubts it fits the library; variation rule relaxed to: category

- Category: multi-value options · Gold edits: `src/click/core.py`
- Problem: An option taking several values must be repeated (`--tag a --tag b`) or post-processed in a callback (#2771). Env vars split on whitespace via split_envvar_value (core.py:3616-3623), default_map strings are only split when nargs != 1 (core.py:2553-2556), and nothing splits command-line values. A comma-list option behaves differently for each source unless every author writes the same callback.

**Novelty: novel.** Issue #2771 is open with no linked PR. Maintainers were sceptical and suggested a callback. The 9.0.0 milestone was removed. PR search for 'separator' found no matching PR; #422 'Option value separators' was closed unmerged in 2016. click-extra MultiChoice is a separate type limited to choices, and its docs don't cover env vars or completion. Typer is a different library. A grep of repo/src/click found no 'separator' on Option; the single hit was in termui.py, which I did not open. So a core separator= is not implemented.

- Closest existing: click-extra MultiChoice (a ParamType, comma separator, Choice-only) and Typer's Option(separator=...). Neither is a kwarg on click.Option that applies to any type and to every source.
- Evidence: [https://github.com/pallets/click/issues/2771](https://github.com/pallets/click/issues/2771): Open request, no PR. Maintainers suggest a callback. MultiChoice in click-extra is mentioned as a partial workaround.
- Evidence: [https://github.com/pallets/click/pulls?q=separator](https://github.com/pallets/click/pulls?q=separator): No PR for comma-separated values. Only #422 (2016, closed unmerged) is close.
- Evidence: [https://kdeldycke.github.io/click-extra/types.html](https://kdeldycke.github.io/click-extra/types.html): MultiChoice has a separator (default ','), but it is a type that works on choices only. Env var and completion behaviour is not documented.

**Value: 2/5** (fits the library: no). The demand is real but modest. Maintainers have signalled reluctance and point to a callback workaround. The outline spreads across env, default_map, prompt, completion and help, which is a large surface for a niche feature. Related upstream requests (#2771) were about nargs=-1 with a separator, not this multiple-style API.

- Who benefits: Authors wanting `--tags a,b,c` lists. Real need, but the usual workaround is a short split callback. Env, default_map and prompt handling add scope beyond what was asked.
- User evidence: [https://github.com/pallets/click/issues/2771](https://github.com/pallets/click/issues/2771): Open request for a non-whitespace separator on options. Maintainers were sceptical: davidism said the parser gets pre-split tokens and showed a split callback. AndreasBackx called comma separators uncommon and confusing. The issue was removed from the 9.0.0 milestone. kdeldycke shipped MultiChoice in click-extra instead.
- User evidence: [https://kdeldycke.github.io/click-extra/types.html](https://kdeldycke.github.io/click-extra/types.html): click-extra provides MultiChoice because click has no equivalent, which shows some demand.
- Contrived rule (to drop): Help metavar '<M>[<sep><M>...]' format
- Contrived rule (to drop): Completion that re-attaches earlier segments
- Contrived rule (to drop): separator combined with multiple=True is allowed as a no-op
- Contrived rule (to drop): TypeError for is_flag/count/nargs!=1 combinations

**Difficulty: 4/5.** Each rule is clear on its own, but they conflict. 'Split command-line occurrences' and 'don't split list defaults' cannot both be met at a single convergence point. On top of that, the prompt path re-processes its own output, and the env-var path has its own split logic. A small model will probably pick one place to split and break one of these sources.

- Interacting rules: 5 · Survives an explicit spec: yes
- Likely failure: Splitting everything inside type_cast_value. That either splits list defaults that should stay intact or leaves command-line occurrences unsplit. A second likely failure is the double prompt processing: the already-converted tuple gets re-split or re-converted badly. Completion that ignores the prefix is also likely.
- Confirmed trap: Prompt path: Option.prompt_for_value passes value_proc=lambda x: self.process_value(ctx, x) (core.py:3551). The prompt answer is a bare string, so splitting only in consume_value misses it. The split has to happen in type casting too.
- Confirmed trap: Prompt values are processed twice. prompt() returns value_proc's result (termui.py:272-278), Option.consume_value returns it as the value (core.py:3678), and handle_parse_result calls process_value again (core.py:2811). The second pass gets a tuple of already-converted items, so type_cast_value must not re-split or reject non-str items. Proposer missed this.
- Confirmed trap: Option.value_from_envvar splits on whitespace whenever multiple/nargs is set (core.py:3617-3623). If separator is implemented as multiple=True underneath, the env var still goes down that path unless it is overridden.
- Confirmed trap: A default_map string with multiple=True and nargs==1 is not split (core.py:2555 checks only nargs != 1). type_cast_value's multiple branch then iterates the string's characters (core.py:2617-2618).
- Confirmed trap: Choice.shell_complete does a plain startswith on the whole incomplete string (types.py:508-515). 'x,' therefore matches nothing until the code splits on the last separator and re-attaches the prefix.
- Confirmed trap: Missed by proposer: splitting depends on the source. Command-line occurrences arrive as a list ['a,b','c'] where each element must be split. A list/tuple default must NOT be split. type_cast_value alone cannot tell these two apart, so splitting must happen per source (consume_value for COMMANDLINE) or carry extra state.

## `mutually-exclusive-params`: mutually_exclusive= on Command: reject conflicting explicit parameters

**Outcome:** reserve: novel, difficulty 2/5, value 3/5; value audit doubts it fits the library, not needed for the top 5

- Category: cross-parameter validation · Gold edits: `src/click/core.py`
- Problem: Click has no way to declare that `--json` and `--yaml` cannot be used together. Users write helpers that count set flags and raise UsageError (the gist warns its helper breaks when names are reused across contexts), or they adopt cloup's constraint system, which requires cloup.Command.

**Novelty: novel.** No open or closed click PR on mutual exclusion. The only search hit, #3452, is an unrelated typing PR. cloup provides the capability, but only in its own command class and constraint system, so it is not a same-shape drop-in. Click core has no such feature, and the grep found no mutually_exclusive in src/click.

- Closest existing: cloup's mutually_exclusive constraint and click-constrained-option. cloup declares it through @constraint or option groups and needs cloup.Command. The candidate is a Command kwarg in plain click, based on parameter sources.
- Evidence: [https://cloup.readthedocs.io/en/latest/pages/constraints.html](https://cloup.readthedocs.io/en/latest/pages/constraints.html): cloup has mutually_exclusive via @constraint(mutually_exclusive, [names]), @mutually_exclusive(...) and option_group constraints. It needs cloup commands and is not a click.Command kwarg.
- Evidence: [https://github.com/pallets/click/pulls?q=mutually+exclusive](https://github.com/pallets/click/pulls?q=mutually+exclusive): The only hit is #3452, an unrelated typing PR. No PR implements this.

**Value: 3/5** (fits the library: no). Demand is clear. Many issues (#257, #509, #1137, #2252, #2342) were all closed, so maintainers have repeatedly declined. A simple name-group check in Command is more modest than option_group, which could make it more acceptable. Declined history lowers the score.

- Who benefits: CLI authors with flags such as --json/--yaml/--csv. This is a common need that is usually solved with hand-written checks or cloup. The workaround is simple, though.
- User evidence: [https://gist.github.com/thebopshoobop/51c4b6dce31017e797699030e3975dbf](https://gist.github.com/thebopshoobop/51c4b6dce31017e797699030e3975dbf): Gist with a hand-written exclusive() helper.
- User evidence: [https://cloup.readthedocs.io/en/latest/pages/constraints.html](https://cloup.readthedocs.io/en/latest/pages/constraints.html): cloup offers mutually_exclusive as part of a constraint system.
- User evidence: [https://github.com/pallets/click/issues/257](https://github.com/pallets/click/issues/257): Long-running request with 37 comments. It was closed by mitsuhiko in 2015: there is 'no likely API' and it can be checked in callbacks. He doubted useful help text could be generated.
- Contrived rule (to drop): Message names only the first two explicit members in declared order
- Contrived rule (to drop): Only the first violation is reported
- Contrived rule (to drop): A false-spelling flag such as --no-json still counts as provided
- Contrived rule (to drop): PROMPT source counts as explicit but DEFAULT_MAP does not

**Difficulty: 2/5.** With the sources and the check location written down, this is about 15 lines in one spot. The rules (explicit-source test, declaration order, first violation wins, skip under resilient parsing) are independent and easy to follow.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Putting the check before the loop, or after the extra-args failure in the wrong order. Or not skipping the check under resilient_parsing. Or reporting the hints in the order given on the command line instead of declaration order.
- Confirmed trap: Using value truthiness instead of ctx.get_parameter_source misses `--no-json` and `--count 0`.
- Confirmed trap: DEFAULT_MAP must count as not explicit. The `source < ParameterSource.DEFAULT_MAP` convention is visible at core.py:2797 and 3661.
- Confirmed trap: The check must run after the processing loop in Command.parse_args (core.py:1374-1375). Placing it right after that loop also gives the intended ordering: missing-required and conversion errors come first, and eager --help exits first.
- Confirmed trap: Missed: get_parameter_source returns None for unknown names. Comparing None < DEFAULT_MAP raises a raw TypeError rather than the spec'd TypeError naming the parameter, so name validation must happen before the comparison.
- Rejected trap: The feature-switch trap mostly goes away because the spec names members by Parameter.name and get_parameter_source is keyed by name. Restoring sources after lost arbitration already happens (core.py:2841-2843).
- Rejected trap: 'Running before arbitration finishes' is not a realistic risk. Arbitration finishes inside each handle_parse_result, and the natural place to insert the check is after the loop.
- Suggested hardening: Prompt suppression: if a group member was already given explicitly (COMMANDLINE/ENVIRONMENT), other members of the same group must not prompt (prompt=True/required) and count as not provided. They must also not raise MissingParameter for required=True. This makes the group state visible inside Option.consume_value's prompt branch (core.py:3672-3679) and process_value's required check (core.py:2664), and it depends on processing order (iter_params_for_processing).

## `config-file-option`: click.config_option(): load a JSON config file into default_map

**Outcome:** rejected: novelty verdict drop_in (click-extra's @config_option, which loads a config file into default_map with subcommand sections and reports DEFAULT_MAP. It also covers TOML/YAML/JSON/INI, so it is a superset of the candidate's JSON-only version. click-config-file is a second similar package.)

- Category: configuration · Gold edits: `src/click/decorators.py`, `src/click/__init__.py`
- Problem: Click only offers the low-level Context.default_map. Every app that wants `--config FILE` writes an eager callback that reads the file and fills ctx.default_map, often mutating the shared context_settings dict, breaking subcommand sections, or failing on a missing default path (jwodder gist and blog post).

**Novelty: drop_in.** click-extra's docs describe essentially the same capability: a --config option whose file values go into default_map (reported as DEFAULT_MAP), with nested subcommand sections, and command line and env overriding the file. The candidate differs only by being JSON-only and living in click core, so this is a sibling library offering the same capability. Click core has no config_option (grep found none), and there is no click PR for one. I did not open click-extra's documentation on missing default paths or on how it merges an existing default_map.

- Closest existing: click-extra's @config_option, which loads a config file into default_map with subcommand sections and reports DEFAULT_MAP. It also covers TOML/YAML/JSON/INI, so it is a superset of the candidate's JSON-only version. click-config-file is a second similar package.
- Evidence: [https://kdeldycke.github.io/click-extra/config.html](https://kdeldycke.github.io/click-extra/config.html): @config_option adds --config and loads the file into default_map. It reports DEFAULT_MAP, supports subcommand sections and many formats including JSON.
- Evidence: [https://github.com/pallets/click/pulls?q=config+option+default_map](https://github.com/pallets/click/pulls?q=config+option+default_map): No click PR implements a config option. The only hit is the unrelated closed #3849.

**Value: 2/5** (fits the library: no). Maintainers have explicitly declined config-format handling in core. The demand ref is an INI tutorial, so JSON-only addresses it loosely. click-extra already provides config_option.

- Who benefits: Authors of apps that want a --config file. Many need this, but it is a well-known recipe, and the format choice and file lookup are contested.
- User evidence: [https://gist.github.com/jwodder/8ce218892331229c9116ed6c3e16a5bb](https://gist.github.com/jwodder/8ce218892331229c9116ed6c3e16a5bb): Tutorial showing a hand-rolled eager --config callback filling default_map. It uses INI, not JSON, and the author says it is simple to do by hand.
- User evidence: [https://github.com/pallets/click/issues/386](https://github.com/pallets/click/issues/386): Request for config file support closed. Maintainers (untitaker, davidism) said format and file handling should live in a third-party package and that click should not handle config formats.
- User evidence: [https://github.com/pallets/click/issues?q=config+file+default_map](https://github.com/pallets/click/issues?q=config+file+default_map): Issues such as #971 and #386 were closed and none shows a built-in option was added.
- Contrived rule (to drop): JSON-only format
- Contrived rule (to drop): A missing file at the default path is silently ignored but an explicit one errors
- Contrived rule (to drop): Recursive merge with file values winning

**Difficulty: 3/5.** Once the spec says 'eager, don't use exists=True, deep-merge into a new dict, check the source', each trap becomes a single instruction. The remaining risk is getting deep-merge-without-mutation right, which is a well-known pattern.

- Interacting rules: 4 · Survives an explicit spec: no
- Likely failure: A shallow merge ({**old, **new}) that replaces nested subcommand sections instead of merging them. Or deep-merging into the existing dict in place, which mutates context_settings across invocations.
- Confirmed trap: Mutating ctx.default_map in place leaks into context_settings or the parent. Context.__init__ assigns the dict as-is (core.py:391-399), and an inherited section is the same object as the parent's nested dict. Merging must copy recursively.
- Confirmed trap: A missing file at the default path vs an explicit one: the code has to check ctx.get_parameter_source in the callback. The source is set before process_value/callback runs (core.py:2791), so this works.
- Confirmed trap: It must be eager so it runs before other parameters (iter_params_for_processing). This is copied directly from help_option/version_option (decorators.py:551-553, 619-621).
- Confirmed trap: Missed: when the option has no default and is not given, the callback receives None and must skip loading. The --config value itself can also come from a parent default_map (source DEFAULT_MAP), and the spec doesn't say whether a missing file is then ignored or an error.
- Rejected trap: The error-prefix formatting is not really a trap. A BadParameter raised inside the callback gets param filled in by augment_usage_errors wrapped around process_value (core.py:2785-2811), so "Invalid value for '--config'" comes for free.
- Suggested hardening: Validate unknown keys: any top-level key that is neither a parameter name of ctx.command nor (for a Group) a subcommand name/alias raises BadParameter listing the keys in sorted order. Keys that map to a subcommand must hold objects. This requires walking ctx.command.params and Group.commands, and handling sections differently from scalar values.

## `choice-enum-by-value`: Choice(enum_by_value=True): match Enum members by their values

**Outcome:** selected (filler, below the difficulty floor): novel, difficulty 2/5, value 3/5

- Category: parameter types · Gold edits: `src/click/types.py`, `src/click/core.py`, `src/click/termui.py`
- Problem: Choice.normalize_choice always uses Enum.name (types.py:416), so `Choice(Format)` makes users type 'TEXT' rather than the value 'text'. Help defaults also show the member name (core.py:3471-3472), and prompts list repr-like 'Format.TEXT' strings (termui.py:117-118).

**Novelty: novel.** Click core has no by-value option. Related PRs were closed without merging: #2958 'Use Enum value for token normalization' and EnumChoice PRs #2210 and #2272. Issues #2911, #2959, #2970 and #3028 show demand, and they are closed. Merged work (#2796, #3004, #3471) kept matching by name and fixed help and completion rendering. click-extra shares the theme but is a different class in another library, with unconfirmed prompt and completion behaviour. So it is not the same shape. This is the closest call. Judged against a drop-in rule based on shape rather than theme, it stays novel.

- Closest existing: click-extra's EnumChoice(choice_source='value') provides value matching as a separate ParamType. The candidate is a kwarg on click.Choice that also fixes help default, prompt and completion in core. Click-extra's docs don't confirm prompt or completion handling.
- Evidence: [https://github.com/pallets/click/pulls?q=Choice+enum](https://github.com/pallets/click/pulls?q=Choice+enum): No open PR. #2958 (use Enum value) and #2210/#2272 (EnumChoice) were closed unmerged. Merged PRs #2796, #3004 and #3471 do not add by-value matching.
- Evidence: [https://github.com/pallets/click/issues?q=Choice+enum+value](https://github.com/pallets/click/issues?q=Choice+enum+value): Demand issues #2911, #2959, #2970 and #3028 are closed. No core by-value option exists.
- Evidence: [https://kdeldycke.github.io/click-extra/types.html](https://kdeldycke.github.io/click-extra/types.html): EnumChoice with choice_source='value' matches member values. It is a separate type, and prompt and completion behaviour is not documented.

**Value: 3/5** (fits the library: yes). Recurring user pain, with a 2025 name-vs-value confusion, and Typer defaults to values. But maintainers closed the EnumChoice PRs and may prefer a separate type. A flag on Choice is a smaller change. The multi-site help, prompt and completion changes are legitimate consistency fixes.

- Who benefits: Authors using Enum or StrEnum with Choice who want users to type values, which is common. Several users have hit this.
- User evidence: [https://github.com/pallets/click/issues/605](https://github.com/pallets/click/issues/605): Enum support was added using names because they are unique. Values were left to click-extra EnumChoice.
- User evidence: [https://github.com/pallets/click/issues?q=Choice+enum](https://github.com/pallets/click/issues?q=Choice+enum): Many issues: #2911 'Choice prefers Enum.name even for StrEnum', #3028 prompt shows values but requires names, #2970, #2959. The EnumChoice PR #2210 was closed.
- Contrived rule (to drop): Int-valued enums match on the stringified value
- Contrived rule (to drop): to_info_dict must stay unchanged

**Difficulty: 2/5.** normalize_choice is the single funnel for nearly all behaviour, so the core change is one line. The two extra display paths are named explicitly in the spec.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Forgetting the help-default or prompt-list path. Or making the prompt list show normalized values for every Choice, which breaks existing tests.
- Confirmed trap: Option.get_help_extra hardcodes default_value.name for enums (core.py:3471-3472).
- Confirmed trap: termui._build_prompt uses map(str, type.choices) (termui.py:117-118), which gives 'Fmt.JSON'.
- Confirmed trap: Values must be stringified for int enums. normalize_choice already does str() for non-enums (types.py:416).
- Confirmed trap: Added: _build_prompt must apply only to by-value choices. Switching it to _normalized_mapping for all Choices would casefold the prompt list for case_sensitive=False and break existing prompt tests.
- Confirmed trap: Added: multiple=True with a list-of-enum default goes through the list branch at core.py:3469-3470 (str(d)) and still shows 'Fmt.JSON'. The spec doesn't cover this case.
- Rejected trap: The to_info_dict trap only applies if the solver adds the key on its own. The spec says to leave it unchanged.
- Rejected trap: Enum defaults and empty prompt answers need no work. prompt round-trips the default through value_proc (termui.py:265-272) into Choice.convert, which normalizes the member itself.
- Suggested hardening: With enum_by_value=True, input may match either a member's value or its name. Value matches take precedence when one member's name equals another member's value (e.g. A='b', B='a'). Metavar, errors, completion and help still list values only. This adds precedence inside convert while the displayed set stays different from the accepted set.

## `help-styles`: Context(help_styles=...) to colour headings and terms in --help

**Outcome:** reserve: novel, difficulty 2/5, value 2/5; value audit doubts it fits the library, not needed for the top 5

- Category: help styling · Gold edits: `src/click/formatting.py`, `src/click/core.py`
- Problem: HelpFormatter writes plain text only (formatting.py:204-271), and Context.make_formatter passes only widths (core.py:638-650). Coloured section headings and option names need click-help-colors, rich-click or a custom formatter_class.

**Novelty: novel.** There is no click PR for styled help (the search hits were unrelated). click-help-colors needs custom command classes. cloup's theming is the closest in shape, with context-level inheritance, but it requires cloup's Command and formatter. Neither works through click.Context. A grep of src/click found no help_styles.

- Closest existing: click-help-colors (HelpColorsGroup/HelpColorsCommand via cls=, with color args for headers and options) and cloup's HelpTheme (context- and command-level settings, but needs cloup commands). The candidate is a Context(help_styles=...) setting in plain click, inherited by subcommands.
- Evidence: [https://github.com/click-contrib/click-help-colors](https://github.com/click-contrib/click-help-colors): Uses cls=HelpColorsGroup/HelpColorsCommand with help_headers_color and help_options_color. It is class-based, not a Context setting.
- Evidence: [https://cloup.readthedocs.io/en/latest/pages/formatting.html](https://cloup.readthedocs.io/en/latest/pages/formatting.html): cloup HelpTheme styles help elements with context-level settings. It needs cloup's own command and formatter classes. This page appeared in the search results and I did not open it, so this finding comes from the search summary.
- Evidence: [https://github.com/pallets/click/pulls?q=help+color+style](https://github.com/pallets/click/pulls?q=help+color+style): No relevant PR. The three closed hits are unrelated.

**Value: 2/5** (fits the library: no). No upstream request was found, and the ecosystem already covers it through formatter_class. It adds a new Context setting and HelpFormatter signature, while click keeps help plain. Adoption of the existing add-ons is modest.

- Who benefits: Authors who want coloured help. There is a niche audience, served by click-help-colors (92 stars), rich-click and cloup.
- User evidence: [https://github.com/click-contrib/click-help-colors](https://github.com/click-contrib/click-help-colors): Small package with 92 stars, so modest demand.
- User evidence: [https://github.com/pallets/click/issues?q=help+color+style+headings](https://github.com/pallets/click/issues?q=help+color+style+headings): No matching upstream issues.
- Contrived rule (to drop): An explicit prefix to write_usage is not restyled
- Contrived rule (to drop): Unknown keys in help_styles are silently ignored
- Contrived rule (to drop): Only 'heading' and 'term' keys

**Difficulty: 2/5.** The existing ANSI-aware width infrastructure removes the main claimed trap. What's left is a handful of independent local edits that are each specified directly.

- Interacting rules: 3 · Survives an explicit spec: no
- Likely failure: Always passing heading_style/term_style from make_formatter. Or styling an explicit write_usage prefix. Or missing parent inheritance when help_styles is None.
- Confirmed trap: make_formatter must pass the new kwargs only when help_styles is set (core.py:648-650). Otherwise custom formatter_class subclasses break.
- Confirmed trap: Heading style must include the colon that write_heading appends (formatting.py:206).
- Confirmed trap: help_styles must be inherited in Context.__init__, in the same way color is.
- Rejected trap: The column-misalignment trap is mostly not real. measure_table already uses term_len (formatting.py:19), write_dl pads with term_len (formatting.py:255-256), and wrap_text/TextWrapper are ANSI-aware since 8.4 (formatting.py:56-60, _textwrap.py:89-154). Styling the terms before measuring aligns correctly for free.
- Rejected trap: There is no extra colour-handling work. Help and usage errors are already echoed with ctx.color (exceptions.py:105-106), so color=False strips the ANSI codes.
- Suggested hardening: term_style applies only to the option names in the first column, not to the metavar or separators. In '-n, --name TEXT' only '-n' and '--name' are styled; in '--shout / --no-shout' both names are styled but the ' / ' is not. This means changing Option.get_help_record/_write_opts (or passing structured terms), while alignment still uses visible width.
