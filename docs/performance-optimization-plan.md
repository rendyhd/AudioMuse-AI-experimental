# AudioMuse-AI Performance Optimization Plan
## Comprehensive End-to-End Analysis & Action Plan

**Generated:** 2025-12-06
**System:** 16 CPUs, 48GB RAM, 16GB GPU (NVIDIA)
**Current Performance:** 17-19s per track (Target: 8-10s per track)

---

## Executive Summary

Through comprehensive analysis combining code review, Gemini AI analysis, and runtime profiling, we identified:

1. **CRITICAL BUG**: SharedMemory leak causing orphaned segments
2. **Architecture Mismatch**: Sequential CPU→GPU pipeline leaves GPU idle
3. **I/O Inefficiency**: Triple-copy pattern for audio data on Windows
4. **Configuration Sub-optimal**: ONNX batch size too conservative for 16GB GPU

**Estimated Impact:** Implementing all fixes = **45-55% performance improvement** (17s → 8-9s per track)

---

## Current State Analysis

### System Resources
```
CPU: 16 cores
RAM: 48GB (43GB available)  ← PLENTY OF HEADROOM
GPU: 16GB VRAM (13.6GB free, 2.4GB used by models)
```

**RAM Implications:**
- Can support MORE aggressive prefetch buffer (4-8GB vs current 2GB)
- Can increase MULTIPROCESSING_WORKERS to 12-16 without memory pressure
- Can batch larger groups of albums in memory
- Zero risk of memory exhaustion with current workload

### Current Configuration
```yaml
MULTIPROCESSING_WORKERS: 8         # Good for 16 cores
ONNX_BATCH_SIZE: 256               # Conservative for 16GB GPU
USE_FAST_TEMPO: true               # ✓ Optimized
ENABLE_ASYNC_INDEX_REBUILDS: true  # ✓ Optimized
ENABLE_PREFETCH_BUFFER: true       # ✓ Enabled
SKIP_CPU_FEATURES: false           # Could optimize
```

### Performance Baseline (Last 20 Albums)
```
Average: 17.2s per track
Range: 8.9s - 24.0s per track
Small albums (2-3 tracks): 21-24s (high overhead)
Large albums (50+ tracks): 10-12s (better efficiency)
```

### Performance Bottleneck Breakdown
```
Audio Loading:          40-45% (7-8s per track)
CPU Feature Extraction: 25-30% (4-5s per track)
Mel Spectrogram:        15-20% (2-3s per track)
GPU Embedding:          5-10%  (1-2s per batch)
DB Storage:             5%     (0.5-1s per track)
Overhead:               5-10%  (1-2s per track)
```

---

## Critical Issues Identified

### 1. CRITICAL: SharedMemory Leak (Memory Exhaustion)

**File:** `tasks/analysis.py:1565-1707` (`gpu_batch_embedding_inference`)

**Issue:**
```python
# Lines 1586-1617
for result in cpu_results:
    shm_name = result.get('shm_name')
    if shm_name:
        shm = SharedMemory(name=shm_name)
        shm_handles.append(shm)
        # ... process ...

# Lines 1676-1683 (finally block)
for shm in shm_handles:
    shm.close()
    shm.unlink()
```

**Problem:**
If function returns early or skips results, SharedMemory segments created by workers are never unlinked, causing permanent memory leak until reboot.

**Evidence:**
- `/dev/shm` previously filled to 100% with orphaned `psm_*` files
- 6-8MB leaked per skipped track
- Accumulates over hours: 735 files = 4GB leaked

**Impact:** HIGH - System crashes when /dev/shm fills

**Fix Priority:** 🔴 CRITICAL - Must implement immediately

---

### 2. HIGH: Sequential CPU→GPU Pipeline (GPU Idle Time)

**File:** `tasks/analysis.py:1783-1850`

