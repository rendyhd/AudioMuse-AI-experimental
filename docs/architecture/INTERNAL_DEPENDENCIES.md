# AudioMuse-AI Internal Dependencies

## Module Dependency Map

This document maps the internal dependencies between modules to help understand the impact of changes.

## Core Modules

### `config.py`
**Exports**: All configuration variables and constants
**Imports**: `os` (stdlib)
**Imported By**: Nearly all modules (central configuration)
**Change Impact**: HIGH - Changes affect the entire application

### `app.py`
**Exports**: `app` (Flask instance)
**Imports**:
- `config.py` (configuration)
- `app_helper.py` (utilities)
- All `app_*.py` blueprints
**Imported By**: RQ workers (for app context)
**Change Impact**: HIGH - Main application entry point

### `app_helper.py`
**Exports**:
- `get_db()` - Database connection
- `rq_queue`, `rq_queue_high` - RQ queues
- `save_task_status()` - Task tracking
- `get_score_data_by_ids()` - Track data retrieval
- `init_db()` - Database initialization
- Task status constants (`TASK_STATUS_*`)
**Imports**:
- `config.py`
- `psycopg2`
- `redis`, `rq`
- `flask.g`
**Imported By**: All blueprints, all task modules
**Change Impact**: CRITICAL - Core infrastructure

### `ai.py`
**Exports**:
- `get_ai_playlist_name()` - Main AI naming function
- `call_ai_for_chat()` - Chat AI interface
- `clean_playlist_name()` - Name sanitization
- Provider-specific functions
**Imports**:
- `config.py`
- `requests` (OpenAI/Ollama)
- `google.generativeai` (Gemini)
- `mistralai` (Mistral)
**Imported By**: `tasks/clustering.py`, `app_chat.py`
**Change Impact**: MEDIUM - AI features only

## Blueprint Modules

### `app_analysis.py`
**Exports**: `analysis_bp` (Blueprint)
**Imports**:
- `app_helper.py` (queues, task status)
- `config.py`
**Enqueues**: `tasks.analysis.analyze_and_cluster_task`
**Change Impact**: MEDIUM - Analysis feature

### `app_clustering.py`
**Exports**: `clustering_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `config.py` (all clustering params)
**Enqueues**: `tasks.clustering.run_clustering_task`
**Change Impact**: MEDIUM - Clustering feature

### `app_voyager.py`
**Exports**: `voyager_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/voyager_manager.py`
**Change Impact**: HIGH - Core similarity feature

### `app_chat.py`
**Exports**: `chat_bp` (Blueprint)
**Imports**:
- `ai.py`
- `app_helper.py`
- `tasks/voyager_manager.py`
**Change Impact**: MEDIUM - Chat feature

### `app_extend_playlist.py`
**Exports**: `extend_playlist_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/voyager_manager.py`
**Change Impact**: MEDIUM - Playlist builder

### `app_map.py`
**Exports**: `map_bp` (Blueprint)
**Imports**:
- `app_helper.py`
**Change Impact**: LOW - Visualization feature

### `app_path.py`
**Exports**: `path_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/path_manager.py`
**Change Impact**: LOW - Path feature

### `app_alchemy.py`
**Exports**: `alchemy_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/song_alchemy.py`
**Change Impact**: LOW - Alchemy feature

### `app_artist_similarity.py`
**Exports**: `artist_similarity_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/artist_gmm_manager.py`
**Change Impact**: MEDIUM - Artist similarity

### `app_cron.py`
**Exports**: `cron_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `config.py`
**Change Impact**: LOW - Scheduling feature

### `app_collection.py`
**Exports**: `collection_bp` (Blueprint)
**Imports**:
- `app_helper.py`
- `tasks/collection_manager.py`
**Change Impact**: LOW - Collection management

## Task Modules

### `tasks/analysis.py`
**Exports**:
- `analyze_and_cluster_task()` - Main analysis entry
- `analyze_single_album_task()` - Per-album processing
**Imports**:
- `config.py`
- `app_helper.py`
- `tasks/mediaserver.py`
- `tasks/voyager_manager.py`
- `onnxruntime`
- `librosa`
**Change Impact**: CRITICAL - Core analysis pipeline

### `tasks/clustering.py`
**Exports**:
- `run_clustering_task()` - Main clustering entry
- `clustering_batch_job()` - Batch processing
**Imports**:
- `config.py`
- `app_helper.py`
- `ai.py`
- `tasks/clustering_gpu.py`
- `tasks/mediaserver.py`
- `sklearn.cluster`, `sklearn.mixture`
**Change Impact**: HIGH - Playlist generation

### `tasks/clustering_gpu.py`
**Exports**:
- `GPUKMeans`, `GPUDBSCAN`, `GPUPCA`, etc.
- `get_clustering_model()` - Factory function
- `check_gpu_available()`
**Imports**:
- `config.py`
- `cupy`, `cuml` (optional)
- `sklearn` (fallback)
**Imported By**: `tasks/clustering.py`
**Change Impact**: LOW - GPU acceleration only

### `tasks/voyager_manager.py`
**Exports**:
- `load_voyager_index_for_querying()`
- `build_and_store_voyager_index()`
- `find_nearest_neighbors_by_id()`
- `find_nearest_neighbors_by_vector()`
- `create_playlist_from_ids()`
- `search_tracks_by_title_and_artist()`
**Imports**:
- `config.py`
- `app_helper.py`
- `voyager`
- `tasks/mediaserver.py`
**Imported By**: Multiple blueprints, `tasks/path_manager.py`
**Change Impact**: CRITICAL - Core similarity search

