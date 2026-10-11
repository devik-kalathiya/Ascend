# Jibun (Python)

The Senior Dev Learning Companion — a Python port of the Node.js CLI. Write your idea in `IDEA.md`, let Jibun
generate a day-wise curriculum, and build it yourself while Jibun watches your files, validates each step,
gives hints (never answers) and reviews each day.

## Install

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e .                                       # or: pip install -r requirements.txt
cp .env.example .env                                   # then put your GROQ_API_KEY in it
```

## Use

```bash
mkdir my-project && cd my-project
echo "# Todo app\nA simple todo app." > IDEA.md

jibun init            # generate INSTRUCTION.md  (--force to regenerate)
jibun start           # watch mode: [h] hint  [r] re-show step  [d] day review  [q] quit
jibun hint            # one-off hint for the current step
jibun review          # review a day  (-d N for a specific day, --ack to move on anyway)
jibun status          # progress per day
```

Without installing: `python -m jibun <command>` from the repo root (set `PYTHONPATH` to it when running
inside a project folder).

`state.json`, `INSTRUCTION.md`, reviews and snapshots use the same formats as the Node version, so existing
projects keep working.

## Tests

```bash
python -m unittest discover -s tests -t .
```

## Layout (JS → Python)

| Node                          | Python                       |
|-------------------------------|------------------------------|
| `bin/jibun.js` (commander)    | `jibun/cli.py` (click)       |
| `src/commands/*.js`           | `jibun/commands/*.py`        |
| `src/core/validator.js`       | `jibun/validator.py`         |
| `src/core/{llm,planner}.js`   | `jibun/{llm,planner,prompts}.py` |
| `src/core/hinting.js`         | `jibun/hinting.py`           |
| `src/core/watcher.js` (chokidar) | `jibun/watcher.py` (watchdog) |
| `src/core/intervention.js`    | `jibun/intervention.py`      |
| `src/agent/*.js`              | `jibun/{gate,snapshot,review_agent}.py` |
| `diff` package                | `difflib`                    |
| `chalk`                       | `colorama`                   |

## Notes on the port

- Everything is synchronous; in watch mode the file watcher, the "stuck?" timer and the keyboard feed a
  single loop, so nothing runs concurrently.
- JS syntax checks of the learner's files use `node --check` when Node is installed, otherwise a built-in
  bracket/string scanner (Node is **not** required).
- `JIBUN_MODEL` is read at call time, so setting it in `.env` works.
- Handlebars template (`templates/instruction.md.hbs`) was never used by the Node code, so it is not ported.
