# AudioMuse-AI Project Structure

## Overview

AudioMuse-AI is a self-hosted music analysis and intelligent playlist generation system that uses machine learning to analyze audio files and create playlists based on sonic similarity.

## Directory Tree

```
AudioMuse-AI/
├── app.py                      # Main Flask application entry point
├── app_helper.py               # Database connections, task management utilities
├── ai.py                       # AI provider integrations (Gemini, Mistral, OpenAI, Ollama)
├── config.py                   # Configuration and environment variables
├── rq_worker.py                # Default priority RQ worker
├── rq_worker_high_priority.py  # High priority RQ worker
├── requirements.txt            # Python dependencies
│
├── app_*.py                    # Flask Blueprints (modular feature endpoints)
│   ├── app_analysis.py         # Audio analysis endpoints
│   ├── app_clustering.py       # Clustering and playlist generation
│   ├── app_voyager.py          # Similarity search (Voyager HNSW)
│   ├── app_sonic_fingerprint.py # User listening history analysis
│   ├── app_path.py             # Musical path generation between tracks
│   ├── app_alchemy.py          # Song blending (add/subtract characteristics)
│   ├── app_map.py              # 2D visualization of music library
│   ├── app_artist_similarity.py # Artist-based recommendations
│   ├── app_extend_playlist.py  # Playlist extension with filters
│   ├── app_collection.py       # Collection and queue management
│   ├── app_chat.py             # AI chat interface
│   ├── app_cron.py             # Scheduled task management
│   ├── app_external.py         # External API integrations
│   ├── app_waveform.py         # Waveform visualization
│   └── app_playlist_sync.py    # Multi-server playlist synchronization
│
├── tasks/                      # Background task modules
│   ├── analysis.py             # Main audio analysis workflow
│   ├── clustering.py           # CPU clustering algorithms
│   ├── clustering_gpu.py       # GPU-accelerated clustering (RAPIDS cuML)
│   ├── mediaserver.py          # Media server abstraction layer (dispatcher)
│   ├── mediaserver_jellyfin.py # Jellyfin integration
│   ├── mediaserver_navidrome.py # Navidrome integration
│   ├── mediaserver_emby.py     # Emby integration
│   ├── mediaserver_lyrion.py   # Lyrion/LMS integration
│   ├── mediaserver_plex.py     # Plex integration
│   ├── voyager_manager.py      # Voyager HNSW index management
│   ├── artist_gmm_manager.py   # Artist GMM index management
│   ├── path_manager.py         # Musical path generation
│   ├── song_alchemy.py         # Song vector blending
│   ├── collection_manager.py   # Collection operations
│   └── playlist_sync.py        # Multi-server sync logic
│
├── templates/                  # Jinja2 HTML templates
│   ├── index.html              # Main dashboard
│   ├── similarity.html         # Similarity search UI
│   ├── map.html                # 2D visualization
│   ├── chat.html               # AI chat interface
│   ├── extend_playlist.html    # Playlist builder UI
│   ├── cron.html               # Scheduled tasks UI
│   └── [other templates]       # Feature-specific templates
│
├── static/                     # Frontend assets
│   ├── script.js               # Main JavaScript
│   └── style.css               # Styles
│
├── models/                     # ONNX ML models (mounted or downloaded)
│   └── *.onnx                  # MusicNN and other models
│
├── deployment/                 # Docker deployment configurations
│   ├── docker-compose.yaml     # Main deployment
│   ├── docker-compose-nvidia.yaml # GPU-enabled deployment
│   ├── docker-compose-worker-nvidia.yaml # Remote GPU worker
│   ├── docker-compose.dev.yaml # Development setup
│   ├── docker-compose-jellyfin.yaml # Jellyfin variant
│   ├── docker-compose-navidrome.yaml # Navidrome variant
│   ├── docker-compose-emby.yaml # Emby variant
│   ├── docker-compose-lyrion.yaml # Lyrion variant
│   ├── docker-compose-plex.yaml # Plex variant
│   ├── .env.example            # Environment variable template
│   └── Dockerfile              # Container image definition
│
├── docs/                       # Documentation
│   ├── architecture/           # Architecture documentation
│   ├── features/               # Feature documentation
│   ├── environments/           # Environment documentation
│   ├── quality/                # Quality/testing documentation
│   ├── security/               # Security documentation
│   └── improvements/           # Improvement backlog
│
└── tests/                      # Test suite
    ├── unit/                   # Unit tests
    └── integration/            # Integration tests
```