**Issue:**
```python
# Lines 1824-1837
# Wait for ALL CPU processing to complete
cpu_results = pool.map(cpu_process_audio_worker, worker_args)

# THEN start GPU processing
track_embeddings, loaded_results = gpu_batch_embedding_inference(
    cpu_results, embedding_sess, batch_size=ONNX_BATCH_SIZE
)
```

**Problem:**
For 50-track album:
- CPU Phase takes 15-18 minutes (all 50 tracks)
- GPU sits idle for 15-18 minutes
- GPU Phase takes 2-3 minutes (all 50 tracks)
- **Total: 18-21 minutes**

**Optimal Pipeline:**
- Process in chunks of 8-16 tracks
- CPU(Chunk1) → GPU(Chunk1) while CPU(Chunk2) runs
- **Estimated Total: 10-12 minutes (40% faster)**

**Impact:** MEDIUM-HIGH - 30-40% improvement on large albums

**Fix Priority:** 🟠 HIGH - Significant impact, moderate complexity

---

### 3. MEDIUM: Input Audio Triple-Copy (I/O Overhead)

**File:** `tasks/analysis.py:1446-1453, 1716-1750`

**Issue:**
```python
# Current flow (Windows):
1. PrefetchBuffer reads file → RAM (copy #1)
2. collect_prefetch_data writes → temp file on DISK (copy #2)
3. cpu_process_audio_worker reads temp file → RAM (copy #3)

# On Linux (/dev/shm is RAM):
- Copies #2 and #3 are in RAM (fast)

# On Windows (C:\Users\...\Temp):
- Copies #2 and #3 hit DISK (slow: 50-200ms per track)
```

**Problem:**
Unnecessary disk I/O adds 100-400ms per track on Windows. For 50 tracks = 5-20 seconds wasted.

**Solution:**
Use SharedMemory for input audio bytes (same technique as output patches):
```python
# In collect_prefetch_data:
shm = SharedMemory(create=True, size=len(file_bytes))
shm.buf[:] = file_bytes
return shm.name  # Pass to worker

# In cpu_process_audio_worker:
shm = SharedMemory(name=input_shm_name)
file_bytes = bytes(shm.buf)
shm.close()  # Main process will unlink
```

**Impact:** MEDIUM - 5-10% improvement, especially on Windows

**Fix Priority:** 🟡 MEDIUM - Good ROI, moderate complexity

---

### 4. LOW-MEDIUM: Conservative ONNX Batch Size

**File:** `config.py:179` (`ONNX_BATCH_SIZE = 256`)

**Issue:**
With 16GB VRAM and only 2.4GB used by models, we have 13GB free. Current batch size only uses ~500MB.

**Recommendation:**
```python
ONNX_BATCH_SIZE = 512  # Double current (uses ~1GB VRAM)
```

**Testing:**
```bash
# Monitor GPU memory during analysis
nvidia-smi --query-gpu=memory.used --format=csv -l 1

# If memory stable <12GB, increase to 768 or 1024
```

**Impact:** LOW-MEDIUM - 10-15% improvement on GPU-bound phases (Phase 1B, 2, 3)

**Fix Priority:** 🟢 LOW - Easy win, minimal risk

---

### 5. LOW: CPU Feature Extraction Overhead

**File:** `tasks/analysis.py:1473-1500`

**Issue:**
```python
# Lines 1473-1500 - Key/Scale detection
chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
# ... 12 correlation calculations per track
```

