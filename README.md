# bluecopa-robot

Scaffold a new Bluecopa RPA robot — minimal, runnable, with **docs-for-Claude** baked in.

The robot equivalent of `create-bluecopa-react-app`: one command lays down a runnable
robot skeleton **and** the `CLAUDE.md` + `docs/building-a-bluecopa-robot.md` that tell a
human or Claude exactly how to build and deploy it.

## Install (one time)

**Prerequisite:** Python 3.9 (the same version the robots run on).

"Installing" here means turning `bluecopa-robot` into a command you can type in any
terminal. You only do this once.

```bash
# 1. Be inside this scaffold folder — the one that contains pyproject.toml.
#    (If you're already here, skip this. Otherwise cd into it.)
cd path\to\bluecopa-robot-scaffold

# 2. Install it as a command
pip install -e .
```

What that second line does:
- `pip install` — install a Python tool.
- `.` — "the project in the current folder" (this scaffold).
- `-e` — *editable* install: it points at these files instead of copying them, so if the
  template is ever updated, you get the update without reinstalling.

After it finishes, the command `bluecopa-robot` works from anywhere. Check it:

```bash
bluecopa-robot --version      # prints: bluecopa-robot 0.1.0
```

> Prefer an isolated install? `pipx install .` instead of `pip install -e .` — same result,
> the command just lives in its own environment.

### For your team — install without cloning

Colleagues do **not** need this repo. `pip` installs the tool straight from git, so all
they run is:

```bash
pip install "git+https://github.com/CH-Akhil/bluecopa-robot-scaffold.git"
bluecopa-robot new my_robot
```

That one `pip install` downloads and installs the `bluecopa-robot` command (templates and
the SDK wheel are bundled inside it). After it, `bluecopa-robot new …` works anywhere.

> Cleaner still: `pipx install "git+https://github.com/CH-Akhil/bluecopa-robot-scaffold.git"`
> — installs the command in its own isolated environment. Update later with
> `pipx upgrade bluecopa-robot` (or re-run the `pip install` with `--upgrade`).

**This repo is private**, so the install needs GitHub auth:
- **SSH** (simplest if you have keys set up): `pip install "git+ssh://git@github.com/CH-Akhil/bluecopa-robot-scaffold.git"`
- **HTTPS + token**: `pip install "git+https://<your-token>@github.com/CH-Akhil/bluecopa-robot-scaffold.git"`

## Use — create a robot

The one command you'll use is `bluecopa-robot new <name>`. It creates a **new folder named
`<name>`** containing a complete, ready-to-run robot.

```bash
bluecopa-robot new invoice_splitter
```

That creates an `invoice_splitter/` folder in your current directory. Run this with **no
flags** and it will *ask you* three things (title, one-line description, and whether the
robot needs GCS), then generate the robot from your answers.

If you'd rather not be asked, pass the answers as flags:

```bash
bluecopa-robot new invoice_splitter --gcs --title "Invoice Splitter" --description "Splits invoices"
```

### The flags

| Flag | What it does |
|------|--------------|
| *(the name)* | `invoice_splitter` becomes the folder name, the module `rpa/invoice_splitter.py`, and the class `InvoiceSplitterRobot`. You can type `"Invoice Splitter"` too — it's converted to `invoice_splitter`. |
| `--gcs` | Include Google Cloud Storage support: adds `rpa/gcs.py` (read/write GCS with ambient auth) and `google-cloud-storage` to requirements. Use this when the robot reads or writes files in GCS. |
| `--no-gcs` | The opposite — a bare robot with no storage code or dependency. Use this when the robot doesn't touch GCS. |
| `--title "..."` | The human name shown in the platform's setup form (e.g. "Invoice Splitter"). |
| `--description "..."` | A one-line description, used in the generated README and `CLAUDE.md`. |
| `--dir <path>` | *Where* to create the robot folder. Defaults to your current directory. |

`--gcs` and `--no-gcs` are opposites — pass at most one. If you pass neither and you're in
an interactive terminal, it asks; otherwise it defaults to **no GCS**.

### The three examples explained

```bash
bluecopa-robot new invoice_splitter
```
→ Creates `invoice_splitter/` here, **asking you** for title, description, and GCS.

```bash
bluecopa-robot new invoice_splitter --gcs --title "Invoice Splitter" --description "Splits invoices"
```
→ Creates `invoice_splitter/` here **with** the GCS helper, and no questions — the title and
description are supplied as flags.

```bash
bluecopa-robot new invoice_splitter --no-gcs --dir ../robots
```
→ Creates the robot **without** GCS, in the `../robots` folder (one level up) instead of the
current directory.

After generating, `cd` into the new folder and follow the "Next steps" the command prints
(install deps, implement `run_robot`, test locally) — also in the robot's own `README.md`.

## What you get

A standalone `<name>/` folder:

- `main.py`, `Dockerfile` (`python:3.9-slim`), `requirements.txt`, the SDK wheel in `libs/`
- `rpa/<name>.py` — a **runnable** `run_robot` stub (writes a placeholder output) with
  `_unwrap_data`
- `rpa/spec.json`, `secrets/*.sample.json`
- `rpa/gcs.py` **only** with `--gcs` (ambient-auth GCS helper) + `google-cloud-storage`
- `CLAUDE.md` + `docs/building-a-bluecopa-robot.md` — the runtime contract, config/spec
  traps, filebox gotchas, and a client-agnostic deploy guide

It is **client-agnostic**: no client repo name, registry, or ECR path is ever emitted.

## Maintaining the template

- The vendored SDK wheel lives at `src/bluecopa_robot/_assets/`. When the SDK updates,
  replace it and bump the filename in `generator.py` (`WHEEL_NAME`) + the `Dockerfile`
  template.
- Template files live under `src/bluecopa_robot/_templates/` (each ends `.tmpl`; the
  generator strips that and substitutes `{{placeholders}}`). `requirements.txt` is
  generated in code, not templated.

## Test

```bash
python -m pytest        # or: python tests/test_generate.py
```