## Core Components

### 1. Flask Web Application (`app.py`)

The main entry point that:
- Initializes Flask app with Swagger/Flasgger
- Registers all blueprints from `app_*.py` files
- Starts background threads:
  - Redis pub/sub listener for index reloading
  - Cron manager for scheduled tasks
- Configures ProxyFix middleware (optional)
- Injects version info into all templates

### 2. Background Workers

| Worker | Queue | Purpose |
|--------|-------|---------|
| `rq_worker.py` | `default` | Long-running batch tasks (analysis, clustering) |
| `rq_worker_high_priority.py` | `high` | User-initiated tasks (instant playlists, similarity) |

Workers use Redis Queue (RQ) and process jobs from PostgreSQL-tracked task hierarchy.

### 3. Blueprint Organization

Each `app_*.py` file is a Flask Blueprint encapsulating a specific feature:

| Blueprint | Route Prefix | Purpose |
|-----------|--------------|---------|
| `app_analysis` | `/api/analysis` | Audio analysis operations |
| `app_clustering` | `/api/clustering` | Playlist generation via clustering |
| `app_voyager` | `/api/similarity` | Song similarity search |
| `app_artist_similarity` | `/api/artist` | Artist-based recommendations |
| `app_path` | `/api/path` | Musical journeys between songs |
| `app_alchemy` | `/api/alchemy` | Song blending operations |
| `app_map` | `/api/map` | 2D visualization data |
| `app_chat` | `/api/chat` | AI conversation interface |
| `app_cron` | `/api/cron` | Scheduled task management |
| `app_collection` | `/api/collection` | Collection/queue management |
| `app_extend_playlist` | `/api/playlist` | Playlist builder |
| `app_waveform` | `/api/waveform` | Waveform data |

### 4. Task Modules (`tasks/`)

Background task logic separated from HTTP layer:

| Module | Responsibility |
|--------|----------------|
| `analysis.py` | Full audio analysis pipeline (feature extraction, ONNX inference) |
| `clustering.py` | Evolutionary Monte Carlo clustering search |
| `clustering_gpu.py` | GPU-accelerated clustering with RAPIDS cuML |
| `voyager_manager.py` | Voyager HNSW index build/query operations |
| `artist_gmm_manager.py` | Artist GMM similarity index |
| `path_manager.py` | Pathfinding between tracks |
| `song_alchemy.py` | Vector arithmetic for song blending |
| `mediaserver.py` | Dispatcher to media server implementations |
| `mediaserver_*.py` | Media server-specific implementations |

### 5. Database Schema (PostgreSQL)

| Table | Purpose |
|-------|---------|
| `score` | Track metadata (title, author, mood, features) |
| `embedding` | 200-dimensional audio embeddings (bytea) |
| `playlist` | Generated playlists and associations |
| `task_status` | Task tracking with parent-child hierarchy |
| `voyager_index_data` | Serialized Voyager HNSW index |
| `artist_similarity_index` | GMM-based artist clustering index |
| `map_projection` | 2D UMAP/PCA projections |
| `cron_jobs` | Scheduled task definitions |

### 6. In-Memory Caches

Loaded at startup for fast querying:
- **Voyager Index**: HNSW graph for approximate nearest neighbor search
- **Artist GMM Index**: Gaussian Mixture Model for artist similarity
- **Map Projections**: Pre-computed 2D coordinates for visualization