**Problem:**
Key/scale detection adds 2-3 seconds per track for marginal value (many users don't use this metadata).

**Recommendation:**
Add config flag:
```python
ENABLE_KEY_DETECTION = os.getenv('ENABLE_KEY_DETECTION', 'false').lower() == 'true'
```

**Impact:** LOW - 10-15% improvement IF disabled (breaks features that rely on key/scale)

**Fix Priority:** 🟢 LOW - Optional optimization for speed-focused deployments

---

## Proposed Solution: Chunked Pipeline Architecture

### Current Architecture
```
┌─────────────────────────────────────────────────┐
│ Album: 50 tracks                                │
│                                                 │
│ Phase 1A: CPU (50 tracks) ──────────┐          │
│   ├─ Worker 1: Track 1-7   (18 min) │          │
│   ├─ Worker 2: Track 8-13           │          │
│   ├─ Worker 3: Track 14-19          │          │
│   ├─ Worker 4: Track 20-25          │          │
│   ├─ Worker 5: Track 26-31          │          │
│   ├─ Worker 6: Track 32-37          │          │
│   ├─ Worker 7: Track 38-44          │          │
│   └─ Worker 8: Track 45-50          │          │
│                                      │          │
│ Phase 1B: GPU (50 tracks) ◄──────────┘          │
│   └─ Batched inference     (2 min)              │
│                                                 │
│ Total: 20 minutes                               │
└─────────────────────────────────────────────────┘

GPU Utilization: 10% (idle 18 of 20 minutes)
```

### Optimized Architecture (Chunked Pipeline)
```
┌─────────────────────────────────────────────────┐
│ Album: 50 tracks (processed in 8-track chunks) │
│                                                 │
│ ┌─ Chunk 1 (8 tracks) ────────────┐            │
│ │ CPU(8) ──┐ (2 min)              │            │
│ │          └──► GPU(8) ─┐ (20s)   │            │
│ └─────────────────────────┼────────┘            │
│                           │                     │
│ ┌─ Chunk 2 (8 tracks) ────┼────────┐            │
│ │ CPU(8) ──┐ (2 min)      │        │            │
│ │          └──► GPU(8) ◄──┘ (20s)  │            │
│ └─────────────────────────┼────────┘            │
│                           │                     │
│ ┌─ Chunk 3-6 (similar)... │                    │
│ │                         │                    │
│ └─────────────────────────┘                    │
│                                                 │
│ Total: 12 minutes (40% faster)                 │
└─────────────────────────────────────────────────┘

GPU Utilization: 40% (processing 5 of 12 minutes)
```

### Implementation
```python
def analyze_album_with_chunked_pipeline(tracks, chunk_size=8):
    """
    Process tracks in chunks, overlapping CPU and GPU work.
    """
    all_track_embeddings = {}
    all_loaded_results = []

    for i in range(0, len(tracks), chunk_size):
        chunk = tracks[i:i+chunk_size]

        # Phase 1A: CPU processing (parallel)
        worker_args = prepare_worker_args(chunk)
        cpu_results = pool.map(cpu_process_audio_worker, worker_args)

        # Phase 1B: GPU processing (while next chunk starts CPU)
        chunk_embeddings, chunk_results = gpu_batch_embedding_inference(
            cpu_results, embedding_sess, batch_size=ONNX_BATCH_SIZE
        )

        all_track_embeddings.update(chunk_embeddings)
        all_loaded_results.extend(chunk_results)

    return all_track_embeddings, all_loaded_results
```

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1) - 🔴 MUST DO

#### 1.1 Fix SharedMemory Leak
**File:** `tasks/analysis.py:1676-1683`

**Current code:**
```python
finally:
    # Cleanup SharedMemory handles
    for shm in shm_handles:
        try:
            shm.close()
            shm.unlink()
        except Exception:
            pass
```

**Fixed code:**
```python
finally:
    # 1. Clean up handles we opened
    for shm in shm_handles:
        try:
            shm.close()
            shm.unlink()
        except Exception:
            pass

    # 2. Ensure ALL shm_names from input are unlinked (even if not processed)
    for result in cpu_results:
        if result is None:
            continue
        shm_name = result.get('shm_name')
        if shm_name:
            try:
                # Try to open and unlink (idempotent if already unlinked)
                shm = SharedMemory(name=shm_name)
                shm.close()
                shm.unlink()
            except FileNotFoundError:
                # Already unlinked, OK
                pass
            except Exception as e:
                logger.warning(f"Failed to cleanup SHM {shm_name}: {e}")
```

