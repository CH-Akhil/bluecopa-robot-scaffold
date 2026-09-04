# Bluecopa RPA Robot Creation Guide

A step-by-step guide to building robots in the Bluecopa RPA framework.

---

## Table of Contents

1. [Getting Started with the Scaffold](#getting-started-with-the-scaffold)
2. [How a Robot Works](#how-a-robot-works)
3. [Project Structure](#project-structure)
4. [Step-by-Step: Build Your First Robot](#step-by-step-build-your-first-robot)
5. [Params: Receiving Runtime Data](#params-receiving-runtime-data)
6. [Configuration: spec.json](#configuration-specjson)
7. [Error Handling](#error-handling)
8. [Patterns: Simple vs Complex Robots](#patterns-simple-vs-complex-robots)
9. [Running Locally](#running-locally)
10. [Deploying to the Platform](#deploying-to-the-platform)
11. [Conventions Reference](#conventions-reference)
12. [Quick Checklist](#quick-checklist)
13. [Troubleshooting](#troubleshooting)

---

## Getting Started with the Scaffold

The fastest way to create a new robot is the `bluecopa-robot` CLI. One command generates a complete, runnable robot project.

### Install the CLI (one time)

```bash
pip install bluecopa-robot
```

Verify it works:
```bash
bluecopa-robot --version      # prints: bluecopa-robot 0.1.0
```

> **Tip:** Use `pipx install bluecopa-robot` instead of `pip install` for a cleaner isolated install.

### Create a robot

```bash
bluecopa-robot new my_robot
```

This creates a `my_robot/` folder with everything ready to run. It will ask you three things interactively:
- **Title** — shown in the platform's setup form (e.g. "My Robot")
- **Description** — one-line summary
- **GCS** — whether the robot reads/writes Google Cloud Storage

Or skip the questions with flags:

```bash
bluecopa-robot new my_robot --gcs --title "My Robot" --description "Does something useful"
```

### CLI flags

| Flag | What it does |
|------|---|
| *(the name)* | Folder name, module name, and class name. `my_robot` -> `MyRobotRobot` in `rpa/my_robot.py`. Accepts spaces too: `"My Robot"` -> `my_robot` |
| `--gcs` | Include GCS support: adds `rpa/gcs.py` (ambient-auth helpers) + `google-cloud-storage` dependency |
| `--no-gcs` | No GCS code or dependency (default in non-interactive mode) |
| `--title "..."` | Human-readable title for the platform setup form |
| `--description "..."` | One-line description for README and CLAUDE.md |
| `--dir <path>` | Where to create the folder (default: current directory) |

### What you get

```
my_robot/
├── main.py                  # Entrypoint (3 lines)
├── Dockerfile               # python:3.9-slim + SDK wheel
├── requirements.txt         # Your dependencies (pinned)
├── libs/                    # SDK wheel (bundled automatically)
├── rpa/
│   ├── my_robot.py          # Runnable stub with _unwrap_data
│   ├── spec.json            # Config schema (empty, ready to fill)
│   ├── gcs.py               # GCS helpers (only with --gcs)
│   └── Exceptions/
├── secrets/
│   ├── config.sample.json   # Placeholder config
│   └── params.sample.json   # Placeholder params
├── docs/
│   └── building-a-bluecopa-robot.md   # Runtime contract & deploy guide
├── CLAUDE.md                # AI context for Claude Code
└── README.md                # Quick start instructions
```

### Next steps after scaffolding

```bash
cd my_robot

# 1. Set up virtual environment
python -m venv .venv
.venv\Scripts\activate                     # Windows
# source .venv/bin/activate                # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt
pip install libs/bluecopa_rpa_python-0.1.0-py3-none-any.whl

# 3. Run the stub (confirms wiring works)
python main.py run --config secrets/config.sample.json --params secrets/params.sample.json --input-file-path dummy --output-folder-path output

# 4. Implement your logic in rpa/my_robot.py
# 5. Define setup fields in rpa/spec.json
# 6. Read docs/building-a-bluecopa-robot.md before deploying
```

The stub writes a placeholder file to `output/` so you can verify the wiring before writing any real logic.

> **Already have a robot and building manually?** The sections below document the conventions and patterns the scaffold follows — use them as a reference.

---

## How a Robot Works

Every robot is a self-contained Python package that:

1. Extends `AbstractRobot` from the Bluecopa SDK
2. Receives an **input file path** and an **output folder path** from the platform
3. Optionally receives **params** (runtime data like file lists, filter values, entity IDs)
4. Reads its **config** from the platform (bucket names, feature flags, etc.)
5. Does its work and writes output to the output folder (which the platform delivers to the filebox)
6. Is packaged as a **Docker container** for deployment

The platform calls your robot like this:

```
python main.py run --config <path> --input-file-path <path> --output-folder-path <path> --params <path>
```

The SDK handles all the argument parsing, file reading, and message protocol. You only write the `run_robot()` method.

---

## Project Structure

```
my_robot/
├── __init__.py              # Empty — marks root as a Python package
├── Dockerfile               # Container definition (identical across all robots)
├── main.py                  # Entrypoint — 3 lines, never changes
├── requirements.txt         # Third-party pip dependencies (NOT the SDK)
├── libs/
│   └── bluecopa_rpa_python-0.1.0-py3-none-any.whl   # SDK wheel
├── rpa/
│   ├── __init__.py          # Empty
│   ├── my_robot.py          # Robot class — extends AbstractRobot
│   ├── spec.json            # JSON Schema for config (drives platform UI)
│   └── ...                  # Additional modules as needed
├── secrets/
│   ├── config.sample.json   # Example config (committed, no real values)
│   └── params.sample.json   # Example params (committed, no real values)
└── docs/
    └── building-a-bluecopa-robot.md  # Runtime contract and deploy guide
```

> **Naming:** Directory = `snake_case`. Class = `PascalCase`. Files = `snake_case`.
> Example: `dataset_csv_export/` -> `DatasetCsvExportRobot` in `dataset_csv_export.py`

---

## Step-by-Step: Build Your First Robot

> **Shortcut:** `bluecopa-robot new my_robot` generates all of this. Use these steps as a reference or if you're setting up manually.

### 1. Create the directory

```
my_robot/
├── __init__.py
├── rpa/
│   └── __init__.py
├── secrets/
└── libs/
```

Copy `bluecopa_rpa_python-0.1.0-py3-none-any.whl` from any existing robot's `libs/` folder.

### 2. main.py

Always the same 3-line pattern:

```python
import sys
from bluecopa_rpa_sdk.entrypoint import launch
from rpa.my_robot import MyRobot

if __name__ == "__main__":
    source = MyRobot()
    launch(source, sys.argv[1:])
```

> No logic here — just wiring.

### 3. Dockerfile

Identical across all robots. Copy as-is:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY libs/bluecopa_rpa_python-0.1.0-py3-none-any.whl /app/bluecopa_rpa_python-0.1.0-py3-none-any.whl
RUN pip install --no-cache-dir /app/*.whl

COPY . .

ENV ROBOT_ENTRYPOINT="python main.py"
CMD ["python", "main.py"]
```

> Always `python:3.9-slim`. Always set `ROBOT_ENTRYPOINT`.

### 4. requirements.txt

Only third-party packages. The SDK is installed separately from the wheel.

```
pandas==2.2.1
openpyxl==3.1.5
```

> Pin exact versions (`==`). Do not include the SDK here.

### 5. rpa/my_robot.py — The Robot Class

```python
import json
import logging
import os
from typing import Any, List, Mapping, MutableMapping, Union

from bluecopa_rpa_sdk.robots.abstract_robot import AbstractRobot


class MyRobot(AbstractRobot):

    def get_config_spec(self):
        return {}

    def run_robot(
        self,
        logger: logging.Logger,
        config: Mapping[str, Any],
        input_file_path: str,
        output_folder_path: str,
        state: Union[List[Any], MutableMapping[str, Any]] = None,
        params: Union[List[Any], MutableMapping[str, Any]] = None,
    ):
        config = config or {}
        data = self._unwrap_data(params) if params else {}
        logger.info("Config: %s", dict(config))
        logger.info("Params: %s", data)

        # TODO: your logic here — read from data/config, do the work,
        # write output into output_folder_path

        os.makedirs(output_folder_path, exist_ok=True)

    @staticmethod
    def _unwrap_data(obj):
        """Unwrap the Bluecopa {"data": ...} envelope (stringified OR object form)."""
        if not isinstance(obj, dict):
            return obj
        data = obj.get("data", obj)
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except (json.JSONDecodeError, TypeError):
                pass
        return data
```

**Key rules:**

- `get_config_spec()` always returns `{}` — the platform reads `spec.json` directly
- Keep `params=None` as the default — ensures compatibility with both SDK versions (older 5-arg and newer 6-arg)
- The robot class is **orchestration only** — delegate business logic to other modules
- Use `logger.info()` / `logger.warning()` / `logger.error()` for logging (not `print()`)
- Write output files into `output_folder_path` — the platform delivers them to the filebox

### 6. rpa/spec.json — Config Schema

Defines the configuration UI on the Bluecopa platform.

```json
{
  "documentationUrl": "https://docs.robots.io/integrations",
  "robotSpecification": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "My Robot",
    "type": "object",
    "required": [],
    "properties": {}
  }
}
```

> See the [Configuration](#configuration-specjson) section below for adding parameters.

### 7. secrets/ — Local Test Files

Create sample files with placeholder values (committed to git):

**secrets/config.sample.json:**
```json
{}
```

**secrets/params.sample.json:**
```json
{
  "data": {
    "example_key": "example_value"
  }
}
```

For local testing, copy these to `config.json` / `params.json` (gitignored) and fill in real values.

---

## Params: Receiving Runtime Data

The platform passes runtime data via `--params` (a JSON file path). The SDK reads the file and hands parsed JSON to `run_robot(params=...)`.

### Payload format

The platform wraps params in a `data` key. The `data` value can be either a JSON string (double-encoded) or a plain object — both forms exist in production:

```json
// Form 1: double-encoded string
{"data": "{\"source_table\":\"proj.ds.tbl\",\"filter_column\":\"date\"}"}

// Form 2: plain object
{"data": {"source_table": "proj.ds.tbl", "filter_column": "date"}}
```

The `_unwrap_data` helper in the robot template handles both forms automatically.

### Making params fields optional

Not every run needs every param. Validate what's required, allow the rest to be omitted:

```python
def parse_params(data: dict):
    # Required
    source = data.get("source_table")
    if not source:
        raise ValueError("Params missing required field 'source_table'.")

    # Optional — None if not provided
    filter_col = data.get("filter_column") or None
    group_col = data.get("group_column") or None

    # Paired fields — both or neither
    filter_val = data.get("filter_value")
    if bool(filter_col) != bool(filter_val):
        raise ValueError("filter_column and filter_value must both be provided or both omitted.")
```

### input_file_path vs params

- `input_file_path` is the **trigger file** dropped into the filebox — a local file path
- `params` is the **runtime payload** with your actual data
- A params-driven robot usually ignores `input_file_path` and works from `data`
- The platform still requires a trigger file to start the run

---

## Configuration: spec.json

`rpa/spec.json` is a JSON Schema that drives the operator's setup form on the platform.

### The required + default trap

A `"default"` in `spec.json` only pre-fills the **form**. It is **NOT** injected into the config at runtime. So:

- If you mark a field `required` and the config doesn't carry it, the SDK rejects the run **before** `run_robot` executes with `'<field>' is a required property`
- The `default` in the schema doesn't save you at runtime

**Decision guide:**
- **Genuinely mandatory** -> put it in `required`. Accept that a missing value is a hard failure.
- **Optional with a sensible default** -> leave it out of `required`. Default it **in code**: `config.get("max_workers", 20)`
- **Tuning knobs** (worker counts, timeouts) -> keep them out of `spec.json` entirely. Own them in code, let them be overridden via config.

### Example with parameters

```json
{
  "documentationUrl": "https://docs.robots.io/integrations",
  "robotSpecification": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "My Robot",
    "type": "object",
    "required": ["bucket_name"],
    "properties": {
      "bucket_name": {
        "type": "string",
        "title": "GCS Bucket",
        "description": "GCS bucket for output files.",
        "label": "GCS Bucket"
      },
      "file_type": {
        "type": "string",
        "title": "File Type",
        "description": "Type of file to process.",
        "enum": ["csv", "xlsx"],
        "default": "xlsx",
        "label": "File Type",
        "format": "radio"
      },
      "enable_validation": {
        "type": "boolean",
        "title": "Enable Validation",
        "description": "Run validation checks before processing.",
        "default": true,
        "label": "Enable Validation",
        "format": "checkbox"
      }
    }
  }
}
```

**Rules:**
- Always include `"documentationUrl"` and `"$schema"`
- Add `"label"` on every property (used by the platform UI)
- Use `"format": "radio"` for enums, `"format": "checkbox"` for booleans
- For complex nested configs, use `oneOf` — see `psg_file_clean/rpa/spec.json` for reference

---

## Error Handling

### Let exceptions propagate

The platform needs to see failures to mark the run as failed and show errors in the UI. Do **not** swallow exceptions:

```python
# WRONG — swallows the error, platform thinks the run succeeded
try:
    result = process_files(input_file_path)
except Exception as ex:
    logger.error("Robot failed: ", ex)

# CORRECT — let the exception propagate
result = process_files(input_file_path)

# ALSO CORRECT — catch specific cases, re-raise the rest
try:
    result = process_files(input_file_path)
except FileNotFoundError:
    raise ValueError(f"Input file not found: {input_file_path}")
```

### Validate early with clear messages

```python
if total_rows == 0:
    raise ValueError(
        f"Zero rows matched filter {filter_col}='{filter_val}' "
        f"on table {table_ref}."
    )

if not bucket_name:
    raise ValueError("Config missing required field 'bucket_name'.")
```

> The platform captures the exception message and displays it in the run log. Make messages specific — include the actual values that caused the failure.

---

## Patterns: Simple vs Complex Robots

### Pattern A: Simple File Transform

For robots that take a file in, process it, write a file out.

**Examples:** `txt_to_csv_conversion`, `excel_formatter_robot`, `psg_file_clean`

```
rpa/
├── my_robot.py     # Orchestration: read input -> call tasks -> copy output
├── tasks.py        # All processing logic as pure functions
└── spec.json
```

- All business logic in `tasks.py`
- Output goes to a temp file, then robot copies to `output_folder_path`
- Robot class = thin orchestrator

### Pattern B: Complex / External Service Robot

For robots that talk to GCS, BigQuery, APIs, or have multiple processing stages.

**Examples:** `dataset_csv_export`, `gcs_claims_copy_robot`, `mt940_to_csv_conversion_v2`

```
rpa/
├── my_robot.py      # Orchestration: validate -> query -> extract -> manifest
├── bq.py            # BigQuery operations
├── gcs.py           # GCS operations
├── validation.py    # Input validation and parsing
├── naming.py        # File naming logic
├── manifest.py      # Manifest generation
└── spec.json
```

- Split logic by domain instead of a single `tasks.py`
- May write directly to external storage (GCS, etc.) rather than just `output_folder_path`
- Typically params-driven (runtime data via `--params`)

> **When to split:** If your robot has more than ~100 lines of logic, or talks to external services, split into domain modules. A single `tasks.py` becomes unreadable fast.

> **External services (GCS, BigQuery, APIs):** See the separate [GCS & External Services Reference](gcs-external-services-reference.md) for authentication patterns, local dev setup, and Docker testing.

---

## Running Locally

### Setup

```bash
# 1. Create virtual environment (use Python 3.9 to match the SDK wheel)
python -m venv .venv
.venv\Scripts\activate                    # Windows
# source .venv/bin/activate               # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install the SDK wheel
pip install libs/bluecopa_rpa_python-0.1.0-py3-none-any.whl
```

### Copy and fill in config

```bash
copy secrets\config.sample.json secrets\config.json
copy secrets\params.sample.json secrets\params.json
# Edit both with real values for your test
```

### Run the robot

**Without params:**
```bash
python main.py run --config secrets/config.json --input-file-path path/to/input.csv --output-folder-path output/
```

**With params:**
```bash
python main.py run --config secrets/config.json --input-file-path path/to/input.csv --output-folder-path output/ --params secrets/params.json
```

| Argument | Required | Description |
|---|---|---|
| `--config` | Yes | Path to the JSON configuration file |
| `--input-file-path` | Yes | Path to the input file (or `dummy` if params-driven) |
| `--output-folder-path` | No | Output directory (defaults to `outputs/` next to input) |
| `--params` | No | Path to runtime params JSON file |
| `--state` | No | Path to state JSON (for stateful robots) |
| `--debug` | No | Enable debug logging |

### Print the config spec

```bash
python main.py spec
```

> **Important:** A clean local run is necessary but not sufficient. The platform passes different config, credentials, and trigger inputs than what you use locally. See `docs/building-a-bluecopa-robot.md` in your scaffold for the full picture.

---

## Deploying to the Platform

### 1. Add to flipkart_rpa

All robots live in the `bluecopa/flipkart_rpa` monorepo:

```bash
git checkout dev
git pull origin dev
git checkout -b feat/my-robot

# Copy your robot directory into the repo root
cp -r /path/to/my_robot ./my_robot

git add my_robot/
git commit -m "feat: add my_robot"
git push -u origin feat/my-robot
```

Create a PR targeting `dev`.

### 2. Add ECR workflow step

In `.github/workflows/docker-image.yml`, add a build step:

```yaml
- name: bluecopa/my-robot
  env:
    ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
    ECR_REPOSITORY: robotimage/my_robot
    IMAGE_TAG: 0.0.1
  run: |
    docker build --no-cache my_robot/. -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
    docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
```

> The ECR repo (`robotimage/my_robot`) must be created first — coordinate with backend/infra.

### 3. Build and register

After the PR is merged:
1. Trigger the GitHub Actions workflow (manual dispatch) to build and push the Docker image
2. Register the robot on the Bluecopa platform with the ECR image URI
3. The platform reads `spec.json` to generate the config form

> After **any** code change, the image must be **rebuilt** — otherwise the cluster keeps running the old image.

---

## Conventions Reference

| Rule | Detail |
|---|---|
| **Python version** | Always `python:3.9-slim` in Docker |
| **SDK install** | From `.whl` in `libs/`, never from PyPI |
| **Naming** | Directory: `snake_case`. Class: `PascalCase`. File: `snake_case` |
| **main.py** | 3 lines — instantiate + launch. No logic |
| **Dockerfile** | Identical template across all robots |
| **get_config_spec** | Return `{}` — platform reads `spec.json` directly |
| **params=None** | Always keep as default in `run_robot` signature (SDK compatibility) |
| **Logging** | Use `logger.info/warning/error()`, not `print()` |
| **Error handling** | Let exceptions propagate. Never swallow with bare try/except |
| **Config** | Static settings via `config.json` / `spec.json` |
| **Params** | Runtime data via `--params`. Handle both string and object `data` envelope |
| **Dependencies** | Pin exact versions in `requirements.txt` |
| **Secrets** | `secrets/*.json` is gitignored. Commit only `*.sample.json` with placeholders |
| **Output** | Write to `output_folder_path` for platform delivery to filebox |
| **Separation** | Robot class = orchestration. Logic in `tasks.py` or domain modules |
| **No hardcoding** | Never hardcode credentials, project IDs, bucket names, registry URLs, or filebox IDs |

---

## Quick Checklist

Before opening a PR for a new robot:

- [ ] `Dockerfile` matches the template exactly
- [ ] `main.py` only instantiates the robot and calls `launch()`
- [ ] Robot class extends `AbstractRobot` with `params=None` default
- [ ] `get_config_spec()` returns `{}`
- [ ] All business logic is outside the robot class (in `tasks.py` or domain modules)
- [ ] `_unwrap_data` handles both string and object `data` envelope
- [ ] `rpa/spec.json` has `label` on every property
- [ ] `required` vs optional decided correctly (no `default` mistaken for a runtime safety net)
- [ ] `secrets/config.sample.json` committed with placeholder values
- [ ] `secrets/params.sample.json` committed if the robot uses params
- [ ] No real secrets or credentials in any committed file
- [ ] All dependency versions pinned in `requirements.txt`
- [ ] Exceptions propagate — no bare `try/except` swallowing errors
- [ ] Error messages include the actual values that caused the failure
- [ ] ECR step added to `.github/workflows/docker-image.yml`
- [ ] Ran locally end-to-end

---

## Troubleshooting

| Symptom (pod logs) | Cause / Fix |
|---|---|
| `'<field>' is a required property` | A `required` spec field wasn't in the runtime config. Either set it in the config, or make it optional + default in code. |
| `Filebox File with id <X> does not exist` | Workflow passed a **box** id where a **file** id was expected. Wire the trigger's `filebox_file_id`. |
| `Project was not passed and could not be determined from the environment` | Local run without a project. Set `GOOGLE_CLOUD_PROJECT`. |
| `unrecognized arguments: --params` | Older SDK wheel installed. Use the wheel bundled in `libs/`. |
| Robot runs old behaviour after a fix | Docker image wasn't rebuilt/pushed — cluster runs the stale image. |
| `Zero rows matched filter...` | Filter value doesn't match the column's data type (e.g. TIMESTAMP cast to STRING includes time portion). Check actual values with a BQ query. |
| Feedback loop: robot keeps re-triggering | Output is being written to the same filebox that triggers the robot. Use a separate output filebox. |
