# AudioMuse-AI Performance Analysis

## Overview

AudioMuse-AI processes large music libraries (10,000+ tracks) with ML inference and clustering. Performance optimizations are critical for reasonable processing times.

## Bottleneck Analysis

### 1. Audio Analysis Pipeline

**Critical Path**:
```
Album Fetch → Track Download → Audio Load → Feature Extraction → ONNX Inference → DB Storage
```

| Stage | Time per Track | Bottleneck |
|-------|---------------|------------|
| Track Download (HTTP) | 2-10s | Network I/O |
| Track Download (Direct File) | 0.01-0.1s | Disk I/O |
| Audio Load (librosa) | 5-15s | CPU (single-threaded) |
| Audio Load (FFmpeg) | 1-3s | CPU (subprocess) |
| Feature Extraction | 2-5s | CPU (GIL-bound) |
| ONNX Inference (CPU) | 0.5-2s | CPU |
| ONNX Inference (GPU) | 0.01-0.1s | GPU transfer |
| DB Storage | 0.01-0.05s | Network I/O |

**Optimizations Implemented**:
- FFmpeg decoder (3.3x faster than librosa)
- Direct file access (10-100x faster than HTTP)
- GPU batched inference (10-50x faster per track)
- Multiprocessing for feature extraction (bypasses GIL)
- Parallel track downloads
- Prefetch buffer for I/O overlap

**Configuration**:
```bash
USE_FFMPEG_DECODER=true           # 3.3x faster decoding
ENABLE_DIRECT_FILE_ACCESS=true    # Bypass HTTP downloads
ENABLE_PREFETCH_BUFFER=true       # Overlap I/O with GPU
USE_MULTIPROCESSING=true          # True parallel CPU work
MULTIPROCESSING_WORKERS=6         # 6-8 for 16GB VRAM
ONNX_BATCH_SIZE=256               # GPU batch size
```

**Benchmark Results** (RTX 4070 Ti, 16GB VRAM):
| Configuration | Time for 1000 Tracks |
|---------------|---------------------|
| Baseline (HTTP + librosa + CPU) | 30+ hours |
| FFmpeg + Direct File | 8-10 hours |
| + GPU Inference | 4-5 hours |
| + Multiprocessing | 2-3 hours |

### 2. Clustering Pipeline

**Critical Path**:
```
Fetch Data → PCA → Clustering (5000 iterations) → Scoring → AI Naming → Playlist Creation
```

| Stage | Time | Bottleneck |
|-------|------|------------|
| Data Fetch | 1-5s | Database I/O |
| PCA (CPU) | 2-10s | CPU |
| PCA (GPU) | 0.1-0.5s | GPU |
| Single Clustering Run | 0.1-2s | CPU |
| 5000 Iterations (CPU) | 8-30 min | CPU |
| 5000 Iterations (GPU) | 1-5 min | GPU |
| AI Naming (per playlist) | 2-10s | API latency |
| Playlist Creation | 0.5-2s | Media server API |

**Optimizations Implemented**:
- Batched RQ jobs (parallelizes iterations)
- GPU clustering via RAPIDS cuML
- Elite-based evolutionary search (faster convergence)
- Configurable iteration count

**Configuration**:
```bash
USE_GPU_CLUSTERING=true           # RAPIDS cuML
CLUSTERING_RUNS=5000              # Total iterations
ITERATIONS_PER_BATCH_JOB=20       # Per-job iterations
MAX_CONCURRENT_BATCH_JOBS=10      # Parallel jobs
```

### 3. Similarity Search

**Critical Path**:
```
Query Vector → HNSW Search → Distance Filtering → Name Deduplication → Results
```

| Stage | Time | Bottleneck |
|-------|------|------------|
| Vector Lookup | 0.001s | Memory |
| HNSW Query (1000 results) | 0.01-0.1s | CPU |
| Distance Filtering | 0.01-0.1s | CPU |
| DB Fetch (metadata) | 0.1-0.5s | Database |
| Deduplication | 0.01-0.1s | CPU |