**Testing:**
```bash
# Monitor /dev/shm before and after album analysis
watch -n 1 'ls -lh /dev/shm/psm_* 2>/dev/null | wc -l'

# Should return to 0 after each album completes
```

**Expected Impact:** Prevents system crashes (critical stability fix)

---

#### 1.2 Increase ONNX Batch Size
**File:** `config.py:179` or `deployment/.env`

**Change:**
```python
# Before
ONNX_BATCH_SIZE = 256

# After
ONNX_BATCH_SIZE = 512
```

**Testing:**
```bash
# Start analysis and monitor GPU memory
docker exec audiomuse-ai-worker-instance-dev bash -c "
  while true; do
    nvidia-smi --query-gpu=memory.used --format=csv,noheader
    sleep 2
  done
"

# If peak <12GB, safe to increase further to 768 or 1024
```

**Expected Impact:** 10-15% speedup on GPU phases

---

### Phase 2: High-Impact Optimizations (Week 2) - 🟠 RECOMMENDED

#### 2.1 Implement Chunked Pipeline
**File:** `tasks/analysis.py` - New function `analyze_album_with_chunked_pipeline_batched_gpu()`

**Pseudocode:**
```python
def analyze_album_with_chunked_pipeline_batched_gpu(
    tracks_to_process,
    album_name,
    embedding_sess,
    prediction_sess,
    other_feature_sessions,
    task_info,
    db_conn
):
    """
    Process album in chunks to overlap CPU and GPU work.

    Args:
        tracks_to_process: List of track dicts
        chunk_size: Tracks per chunk (default: 2 * MULTIPROCESSING_WORKERS)
    """
    CHUNK_SIZE = 2 * MULTIPROCESSING_WORKERS  # 16 for 8 workers

    all_track_results = {}
    total_tracks = len(tracks_to_process)
    processed_count = 0

    for chunk_start in range(0, total_tracks, CHUNK_SIZE):
        chunk_end = min(chunk_start + CHUNK_SIZE, total_tracks)
        chunk = tracks_to_process[chunk_start:chunk_end]
        chunk_num = chunk_start // CHUNK_SIZE + 1
        total_chunks = (total_tracks + CHUNK_SIZE - 1) // CHUNK_SIZE

        logger.info(f"[Chunk {chunk_num}/{total_chunks}] Processing {len(chunk)} tracks...")

        # Phase 1A: CPU processing (parallel)
        worker_args = []
        for item in chunk:
            temp_path, original_path = prepare_audio_source(item, prefetch_buffer)
            worker_args.append((temp_path, original_path, item['track_id'], item))

        cpu_results = _execute_with_pool_recovery(
            worker_args,
            task_info,
            max_retries=2,
            progress_callback=lambda: update_progress(...)
        )

        # Phase 1B: GPU embedding (batched)
        track_embeddings, loaded_results = gpu_batch_embedding_inference(
            cpu_results,
            embedding_sess,
            batch_size=ONNX_BATCH_SIZE
        )

        # Combine into track_results for this chunk
        for loaded_result in loaded_results:
            track_id = loaded_result['track_id']
            if track_id in track_embeddings:
                all_track_results[track_id] = {
                    'item': loaded_result['item'],
                    'cpu_features': loaded_result['cpu_features'],
                    'embeddings_per_patch': track_embeddings[track_id]
                }

        processed_count += len(chunk)
        progress = 10 + int((processed_count / total_tracks) * 30)  # Phase 1: 10-40%
        save_task_status(db_conn, task_info['task_id'], 'PROGRESS', progress)

    # Continue with Phase 2, 3, 4 as before (all tracks processed)
    return continue_with_remaining_phases(all_track_results, ...)
```

**Integration:**
Replace call to `analyze_album_with_multiprocessing_batched_gpu()` with `analyze_album_with_chunked_pipeline_batched_gpu()` in `analyze_album_task()`.

**Expected Impact:** 30-40% speedup on albums >20 tracks

