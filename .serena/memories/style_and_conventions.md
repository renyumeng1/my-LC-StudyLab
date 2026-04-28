# Style and Conventions

- Python code uses type hints, e.g. `Optional[str | BaseLanguageModel]`.
- Existing comments/docstrings include Chinese explanations.
- Keep changes small and aligned with LangChain abstractions.
- Prefer provider-neutral LangChain chat model interfaces (`BaseLanguageModel` / chat model Runnable interface) for agent base classes.