**Optimizations Implemented**:
- LRU cache for vector lookups (1000 entries)
- Batch DB queries
- Thread pool for parallel operations
- Pre-computed artist caps

**Configuration**:
```bash
VOYAGER_EF_CONSTRUCTION=512       # Index quality vs build time
VOYAGER_M=48                      # Memory vs accuracy
VOYAGER_QUERY_EF=1024             # Query accuracy
```

### 4. Index Rebuilds

**Critical Path**:
```
Fetch Embeddings → Build HNSW → Serialize → Store in DB → Publish Reload
```

| Stage | Time (10K tracks) | Bottleneck |
|-------|-------------------|------------|
| Fetch Embeddings | 2-5s | Database |
| Build HNSW Index | 10-60s | CPU |
| Serialize | 1-5s | CPU |
| Store in DB | 1-5s | Database |

**Optimizations Implemented**:
- Async index rebuilds (non-blocking)
- Batched rebuilds (every N albums)
- Redis pub/sub for reload notification

**Configuration**:
```bash
ENABLE_ASYNC_INDEX_REBUILDS=true  # Non-blocking
REBUILD_INDEX_BATCH_SIZE=200      # Albums before rebuild
```

## Memory Usage

### Flask App
- **Base**: ~100MB
- **Voyager Index (10K tracks)**: ~50-100MB
- **GMM Index**: ~10-20MB
- **Map Projections**: ~20-50MB

### RQ Workers
- **Base**: ~100MB
- **During Analysis**: 500MB-2GB (audio buffers, ONNX)
- **During Clustering**: 200MB-1GB

### GPU Memory (ONNX Inference)
| ONNX_BATCH_SIZE | VRAM Usage |
|-----------------|------------|
| 128 | ~6-8GB |
| 256 | ~10-12GB |
| 384 | ~15-16GB |
| 512 | ~20-22GB |

## Database Performance

### Index Recommendations
```sql
-- Already created by init_db()
CREATE INDEX IF NOT EXISTS idx_score_item_id ON score(item_id);
CREATE INDEX IF NOT EXISTS idx_embedding_item_id ON embedding(item_id);
CREATE INDEX IF NOT EXISTS idx_task_status_type ON task_status(task_type);
```

### Query Optimization
- Batch fetches use `WHERE item_id = ANY(%s)` instead of multiple queries
- DictCursor for efficient row access
- Connection pooling via Flask's `g` object

## Scaling Considerations

### Horizontal Scaling
- **Workers**: Add more RQ workers for parallel task execution
- **Remote Workers**: `docker-compose-worker-nvidia.yaml` for distributed GPU processing

### Vertical Scaling
- **More CPU cores**: Increase `MULTIPROCESSING_WORKERS`
- **More GPU VRAM**: Increase `ONNX_BATCH_SIZE`
- **More RAM**: Increase `PREFETCH_BUFFER_SIZE`

### Library Size Limits
| Library Size | Estimated Analysis Time | Recommendations |
|-------------|------------------------|-----------------|
| 1,000 tracks | 2-4 hours | Default config |
| 10,000 tracks | 15-30 hours | Enable GPU, direct file access |
| 50,000 tracks | 3-7 days | Remote GPU workers, distributed |
| 100,000+ tracks | 1-2 weeks | Multiple GPU workers |

## Monitoring Recommendations

### Key Metrics
1. **Task queue depth**: RQ queue size
2. **Task duration**: Time per album analysis
3. **GPU utilization**: `nvidia-smi` monitoring
4. **Memory usage**: Container memory limits
5. **Database connections**: PostgreSQL connection count

### Alerting Thresholds
- Queue depth > 1000 jobs
- Task duration > 10 minutes per album
- Memory usage > 90% of limit
- GPU utilization < 10% during inference