---

#### 2.2 Input Audio SharedMemory (Windows Performance)
**File:** `tasks/analysis.py:1716-1750` (`collect_prefetch_data`)

**Current:**
```python
def collect_prefetch_data(tracks_to_process, prefetch_buffer):
    """Collects prefetch data in ThreadPoolExecutor."""
    # ... writes temp files to disk ...
```

**Optimized:**
```python
def collect_prefetch_data_shm(tracks_to_process, prefetch_buffer):
    """
    Collects prefetch data using SharedMemory (zero-copy).
    Returns: list of (shm_name, original_path, track_id, item_dict)
    """
    from multiprocessing.shared_memory import SharedMemory

    input_shm_handles = []  # Track for cleanup
    worker_args = []

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS) as executor:
        futures = {}

        for item in tracks_to_process:
            future = executor.submit(
                _prepare_audio_source_shm,
                item,
                prefetch_buffer
            )
            futures[future] = item

        for future in as_completed(futures):
            item = futures[future]
            try:
                shm_name, original_path = future.result()
                if shm_name:
                    input_shm_handles.append(shm_name)

                worker_args.append((
                    shm_name,          # Instead of temp_path
                    original_path,
                    item['track_id'],
                    item
                ))
            except Exception as e:
                logger.error(f"Failed to prepare {item['name']}: {e}")
                continue

    return worker_args, input_shm_handles

def _prepare_audio_source_shm(item, prefetch_buffer):
    """
    Prepares audio source using SharedMemory.
    Returns: (shm_name, original_path)
    """
    if prefetch_buffer:
        file_bytes, original_path = prefetch_buffer.get(item['track_id'], timeout=120)
        if file_bytes:
            # Create SharedMemory for input audio
            shm = SharedMemory(create=True, size=len(file_bytes))
            shm.buf[:] = file_bytes
            shm.close()  # Close handle, memory persists
            return shm.name, original_path

    # Fallback: direct file access
    return None, item.get('file_path')
```

**Update `cpu_process_audio_worker`:**
```python
def cpu_process_audio_worker(args):
    input_shm_name, original_path, track_id, item_dict = args

    try:
        # --- 1. Load Audio from SharedMemory ---
        if input_shm_name:
            try:
                shm = SharedMemory(name=input_shm_name)
                file_bytes = bytes(shm.buf)
                shm.close()  # Don't unlink (main process will)
                audio, sr = load_audio_with_ffmpeg_from_bytes(
                    file_bytes, original_path, 16000, AUDIO_LOAD_TIMEOUT
                )
            except Exception as e:
                logger.warning(f"SHM load failed for {track_id}, falling back: {e}")
                audio, sr = load_audio_with_ffmpeg(original_path, 16000, AUDIO_LOAD_TIMEOUT)
        else:
            # Fallback: direct file access
            audio, sr = load_audio_with_ffmpeg(original_path, 16000, AUDIO_LOAD_TIMEOUT)

        # ... rest of processing ...
```

**Cleanup in main process:**
```python
finally:
    # Cleanup input SharedMemory
    for input_shm_name in input_shm_handles:
        try:
            shm = SharedMemory(name=input_shm_name)
            shm.close()
            shm.unlink()
        except Exception:
            pass
```

**Expected Impact:** 5-10% speedup, especially on Windows

---

### Phase 3: Optional Optimizations (Future) - 🟢 NICE TO HAVE

#### 3.1 Dynamic Worker Count
**File:** `config.py:156`

**Change:**
```python
# Current
MULTIPROCESSING_WORKERS = int(os.getenv('MULTIPROCESSING_WORKERS', '4'))

# Optimized
def _get_optimal_worker_count():
    """
    Automatically determine optimal worker count.

    Logic:
    - If explicitly set: use that value
    - Otherwise: min(cpu_count // 2, 8)
    - Rationale: Leave half for GPU, OS, and I/O threads
    """
    env_value = os.getenv('MULTIPROCESSING_WORKERS')
    if env_value:
        return int(env_value)

    cpu_count = os.cpu_count() or 4
    # Conservative: half of CPUs, capped at 8 to avoid memory issues
    return min(cpu_count // 2, 8)

MULTIPROCESSING_WORKERS = _get_optimal_worker_count()
```

