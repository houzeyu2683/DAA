Reference:
- https://docs.langchain.com/oss/python/langgraph/overview
- https://docs.langchain.com/oss/python/langchain/overview
- https://gradio.app/

Ask anytime before do the operations

Naming convention (compound variable names like `file_input`):
- Modifier (the first part) stays singular by default, e.g. `file_input`, not `files_input` — English attributive nouns are normally singular regardless of how many items they refer to (cf. "file cabinet", not "files cabinet").
- Head noun (the last part) is plural only if there are actually multiple distinct instances of that thing, e.g. `file_paths` (a real list of paths) vs `file_input` (one widget instance, even if it accepts multiple files) — don't pluralize just because the underlying data can hold multiple values.

Nested function definitions:
- Don't define a `def` inside another function unless it carries a decorator (e.g. `@tool`). Decorated nested `def`s are the one allowed case, since they typically need to close over an outer variable at construction time.
- A plain (non-decorated) helper that a function needs internally belongs at module level, not nested inside it.