### `tasks/mediaserver.py`
**Exports**:
- `get_recent_albums()`
- `get_tracks_from_album()`
- `download_track()`
- `create_instant_playlist()`
**Imports**:
- `config.py`
- `tasks/mediaserver_*.py` (server implementations)
**Imported By**: `tasks/analysis.py`, `tasks/clustering.py`, `tasks/voyager_manager.py`
**Change Impact**: HIGH - Media server abstraction

### `tasks/mediaserver_jellyfin.py`
**Exports**: Server-specific functions
**Imports**: `config.py`, `requests`
**Imported By**: `tasks/mediaserver.py`
**Change Impact**: LOW - Jellyfin only

### `tasks/mediaserver_navidrome.py`
**Exports**: Server-specific functions
**Imports**: `config.py`, `requests`
**Imported By**: `tasks/mediaserver.py`
**Change Impact**: LOW - Navidrome only

### `tasks/mediaserver_emby.py`
**Exports**: Server-specific functions
**Imports**: `config.py`, `requests`
**Imported By**: `tasks/mediaserver.py`
**Change Impact**: LOW - Emby only

### `tasks/mediaserver_lyrion.py`
**Exports**: Server-specific functions
**Imports**: `config.py`, `requests`
**Imported By**: `tasks/mediaserver.py`
**Change Impact**: LOW - Lyrion only

### `tasks/mediaserver_plex.py`
**Exports**: Server-specific functions
**Imports**: `config.py`, `requests`
**Imported By**: `tasks/mediaserver.py`
**Change Impact**: LOW - Plex only

### `tasks/path_manager.py`
**Exports**:
- `generate_music_path()`
**Imports**:
- `config.py`
- `tasks/voyager_manager.py`
**Imported By**: `app_path.py`
**Change Impact**: LOW - Path feature only

### `tasks/song_alchemy.py`
**Exports**:
- `blend_songs()`
**Imports**:
- `tasks/voyager_manager.py`
**Imported By**: `app_alchemy.py`
**Change Impact**: LOW - Alchemy feature only

### `tasks/artist_gmm_manager.py`
**Exports**:
- `build_and_store_artist_index()`
- `find_similar_artists()`
**Imports**:
- `config.py`
- `app_helper.py`
- `sklearn.mixture`
**Imported By**: `app_artist_similarity.py`
**Change Impact**: MEDIUM - Artist similarity

### `tasks/collection_manager.py`
**Exports**:
- Collection management functions
**Imports**:
- `app_helper.py`
**Imported By**: `app_collection.py`
**Change Impact**: LOW - Collection feature

## Dependency Graph (Simplified)

```
                    ┌─────────────┐
                    │  config.py  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ app_helper  │ │    ai.py    │ │   tasks/    │
    └──────┬──────┘ └──────┬──────┘ │ mediaserver │
           │               │        └──────┬──────┘
           ▼               │               │
    ┌─────────────┐        │        ┌──────┴──────┐
    │   app.py    │        │        │   tasks/    │
    │ (blueprints)│        │        │  analysis   │
    └──────┬──────┘        │        └──────┬──────┘
           │               │               │
           ▼               ▼               ▼
    ┌─────────────────────────────────────────────┐
    │              tasks/clustering               │
    └─────────────────────┬───────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────┐
    │            tasks/voyager_manager            │
    └─────────────────────────────────────────────┘
```

## Critical Paths

### Analysis Pipeline
```
app_analysis.py → tasks/analysis.py → tasks/mediaserver.py
                                    → tasks/voyager_manager.py
```

### Clustering Pipeline
```
app_clustering.py → tasks/clustering.py → tasks/clustering_gpu.py
                                        → ai.py
                                        → tasks/mediaserver.py
```

### Similarity Search
```
app_voyager.py → tasks/voyager_manager.py → voyager (library)
                                          → app_helper.py (DB)
```

### Chat Feature
```
app_chat.py → ai.py → External AI APIs
            → tasks/voyager_manager.py (song lookup)
```

## Coupling Analysis

| Module | Afferent (depended on) | Efferent (depends on) | Instability |
|--------|------------------------|----------------------|-------------|
| config.py | HIGH (20+) | LOW (1) | 0.05 (Stable) |
| app_helper.py | HIGH (15+) | MEDIUM (5) | 0.25 (Stable) |
| tasks/voyager_manager.py | HIGH (8) | MEDIUM (4) | 0.33 (Stable) |
| tasks/mediaserver.py | MEDIUM (5) | LOW (5) | 0.50 (Neutral) |
| ai.py | MEDIUM (3) | MEDIUM (4) | 0.57 (Neutral) |
| tasks/clustering.py | LOW (1) | HIGH (8) | 0.89 (Unstable) |
| tasks/analysis.py | LOW (1) | HIGH (7) | 0.88 (Unstable) |

**Legend**:
- Afferent: Number of modules that depend on this module
- Efferent: Number of modules this module depends on
- Instability = Efferent / (Afferent + Efferent)
- Lower instability = More stable (should be abstract/interfaces)
- Higher instability = Less stable (should be concrete implementations)