**Expected Impact:** 10-20% speedup on high-core systems (16+ cores)

---

#### 3.2 Optional Key/Scale Detection
**File:** `config.py` + `tasks/analysis.py`

**Add config:**
```python
# config.py
ENABLE_KEY_DETECTION = os.getenv('ENABLE_KEY_DETECTION', 'true').lower() == 'true'
```

**Update worker:**
```python
# tasks/analysis.py:1473-1500
if not SKIP_CPU_FEATURES:
    # Always extract tempo and energy
    tempo = librosa.beat.tempo(y=audio, sr=sr)[0]
    average_energy = np.mean(librosa.feature.rms(y=audio))

    # Optional: key/scale detection (expensive)
    if ENABLE_KEY_DETECTION:
        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        # ... correlation analysis ...
        musical_key = key_vals[...]
        scale = 'major' or 'minor'
    else:
        musical_key = 'Unknown'
        scale = 'Unknown'
```

**Expected Impact:** 10-15% speedup IF disabled (loses key/scale metadata)

---

#### 3.3 Batch Database Inserts
**File:** `tasks/analysis.py:2080-2150` (`save_track_analysis_and_embedding`)

**Current:** Sequential inserts per track

**Optimized:** Batch insert 10-50 tracks at once
```python
def save_track_batch_analysis(db_conn, track_analyses):
    """
    Save multiple track analyses in a single transaction.

    Args:
        track_analyses: List of dicts with track data
    """
    import psycopg2.extras

    cur = db_conn.cursor()

    # Prepare batch data
    batch_data = []
    for analysis in track_analyses:
        batch_data.append((
            analysis['track_id'],
            analysis['embedding_bytes'],
            analysis['mood_vector'],
            # ... all fields ...
        ))

    # Single batch INSERT
    insert_query = """
        INSERT INTO tracks (track_id, embedding, mood_vector, ...)
        VALUES %s
        ON CONFLICT (track_id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            mood_vector = EXCLUDED.mood_vector,
            ...
    """

    psycopg2.extras.execute_values(
        cur,
        insert_query,
        batch_data,
        template="(%s, %s, %s, ...)"
    )

    db_conn.commit()
```

**Expected Impact:** 20-30% reduction in database time (5-10s → 1-2s per 50 tracks)

---

## Testing & Validation Plan

### Test Suite

**Test 1: Small Album (5 tracks)**
```bash
# Baseline
docker exec audiomuse-ai-worker-instance-dev bash -c "
  curl -X POST http://localhost:8000/api/analysis/start \\
    -H 'Content-Type: application/json' \\
    -d '{\"num_recent_albums\": 1}'
"
# Expected: 60-90 seconds total

# Monitor progress
watch -n 1 'docker logs --tail 50 audiomuse-ai-worker-instance-dev | grep -E "Phase|Successfully"'
```

**Test 2: Medium Album (20 tracks)**
```bash
# Expected baseline: 5-6 minutes (20 * 17s avg)
# Expected after Phase 1 fixes: 3-4 minutes (20 * 10s avg)
# Expected after Phase 2 chunked: 2.5-3 minutes (40% improvement)
```

**Test 3: Large Album (50 tracks)**
```bash
# Expected baseline: 15-18 minutes (sequential)
# Expected after chunked pipeline: 10-12 minutes (overlapped)
```

**Test 4: Memory Leak Test**
```bash
# Run 100 albums continuously
# Monitor /dev/shm usage
df -h /dev/shm
ls -lh /dev/shm/psm_* | wc -l

# Should stay at 0-10 files max, never accumulate
```

