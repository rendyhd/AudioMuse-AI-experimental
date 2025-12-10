# Optimization Context: Analysis Pipeline

Summary of findings from v0.7.12-beta → current branch comparison for future optimization work.

---

## Current Architecture Overview

```
Phase 0: PrefetchBuffer (background threads) → RAM cache
Phase 1A: ProcessPoolExecutor (CPU) → FFmpeg decode + spectrograms
Phase 1B: GPU Batch Inference → embeddings (ONNX_BATCH_SIZE chunks)
Phase 2-3: Mood/Feature prediction on cached embeddings
Phase 4: Batch DB write
```

---

## Key Performance Insights

### 1. VRAM Usage is Controlled by Batch Size, Not Song Length

**Old behavior:** VRAM scaled with song length (long songs = OOM risk)
**New behavior:** VRAM capped at `ONNX_BATCH_SIZE` (default: 100 patches)

```python
# VRAM is constant regardless of song length:
for i in range(0, total_patches, ONNX_BATCH_SIZE):
    batch = patches[i:i+ONNX_BATCH_SIZE]  # Never exceeds batch size
    embeddings = session.run(batch)
```

**Tuning:** Users with spare VRAM can increase `ONNX_BATCH_SIZE` (256-512) for ~10-30% speedup. Diminishing returns beyond 512.

### 2. ONNXModelManager Eliminates Session Thrashing

**Old:** 8 ONNX sessions created/destroyed per track
**New:** 8 sessions cached globally in singleton manager

Benefits:
- No repeated CUDA context initialization
- No VRAM fragmentation from alloc/dealloc cycles
- Graph optimization applied once

### 3. Multiprocessing Serializes GPU Access (Critical for VRAM)

**With multiprocessing:** CPU work parallel, GPU access serialized → low VRAM
**Without multiprocessing (ThreadPool):** Threads hit GPU simultaneously → VRAM explosion

```
Threads hitting GPU | VRAM multiplier
--------------------|----------------
1                   | 1× baseline
4                   | ~3.5×
8                   | ~6×
```

**Root cause:** CUDA allocates separate workspace buffers for each concurrent `session.run()` call.

---

## Multiprocessing Stability Issues (Why It Crashes)

### Root Causes Identified

| Issue | Severity | Impact |
|-------|----------|--------|
| Pickle serialization of 50MB+ file_bytes | Critical | 4GB+ memory overhead |
| Parallel numba JIT in 12 child processes | Critical | 3-6GB memory spike |
| fork() Copy-on-Write memory explosion | High | Hidden memory usage |
| subprocess.Popen in forked children | Medium | FD inheritance issues |

### Memory Calculation (40-track album, 12 workers)

```
Main process base:           ~1.5GB
Prefetch buffer (24×50MB):   ~1.2GB
12 child processes (400MB):  ~4.8GB
Pickle buffers (40×50MB):    ~2.0GB
JIT compilation overhead:    ~2.0GB
Audio arrays:                ~1.0GB
─────────────────────────────────────
Peak total:                  ~12.5GB
```

---

## Recommended Fixes for Multiprocessing

### Quick Fixes
1. Reduce `MULTIPROCESSING_WORKERS` from 12 to 4
2. Use `spawn` instead of `fork` start method

### Architectural Fixes (Eliminate Pickle Overhead)

**Option A: Shared Memory**
```python
from multiprocessing import shared_memory
shm = shared_memory.SharedMemory(create=True, size=len(file_bytes))
shm.buf[:] = file_bytes
# Pass shm.name (string) instead of file_bytes
```

**Option B: RAM-backed temp files (recommended)**
```python
temp_path = f"/dev/shm/track_{track_id}.flac"  # tmpfs, no disk I/O
with open(temp_path, 'wb') as f:
    f.write(file_bytes)
# Pass temp_path, child reads file (no pickle)
```

**Option C: Worker JIT warm-up**
```python
def initializer():
    dummy = np.random.randn(16000).astype(np.float32)
    _ = librosa.beat.tempo(y=dummy, sr=16000)
    _ = librosa.feature.chroma_stft(y=dummy, sr=16000)

ProcessPoolExecutor(max_workers=4, initializer=initializer)
```

---

## Optimal Architecture Target

```
[Main Process]
      │
      ▼
[ThreadPool: Prefetch] ──→ /dev/shm temp files (no pickle)
      │
      ▼
[ProcessPool: CPU work] ──→ reads temp files, returns small results
      │
      ▼
[Main Process: GPU] ──→ batched ONNX inference (serialized)
      │
      ▼
[Batch DB write + cleanup]
```

---

## Configuration Reference

### Performance Tuning
```env
# Audio decoding
USE_FFMPEG_DECODER=true          # 3.3× faster than librosa.load

# CPU parallelism
USE_MULTIPROCESSING=true         # True parallel CPU work
MULTIPROCESSING_WORKERS=4        # Start conservative (not 12)

# GPU batching
ONNX_BATCH_SIZE=256              # Increase if VRAM available
ENABLE_MODEL_PRELOAD=true        # Cache ONNX sessions

# I/O optimization
ENABLE_PREFETCH_BUFFER=true      # Overlap I/O with compute
PREFETCH_BUFFER_SIZE=10
ENABLE_DIRECT_FILE_ACCESS=true   # Bypass HTTP if volumes mapped
```

### Stability vs Performance Trade-off
```env
# Maximum stability (slower)
USE_MULTIPROCESSING=false
ONNX_BATCH_SIZE=100

# Balanced
USE_MULTIPROCESSING=true
MULTIPROCESSING_WORKERS=4
ONNX_BATCH_SIZE=256

# Maximum performance (requires tuning)
USE_MULTIPROCESSING=true
MULTIPROCESSING_WORKERS=8
ONNX_BATCH_SIZE=512
ENABLE_DIRECT_FILE_ACCESS=true
```

---

## Key Metrics to Monitor

```bash
# GPU utilization (aim for 80%+)
nvidia-smi -l 1

# Memory pressure
watch -n 1 free -h

# Per-process memory
ps aux --sort=-%mem | head -20
```

---

*Last updated: December 2, 2025*
