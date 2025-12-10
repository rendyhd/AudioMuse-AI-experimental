# AudioMuse-AI Technology Stack

## Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language |
| Flask | 3.x | Web framework |
| Flasgger | 0.9.x | Swagger/OpenAPI documentation |
| psycopg2 | 2.9.x | PostgreSQL driver |
| Redis | 7.x | Cache and message broker |
| RQ (Redis Queue) | 1.x | Background job queue |

## Database

| Technology | Version | Purpose |
|------------|---------|---------|
| PostgreSQL | 15+ | Primary database |
| Redis | 7.x | Job queue, pub/sub messaging |

## Machine Learning & Audio Processing

| Technology | Version | Purpose |
|------------|---------|---------|
| ONNX Runtime | 1.16+ | Model inference (CUDA/CPU) |
| librosa | 0.10.x | Audio feature extraction |
| numpy | 1.24+ | Numerical computing |
| scikit-learn | 1.3+ | Clustering algorithms (CPU) |
| RAPIDS cuML | 23.x+ | GPU-accelerated clustering (optional) |
| Voyager | 2.x | Spotify's HNSW library for similarity search |
| UMAP | 0.5.x | Dimensionality reduction for visualization |
| soundfile | 0.12.x | Audio file I/O |
| FFmpeg | 6.x | Audio decoding (subprocess) |

## ONNX Models

| Model | Dimensions | Purpose |
|-------|------------|---------|
| MusicNN (MTT) | 200-dim | Audio embeddings |
| mood_* models | Various | Mood/genre predictions |

## AI Providers (Playlist Naming & Chat)

| Provider | Models Supported | Purpose |
|----------|------------------|---------|
| Google Gemini | gemini-2.5-pro, etc. | Playlist naming, chat |
| Mistral | ministral-3b-latest, etc. | Playlist naming, chat |
| OpenAI/OpenRouter | GPT-4, etc. | Playlist naming, chat |
| Ollama | DeepSeek, Llama, etc. | Self-hosted LLM |

## Media Server Integrations

| Server | API Type | Implemented In |
|--------|----------|----------------|
| Jellyfin | REST API | `mediaserver_jellyfin.py` |
| Navidrome | Subsonic API | `mediaserver_navidrome.py` |
| Emby | REST API | `mediaserver_emby.py` |
| Lyrion/LMS | JSON-RPC | `mediaserver_lyrion.py` |
| Plex | REST API | `mediaserver_plex.py` |

## Frontend

| Technology | Purpose |
|------------|---------|
| HTML5/CSS3 | Structure and styling |
| Vanilla JavaScript | Interactivity |
| Jinja2 | Server-side templating |
| Chart.js | Visualizations |
| D3.js | Map visualization |

## Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Multi-container orchestration |
| NVIDIA Container Toolkit | GPU passthrough for CUDA |

## Key Libraries by Domain

### Audio Analysis Pipeline
```
librosa          → Audio loading, feature extraction
soundfile        → Audio file I/O
numpy            → Numerical operations
onnxruntime      → Neural network inference
onnxruntime-gpu  → CUDA-accelerated inference
```

### Similarity Search
```
voyager          → Spotify's HNSW implementation
numpy            → Vector operations
psycopg2         → Index persistence (bytea)
```

### Clustering
```
scikit-learn     → KMeans, DBSCAN, GMM, Spectral (CPU)
cuml             → GPU-accelerated algorithms (optional)
numpy            → Data manipulation
```

### Web Framework
```
flask            → HTTP routing, blueprints
flasgger         → Swagger documentation
werkzeug         → WSGI utilities
```

### Background Jobs
```
rq               → Redis-based job queue
redis            → Connection to Redis
psycopg2         → Task status persistence
```

### AI Integration
```
google-generativeai  → Gemini API
mistralai            → Mistral API
requests             → OpenAI/OpenRouter/Ollama HTTP calls
ftfy                 → Text cleaning for AI responses
```

## Configuration Sources

1. **Environment Variables** (primary)
   - `deployment/.env` file
   - Docker Compose environment

2. **config.py** (defaults)
   - Reads from environment
   - Provides typed defaults

## Version Compatibility

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| PostgreSQL | 13 | 15+ |
| Redis | 6 | 7+ |
| Docker | 20.10 | 24+ |
| CUDA (optional) | 11.8 | 12.x |
| NVIDIA Driver (optional) | 525 | 535+ |
