# ADR 0010: Filesystem-Backed Prompt Injection Pattern

**Status:** Accepted
**Date:** 2026-04-08

## Context

The project began with agent system prompts as Python string constants defined at module level inside each agent file (e.g. `STRATEGIST_SYSTEM_PROMPT` in `agents/strategist.py`). This worked for early development but became unmanageable as the prompts grew and as the project added configurable elements:

1. **Creative philosophies** for the Creative Director — five interchangeable prompt fragments that shape the CD's evaluation lens. Hardcoding these as Python constants would have meant a large dict-of-strings inside the agent file, mixing prompt content with code logic.
2. **Strategic philosophies** for the strategist — same pattern, applied to a different agent.
3. **Creative philosophies** for the creative agent — the same five files reused for a third agent.
4. **A creative brief template** — a long, structured markdown document that defines the output format the strategist should produce. Embedding it as a Python string would have made `strategist.py` mostly prompt content rather than code.
5. **Proposition writing guidance** — a detailed reference document on how to write a single-minded proposition, injected into the strategist's prompt to improve output quality.

The prompt content also needed to be **editable by non-engineers** — strategists and creative leads who want to refine philosophies or templates without touching Python files.

Alternatives considered:

- **Inline string constants.** Original approach. Doesn't scale, mixes content with code, blocks non-engineer editing.
- **YAML or JSON prompt files.** Structured but adds parsing overhead, escaping headaches for prompt content with quotes/colons/special characters, and requires schema decisions for what should be free-form text.
- **A prompt management library** (LangChain Hub, Promptfoo, etc.). Heavier dependency, external service coupling, and unnecessary for a project where prompts live alongside the code in the same repo.
- **Plain text files on disk, organised by category, loaded by a small loader function.** Each prompt is its own `.txt` file in a categorised directory. Loaded at runtime by a generalised `load_prompt(category, name)` function. Content is plain prose that anyone can edit.

## Decision

Store prompt content as plain text files on disk, organised by category under `src/agt_sea/prompts/`. Categories currently in use:

- `prompts/philosophies/creative/` — five creative philosophy files (used by both the creative agent and CD)
- `prompts/philosophies/strategic/` — five strategic philosophy files (used by the strategist)
- `prompts/templates/` — output format templates (currently: `creative_brief.txt`)
- `prompts/guidance/` — supplementary guidance documents (currently: `proposition_101_lite.txt`)

A single loader function in `prompts/loader.py` handles all reads:

```python
def load_prompt(category: str, name: str) -> str:
    """Load a prompt text file from disk."""
    path = _PROMPTS_DIR / category / f"{name}.txt"
    return path.read_text().strip()
```

Convenience wrappers for the most common categories provide type-safe access:

```python
def load_creative_philosophy(philosophy: CreativePhilosophy) -> str:
    return load_prompt("philosophies/creative", philosophy.value)

def load_strategic_philosophy(philosophy: StrategicPhilosophy) -> str:
    return load_prompt("philosophies/strategic", philosophy.value)

def load_template(name: str) -> str:
    return load_prompt("templates", name)

def load_guidance(name: str) -> str:
    return load_prompt("guidance", name)
```

Agents build their system prompts via private `_build_system_prompt()` functions that compose the static parts of the prompt (the agent's role, instructions, constraints) with dynamically loaded content (philosophies, templates, guidance). The static parts remain inline in the agent file because they're agent-specific and rarely change. The dynamic parts come from disk because they're shared, swappable, or non-engineer-editable.

A `NEUTRAL` enum value exists for both `CreativePhilosophy` and `StrategicPhilosophy`. When neutral is selected, `_build_system_prompt()` skips the philosophy injection block entirely — the LLM sees no mention of any philosophy at all, exactly as if the feature didn't exist. This is handled in code, not as a `neutral.txt` file, because the desired behaviour is *absence* of injection rather than injection of a neutral document.

## Consequences

- **Positive:** Prompt content is editable by anyone with a text editor. Strategists, creative leads, and prompt engineers can iterate on philosophies without touching Python.
- **Positive:** Categories scale cleanly. Adding a new prompt type (e.g. `prompts/personas/`) is "create the directory, add files, optionally add a convenience wrapper" — no architectural changes.
- **Positive:** The same philosophy files can be reused by multiple agents. The five creative philosophies serve both the creative agent and the CD without duplication.
- **Positive:** The neutral-as-skip pattern means "no philosophy" is a first-class option, not a workaround. Default state is genuinely unflavoured rather than "vaguely opinionated by accident."
- **Positive:** Loading is lazy (per call) rather than at module import. Edits to prompt files take effect on the next agent run without restarting the app — useful for iterating on prompts during development.
- **Positive:** The directory structure matches the enum structure (one file per enum value, named after the value), making the mapping obvious and validation trivial. A new philosophy is "add an enum value, add a file with the matching name."
- **Negative:** Lazy loading means file I/O on every agent invocation. Negligible at the project's current scale, but if the agents start being called at high frequency, a simple in-memory cache (`functools.lru_cache`) on `load_prompt` would eliminate it.
- **Negative:** No validation that every enum value has a corresponding file. A new enum value without a file will fail at runtime with `FileNotFoundError`, not at import. A startup check could be added but is overkill at this scale.
- **Negative:** Plain text files don't support templating natively. If prompts ever need variable substitution (e.g. injecting brand names), we'll need to either move to a format that supports it or layer Python `.format()` over the loaded text. The latter is preferable when the time comes — keeps the files readable.
- **Negative:** Prompt content is not version-controlled separately from code. Changes to a philosophy file appear in `git log` alongside code changes. Acceptable for now; if prompts start having their own iteration cycle, they could move to a separate repo or content management system later.
