# AudioMuse-AI Patterns and Conventions

## Architecture Patterns

### 1. Flask Blueprint Pattern
Each feature is encapsulated in a Blueprint module (`app_*.py`), promoting:
- Modularity and separation of concerns
- Independent feature development
- Clear routing namespaces

```python
# Example: app_voyager.py
voyager_bp = Blueprint('voyager_bp', __name__)

@voyager_bp.route('/api/similarity/find', methods=['POST'])
def find_similar():
    ...
```

### 2. Task Queue Pattern (RQ)
Long-running operations use Redis Queue (RQ) for background processing:
- Two priority queues: `high` (user-facing) and `default` (batch)
- Parent-child task hierarchy tracked in PostgreSQL
- Status polling from frontend

```python
# Enqueue pattern
job = rq_queue_high.enqueue(
    'tasks.clustering.run_clustering_task',
    kwargs={...},
    job_id=task_id,
    on_failure=failure_handler
)
```

### 3. Media Server Abstraction (Dispatcher Pattern)
Single entry point (`tasks/mediaserver.py`) dispatches to server-specific implementations:

```python
# mediaserver.py
def get_recent_albums():
    if MEDIASERVER_TYPE == 'jellyfin':
        return mediaserver_jellyfin.get_recent_albums()
    elif MEDIASERVER_TYPE == 'navidrome':
        return mediaserver_navidrome.get_recent_albums()
    ...
```

### 4. Index Reload via Pub/Sub
Workers notify Flask app of index changes via Redis pub/sub:

```python
# Worker side
redis_conn.publish('index-updates', 'reload')

# Flask side (background thread)
pubsub.subscribe('index-updates')
for message in pubsub.listen():
    if message['data'] == b'reload':
        load_voyager_index_for_querying(force_reload=True)
```

### 5. GPU Fallback Pattern
GPU-accelerated code gracefully falls back to CPU:

```python
class GPUKMeans:
    def fit_predict(self, X):
        if check_gpu_available():
            try:
                # GPU implementation
                from cuml.cluster import KMeans as cuKMeans
                ...
            except Exception:
                pass  # Fall through to CPU

        # CPU fallback
        from sklearn.cluster import KMeans
        ...
```

## Database Patterns

### 1. Request-Scoped Connections (Flask)
```python
def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL)
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
```

### 2. Worker Connections (RQ Jobs)
Workers create their own connections inside task functions:
```python
def analyze_task():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        # ... task logic
    finally:
        conn.close()
```

### 3. Embedding Storage
Embeddings stored as PostgreSQL `bytea`:
```python
# Store
embedding_bytes = embedding_array.astype(np.float32).tobytes()
cur.execute("INSERT INTO embedding (embedding) VALUES (%s)",
            (psycopg2.Binary(embedding_bytes),))

# Retrieve
embedding = np.frombuffer(row['embedding'], dtype=np.float32)
```

### 4. Upsert Pattern
```python
INSERT INTO voyager_index_data (index_name, index_data, ...)
VALUES (%s, %s, ...)
ON CONFLICT (index_name) DO UPDATE SET
    index_data = EXCLUDED.index_data,
    ...
```

## Code Conventions

### 1. Logging
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Processing album %s", album_id)
logger.warning("Fallback to CPU: %s", error)
logger.error("Critical failure: %s", e, exc_info=True)
```

### 2. Configuration Access
All configuration via `config.py`:
```python
from config import EMBEDDING_DIMENSION, VOYAGER_METRIC, ...
```

### 3. Task Status Management
```python
from app_helper import save_task_status, TASK_STATUS_PROGRESS

save_task_status(
    task_id,
    "main_analysis",
    TASK_STATUS_PROGRESS,
    progress=45,
    details={"message": "Processing album 10/22", "log": [...]}
)
```

### 4. Error Handling in Tasks
```python
def task_failure_handler(job, connection, type, value, tb):
    from app import app
    from app_helper import save_task_status, TASK_STATUS_FAILURE

    with app.app_context():
        save_task_status(
            job.get_id(),
            "task_type",
            TASK_STATUS_FAILURE,
            progress=100,
            details={"error": str(value), "traceback": ...}
        )
```

### 5. Blueprint Registration
```python
# In app.py
from app_voyager import voyager_bp
app.register_blueprint(voyager_bp)
```

### 6. API Response Format
```python
# Success
return jsonify({"results": [...], "count": 10}), 200

# Accepted (async task)
return jsonify({"task_id": job.id, "task_type": "..."}), 202

# Error
return jsonify({"error": "Description"}), 400
```

## Naming Conventions

### Files
- Blueprints: `app_<feature>.py`
- Tasks: `tasks/<module>.py`
- Media servers: `tasks/mediaserver_<type>.py`
- Templates: `templates/<feature>.html`

### Functions
- Route handlers: `<verb>_<noun>_endpoint()` or `<action>_<noun>()`
- Task functions: `<action>_task()` or `run_<action>_task()`
- Helpers: `get_<noun>()`, `save_<noun>()`, `build_<noun>()`
- Validators: `is_<condition>()`, `check_<condition>()`

### Variables
- Database connections: `conn`, `db_conn`
- Cursors: `cur`
- Task IDs: `task_id`, `job_id`
- Configuration overrides: `<name>_param`

### Constants
- All uppercase with underscores: `MAX_SONGS_PER_ARTIST`
- Task statuses: `TASK_STATUS_<STATE>`

## Testing Conventions

### Test Structure
```
tests/
├── unit/
│   └── test_<module>.py
└── integration/
    └── test_<feature>.py
```

### Test Naming
```python
def test_<function>_<scenario>_<expected_result>():
    ...

# Example
def test_find_neighbors_empty_index_returns_empty_list():
    ...
```

## Error Handling Patterns

### 1. Graceful Degradation
```python
try:
    # Preferred method
    import voyager
    VOYAGER_AVAILABLE = True
except ImportError:
    logger.warning("Voyager not available")
    VOYAGER_AVAILABLE = False
```

### 2. Retry Pattern
```python
max_retries = 3
for attempt in range(max_retries):
    try:
        result = api_call()
        break
    except RateLimitError:
        time.sleep(base_delay * (2 ** attempt))
```

### 3. Context Manager for Resources
```python
with db_conn.cursor(cursor_factory=DictCursor) as cur:
    cur.execute(...)
    result = cur.fetchall()
# Cursor auto-closed
```

## Performance Patterns

### 1. LRU Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def _get_cached_vector(item_id: str) -> np.ndarray | None:
    ...
```

### 2. Batch Processing
```python
BATCH_SIZE = 100
for i in range(0, len(items), BATCH_SIZE):
    batch = items[i:i + BATCH_SIZE]
    process_batch(batch)
```

### 3. Thread Pooling
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(process, item): item for item in items}
    for future in as_completed(futures):
        result = future.result()
```

### 4. Pre-computed Indexes
- Voyager HNSW index for similarity search
- GMM index for artist similarity
- UMAP/PCA projections for visualization

All loaded at startup and stored in memory for fast queries.
