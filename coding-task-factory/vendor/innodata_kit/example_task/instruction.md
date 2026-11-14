# Add a `truncate` helper to `stringkit`

`stringkit` is a tiny string-utilities library. It currently exposes one function, `slugify`.
Add a second public function, `truncate`, for shortening text to a maximum display length.

## Public interface

```python
truncate(text: str, limit: int, suffix: str = "…") -> str
```

Export it from the package so that `from stringkit import truncate` works, and keep
`slugify` exported and unchanged.

## Required behavior

Return a shortened copy of `text` that is at most `limit` characters long:

1. **Short enough already.** If `len(text) <= limit`, return `text` unchanged.
2. **Needs shortening.** If `len(text) > limit`, return a string of length **exactly** `limit`
   that ends with `suffix`: keep the first `limit - len(suffix)` characters of `text` and append
   `suffix`.
3. **Limit at or below the suffix length.** If `limit <= len(suffix)`, there is no room for any of
   `text`; return just the first `limit` characters of `suffix` (`suffix[:limit]`).
4. **Custom suffix.** `suffix` may be any string (e.g. `"..."`); the rules above use its actual
   length. The default suffix is the single-character ellipsis `"…"` (U+2026).
5. **Invalid input.** If `limit < 0`, raise `ValueError`.

The result is measured in characters (Python `str` length), counting the suffix.

## Examples

| Call | Result |
|---|---|
| `truncate("hello", 10)` | `"hello"` |
| `truncate("hello world", 8)` | `"hello w…"` |
| `truncate("hello world", 8, suffix="...")` | `"hello..."` |
| `truncate("hello", 2, suffix="...")` | `".."` |
| `truncate("hello", -1)` | raises `ValueError` |

## Acceptance criteria

- `from stringkit import truncate` succeeds and `slugify` still works as before.
- All five behaviors above hold, including the exact-length guarantee and the `ValueError` on a
  negative limit.
