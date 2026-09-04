# GCS & External Services Reference

Authentication patterns, local dev setup, and Docker testing for Bluecopa robots that talk to Google Cloud Storage, BigQuery, or other external services.

> This is a companion to the [Robot Creation Guide](robot-creation-guide.md). Read that first for the basic robot structure.

---

## Table of Contents

1. [Ambient Authentication](#ambient-authentication)
2. [GCS Operations](#gcs-operations)
3. [BigQuery Operations](#bigquery-operations)
4. [Local Development Setup](#local-development-setup)
5. [Docker Testing with Real GCS](#docker-testing-with-real-gcs)
6. [Dependencies](#dependencies)
7. [Common Patterns](#common-patterns)

---

## Ambient Authentication

On the Bluecopa platform, credentials are provided automatically via workload identity. The container already has a service account and project.

**The rule: create clients with NO arguments.**

```python
from google.cloud import storage, bigquery

# CORRECT — ambient auth
storage_client = storage.Client()
bq_client = bigquery.Client()

# WRONG — never do any of these
# storage_client = storage.Client(project="my-project")
# storage_client = storage.Client(credentials=creds)
# bq_client = bigquery.Client(project="my-project", credentials=creds)
```

**Never** put credentials, project IDs, or service account keys in:
- Config (`config.json` / `spec.json`)
- Code (constants, env var reads)
- Params

Credentials are ambient. Project is ambient. Configuration comes from `config` (bucket names, paths). That's it.

---

## GCS Operations

### Thread-safe client singleton

```python
import threading
from google.cloud import storage

_client = None
_client_lock = threading.Lock()

def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = storage.Client()
    return _client
```

> Use a singleton for robots with concurrent workers (ThreadPoolExecutor). Creating a new client per thread is wasteful.

### Common GCS helpers

The scaffold's `--gcs` flag generates `rpa/gcs.py` with these ready to use:

```python
def parse_gs_uri(uri: str) -> tuple:
    """Parse gs://bucket/path into (bucket, path)."""

def list_blobs(bucket_name: str, prefix: str) -> list:
    """List (name, size_bytes) for every blob under the prefix."""

def download_blob(bucket_name: str, blob_name: str, dest_dir: str) -> str:
    """Download a blob to a local file. Returns the local path."""

def upload_blob(local_path: str, bucket_name: str, dest_blob: str) -> str:
    """Upload a local file. Returns the gs:// URI."""
```

### Filebox = GCS path

A Bluecopa filebox is a folder inside a GCS bucket. A filebox "blob id" is the object path (e.g. `copa_filebox/<boxId>/<ts>/<file>`). Combine with the bucket name to get the full GCS URI: `gs://<bucket>/<blobId>`.

---

## BigQuery Operations

### Client setup

Same ambient pattern as GCS:

```python
from google.cloud import bigquery

_client = None
_client_lock = threading.Lock()

def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = bigquery.Client()
    return _client
```

### Parameterized queries

Always use parameterized queries to prevent SQL injection:

```python
query = """
    SELECT * FROM `{table_ref}`
    WHERE CAST(`{filter_col}` AS STRING) = @filter_val
"""
job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("filter_val", "STRING", filter_val),
    ]
)
result = client.query(query, job_config=job_config).result()
```

> Column and table names can't be parameterized in BQ — they go in f-strings. But filter **values** must always be parameters.

### Region discovery

BigQuery datasets have a location (region). To query `INFORMATION_SCHEMA.TABLES` across a project, you need the region:

```python
def _discover_regions() -> list:
    client = _get_client()
    dataset_refs = list(client.list_datasets(max_results=1))
    if not dataset_refs:
        return ["us"]
    try:
        ds = client.get_dataset(dataset_refs[0].reference)
        return [ds.location] if ds.location else ["us"]
    except Exception:
        return ["us"]
```

> **Gotcha:** `list_datasets()` returns `DatasetListItem` objects which do NOT have `.location`. You must call `get_dataset()` to get the full `Dataset` object with the location attribute.

### BQ extract to GCS

BQ can write query results directly to GCS as CSV:

```python
dest_uri = f"gs://{bucket}/{prefix}/{filename}"
extract_config = bigquery.ExtractJobConfig(
    destination_format=bigquery.DestinationFormat.CSV,
    print_header=True,
)
extract_job = client.extract_table(source_table, dest_uri, job_config=extract_config)
extract_job.result()
```

> **1 GB limit:** BQ extract with an exact filename (no wildcard) caps at 1 GB. For larger exports, use a wildcard pattern like `gs://bucket/prefix/file-*.csv`.

---

## Local Development Setup

### Google Cloud SDK (ADC)

```bash
# Login and create Application Default Credentials
gcloud auth application-default login
```

User ADC credentials do NOT carry a default project. You must set it:

```bash
# Windows
set GOOGLE_CLOUD_PROJECT=my-project-id

# Linux/macOS
export GOOGLE_CLOUD_PROJECT=my-project-id
```

Without it you'll get: `Project was not passed and could not be determined from the environment`

### Alternative: Service account key

```bash
# Windows
set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account-key.json

# Linux/macOS
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

Service account keys carry the project, so `GOOGLE_CLOUD_PROJECT` is not needed.

### Python version note

The SDK wheel targets Python 3.9. `google-auth` on 3.9 prints a harmless EOL FutureWarning — ignore it.

---

## Docker Testing with Real GCS

Mount your ADC credentials into the container:

### Linux/macOS

```bash
docker run \
  -v ~/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
  -e GOOGLE_CLOUD_PROJECT=my-project-id \
  my-robot-image python main.py run \
    --config /app/secrets/config.json \
    --input-file-path dummy \
    --output-folder-path /app/output \
    --params /app/secrets/params.json
```

### Windows (Git Bash)

Prefix with `MSYS_NO_PATHCONV=1` to prevent Git Bash from mangling the container paths:

```bash
MSYS_NO_PATHCONV=1 docker run \
  -v "$APPDATA/gcloud/application_default_credentials.json:/tmp/adc.json:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json \
  -e GOOGLE_CLOUD_PROJECT=my-project-id \
  my-robot-image python main.py run \
    --config /app/secrets/config.json \
    --input-file-path dummy \
    --output-folder-path /app/output \
    --params /app/secrets/params.json
```

> On Windows, gcloud ADC lives at `%APPDATA%\gcloud\application_default_credentials.json`.

---

## Dependencies

Add these to `requirements.txt` as needed:

```
# GCS only
google-cloud-storage==2.16.0

# BigQuery only
google-cloud-bigquery>=3.20.0

# Both
google-cloud-storage==2.16.0
google-cloud-bigquery>=3.20.0
```

> The scaffold's `--gcs` flag adds `google-cloud-storage` automatically.

---

## Common Patterns

### Parallel GCS operations

Use `ThreadPoolExecutor` for concurrent blob operations:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=50) as pool:
    futures = {
        pool.submit(upload_blob, path, bucket, dest): path
        for path, dest in file_map.items()
    }
    for fut in as_completed(futures):
        path = futures[fut]
        try:
            uri = fut.result()
            logger.info("Uploaded: %s -> %s", path, uri)
        except Exception as e:
            logger.error("Failed: %s — %s", path, e)
```

### Config-driven bucket names

Bucket names come from config (set per robot instance on the platform), never hardcoded:

```python
bucket = config.get("bucket_name")
if not bucket:
    raise ValueError("Config missing required field 'bucket_name'.")
```

### Checking blob size after upload

```python
blob = storage.Client().bucket(bucket).blob(path)
blob.reload()
size_bytes = blob.size or 0
```

### Cleaning up GCS prefixes

```python
def delete_prefix(bucket_name: str, prefix: str):
    client = _get_client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    if blobs:
        bucket.delete_blobs(blobs)
```