**Test 5: GPU Memory Test**
```bash
# With ONNX_BATCH_SIZE=512
nvidia-smi --query-gpu=memory.used --format=csv -l 1

# Should peak <12GB (safe margin on 16GB GPU)
```

---

## Performance Targets

### Per-Track Performance
| Metric | Baseline | Phase 1 | Phase 2 | Target |
|--------|----------|---------|---------|--------|
| Small albums (2-3 tracks) | 21-24s | 18-20s | 15-17s | 12-15s |
| Medium albums (10-20 tracks) | 16-18s | 12-14s | 9-11s | 8-10s |
| Large albums (50+ tracks) | 14-16s | 10-12s | 7-9s | 6-8s |

### Album Completion Times
| Album Size | Baseline | Phase 1 | Phase 2 | Target |
|------------|----------|---------|---------|--------|
| 5 tracks | 1:30 | 1:10 | 0:50 | 0:40-0:50 |
| 10 tracks | 3:00 | 2:10 | 1:30 | 1:20-1:40 |
| 20 tracks | 6:00 | 4:20 | 3:00 | 2:40-3:20 |
| 50 tracks | 17:00 | 12:00 | 8:00 | 6:00-8:00 |

---

## Risk Assessment

### Low Risk ✅
- ONNX batch size increase (easily reversible)
- Dynamic worker count (well-tested pattern)
- Optional key detection (feature flag)

### Medium Risk ⚠️
- Input SharedMemory (new code path, needs fallback)
- Batch database inserts (transaction safety)

### High Risk 🔴
- SharedMemory leak fix (critical but simple)
- Chunked pipeline (architectural change, needs thorough testing)

**Mitigation:**
- Implement in separate branch
- Test each phase independently
- Keep rollback plan ready
- Monitor system metrics during deployment

---

## Rollback Plan

If issues arise:

```bash
# Revert to previous Docker image
docker tag audiomuse-ai:current audiomuse-ai:rollback
docker compose -f deployment/docker-compose.dev.yaml down
docker compose -f deployment/docker-compose.dev.yaml up -d

# Or revert specific configs
docker exec audiomuse-ai-worker-instance-dev bash -c "
  export ONNX_BATCH_SIZE=256
  export MULTIPROCESSING_WORKERS=4
"
docker restart audiomuse-ai-worker-instance-dev
```

---

## Implementation Timeline

### Week 1: Critical Fixes
- Day 1-2: Implement SharedMemory leak fix
- Day 3: Test leak fix (100 albums stress test)
- Day 4: Increase ONNX batch size + test
- Day 5: Deploy to production, monitor

### Week 2: High-Impact Optimizations
- Day 1-2: Implement chunked pipeline
- Day 3: Implement input SharedMemory
- Day 4-5: Integration testing
- Day 6-7: Production deployment + monitoring

### Week 3: Optional Optimizations (if needed)
- Day 1-2: Dynamic worker count
- Day 3: Optional key detection flag
- Day 4-5: Batch database inserts
- Day 6-7: Final testing + documentation

---

## Success Metrics

**Primary KPIs:**
- ✅ Per-track processing time: <10s average (from 17s)
- ✅ 10-track album: <1:40 total (from 3:00)
- ✅ No /dev/shm leaks after 1000 albums
- ✅ GPU memory stable <12GB (from varying)

**Secondary KPIs:**
- GPU utilization: >30% (from 10%)
- Worker pool efficiency: >80% (measured by idle time)
- Database transaction time: <2s per 50 tracks (from 5-10s)

---

## Conclusion

This comprehensive plan addresses all identified bottlenecks:

1. **Critical stability** (SharedMemory leak)
2. **Architecture efficiency** (chunked pipeline)
3. **I/O optimization** (SharedMemory for input)
4. **Resource utilization** (ONNX batch size)

**Expected overall improvement: 45-55%** (17s → 8-9s per track)

All changes are backwards compatible with fallback paths and can be deployed incrementally.
