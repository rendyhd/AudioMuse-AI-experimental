# AudioMuse-AI Configuration Variables

## Media Server Configuration

### Jellyfin
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JELLYFIN_URL` | Yes* | - | Jellyfin server URL (e.g., `http://jellyfin:8096`) |
| `JELLYFIN_USER_ID` | Yes* | - | Jellyfin user ID |
| `JELLYFIN_TOKEN` | Yes* | - | Jellyfin API token |

### Emby
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMBY_URL` | Yes* | - | Emby server URL |
| `EMBY_USER_ID` | Yes* | - | Emby user ID |
| `EMBY_TOKEN` | Yes* | - | Emby API token |

### Navidrome
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NAVIDROME_URL` | Yes* | - | Navidrome server URL |
| `NAVIDROME_USER` | Yes* | - | Navidrome username |
| `NAVIDROME_PASSWORD` | Yes* | - | Navidrome password |

### Lyrion/LMS
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LYRION_URL` | Yes* | - | Lyrion server URL |

### Plex
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLEX_URL` | Yes* | - | Plex server URL (e.g., `http://plex:32400`) |
| `PLEX_TOKEN` | Yes* | - | Plex API token |

### Server Selection
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MEDIASERVER_TYPE` | Yes | `jellyfin` | Media server type: `jellyfin`, `emby`, `navidrome`, `lyrion`, `plex` |
| `MUSIC_LIBRARIES` | No | - | Comma-separated library names to scan (empty = all) |

*Required only if using that media server type

## Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_HOST` | Yes | `postgres` | PostgreSQL hostname |
| `POSTGRES_PORT` | Yes | `5432` | PostgreSQL port |
| `POSTGRES_DB` | Yes | `audiomusedb` | Database name |
| `POSTGRES_USER` | Yes | `audiomuse` | Database user |
| `POSTGRES_PASSWORD` | Yes | - | Database password |
| `DATABASE_URL` | Auto | - | Full connection string (auto-generated) |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection URL |

## AI Provider Configuration

### Provider Selection
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_MODEL_PROVIDER` | No | `NONE` | AI provider: `NONE`, `GEMINI`, `MISTRAL`, `OPENAI`, `OLLAMA` |

### Google Gemini
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes* | - | Gemini API key |
| `GEMINI_MODEL_NAME` | No | `gemini-2.5-pro` | Gemini model name |
| `GEMINI_API_CALL_DELAY_SECONDS` | No | `7` | Delay between API calls |

### Mistral
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MISTRAL_API_KEY` | Yes* | - | Mistral API key |
| `MISTRAL_MODEL_NAME` | No | `ministral-3b-latest` | Mistral model name |
| `MISTRAL_API_CALL_DELAY_SECONDS` | No | `7` | Delay between API calls |

### OpenAI / OpenRouter
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI/OpenRouter API key |
| `OPENAI_SERVER_URL` | No | `https://openrouter.ai/api/v1/chat/completions` | API endpoint |
| `OPENAI_MODEL_NAME` | No | - | Model name |
| `OPENAI_API_CALL_DELAY_SECONDS` | No | `7` | Delay between API calls |

### Ollama (Self-hosted)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_SERVER_URL` | Yes* | - | Ollama server URL (e.g., `http://ollama:11434/api/generate`) |
| `OLLAMA_MODEL_NAME` | No | `llama3.1` | Ollama model name |

*Required only if using that AI provider

## Analysis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NUM_RECENT_ALBUMS` | No | `0` | Albums to analyze (0 = all) |
| `TOP_N_MOODS` | No | `5` | Number of mood tags in feature vector |
| `REBUILD_INDEX_BATCH_SIZE` | No | `200` | Albums before index rebuild |
| `AUDIO_LOAD_TIMEOUT` | No | `600` | Audio loading timeout (seconds) |
| `MODELS_PATH` | No | `./models` | ONNX models directory |

## GPU & Performance Configuration

### ONNX Inference
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ONNX_BATCH_SIZE` | No | `256` | GPU batch size for inference |
| `USE_FFMPEG_DECODER` | No | `true` | Use FFmpeg for audio decoding |
| `USE_MULTIPROCESSING` | No | `true` | Enable multiprocessing |
| `MULTIPROCESSING_WORKERS` | No | `6` | Number of worker processes |
| `USE_FAST_TEMPO` | No | `true` | Faster tempo detection |
| `POOL_MAX_TASKS_BEFORE_REFRESH` | No | `500` | Worker pool refresh threshold |

### GPU Clustering
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_GPU_CLUSTERING` | No | `false` | Enable RAPIDS cuML for clustering |

### Direct File Access
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_DIRECT_FILE_ACCESS` | No | `false` | Read files directly (bypass HTTP) |
| `DIRECT_FILE_PATH_MAPPING` | No | - | Path mapping (e.g., `/mnt/plex:/mnt/music`) |
| `ENABLE_PREFETCH_BUFFER` | No | `true` | Pre-load files into RAM |
| `PREFETCH_BUFFER_SIZE` | No | `12` | Number of files to prefetch |
| `PREFETCH_MAX_MEMORY_MB` | No | `1024` | Max prefetch memory (MB) |

### Parallel Downloads
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_PARALLEL_DOWNLOADS` | No | `true` | Enable parallel track downloads |
| `MAX_PARALLEL_DOWNLOADS` | No | `2` | Number of parallel downloads |
| `DOWNLOAD_CHUNK_SIZE` | No | `65536` | Download chunk size (bytes) |
| `DOWNLOAD_RETRY_ATTEMPTS` | No | `3` | Retry attempts for downloads |
| `DOWNLOAD_RETRY_BASE_DELAY` | No | `2.0` | Base retry delay (seconds) |
| `PARALLEL_DOWNLOAD_STAGGER_DELAY` | No | `1.0` | Stagger delay (seconds) |
| `ENABLE_ASYNC_INDEX_REBUILDS` | No | `true` | Non-blocking index rebuilds |
| `ENABLE_MODEL_PRELOAD` | No | `true` | Preload ONNX models |

## Clustering Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLUSTER_ALGORITHM` | No | `kmeans` | Algorithm: `kmeans`, `dbscan`, `gmm`, `spectral` |
| `ENABLE_CLUSTERING_EMBEDDINGS` | No | `true` | Use embeddings vs features |
| `CLUSTERING_RUNS` | No | `5000` | Evolutionary search iterations |
| `ITERATIONS_PER_BATCH_JOB` | No | `20` | Iterations per RQ job |
| `MAX_CONCURRENT_BATCH_JOBS` | No | `10` | Max parallel batch jobs |
| `TOP_N_PLAYLISTS` | No | `8` | Top playlists to keep |
| `MAX_SONGS_PER_CLUSTER` | No | `100` | Max songs per playlist |

### Algorithm Parameters
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NUM_CLUSTERS_MIN` | No | `5` | Min clusters (KMeans/GMM) |
| `NUM_CLUSTERS_MAX` | No | `25` | Max clusters (KMeans/GMM) |
| `DBSCAN_EPS_MIN` | No | `0.1` | Min epsilon (DBSCAN) |
| `DBSCAN_EPS_MAX` | No | `2.0` | Max epsilon (DBSCAN) |
| `DBSCAN_MIN_SAMPLES_MIN` | No | `3` | Min samples (DBSCAN) |
| `DBSCAN_MIN_SAMPLES_MAX` | No | `10` | Max samples (DBSCAN) |
| `GMM_N_COMPONENTS_MIN` | No | `5` | Min components (GMM) |
| `GMM_N_COMPONENTS_MAX` | No | `25` | Max components (GMM) |
| `GMM_COVARIANCE_TYPE` | No | `full` | Covariance type (GMM) |
| `SPECTRAL_N_CLUSTERS_MIN` | No | `5` | Min clusters (Spectral) |
| `SPECTRAL_N_CLUSTERS_MAX` | No | `25` | Max clusters (Spectral) |
| `SPECTRAL_N_NEIGHBORS` | No | `10` | Neighbors (Spectral) |
| `PCA_COMPONENTS_MIN` | No | `10` | Min PCA components |
| `PCA_COMPONENTS_MAX` | No | `50` | Max PCA components |

### Scoring Weights
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SCORE_WEIGHT_DIVERSITY` | No | `2.0` | Inter-playlist mood diversity |
| `SCORE_WEIGHT_PURITY` | No | `1.0` | Intra-playlist mood consistency |
| `SCORE_WEIGHT_SILHOUETTE` | No | `0.0` | Silhouette score weight |
| `SCORE_WEIGHT_DAVIES_BOULDIN` | No | `0.0` | Davies-Bouldin weight |
| `SCORE_WEIGHT_CALINSKI_HARABASZ` | No | `0.0` | Calinski-Harabasz weight |
| `SCORE_WEIGHT_OTHER_FEATURE_DIVERSITY` | No | `0.5` | Other features diversity |
| `SCORE_WEIGHT_OTHER_FEATURE_PURITY` | No | `0.5` | Other features purity |

### Stratified Sampling
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRATIFIED_GENRES` | No | - | Comma-separated genre list |
| `MIN_SONGS_PER_GENRE_FOR_STRATIFICATION` | No | `10` | Min songs per genre |
| `STRATIFIED_SAMPLING_TARGET_PERCENTILE` | No | `50` | Target percentile |

## Similarity Search Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VOYAGER_METRIC` | No | `angular` | Distance metric: `angular`, `euclidean`, `dot` |
| `VOYAGER_EF_CONSTRUCTION` | No | `512` | HNSW construction parameter |
| `VOYAGER_M` | No | `48` | HNSW max connections |
| `VOYAGER_QUERY_EF` | No | `1024` | HNSW query parameter |
| `MAX_SONGS_PER_ARTIST` | No | `3` | Artist cap in results |
| `DUPLICATE_DISTANCE_THRESHOLD_COSINE` | No | `0.05` | Cosine duplicate threshold |
| `DUPLICATE_DISTANCE_THRESHOLD_EUCLIDEAN` | No | `0.5` | Euclidean duplicate threshold |
| `DUPLICATE_DISTANCE_CHECK_LOOKBACK` | No | `5` | Lookback for duplicate check |
| `MOOD_SIMILARITY_ENABLE` | No | `false` | Enable mood filtering |
| `MOOD_SIMILARITY_THRESHOLD` | No | `0.3` | Mood similarity threshold |
| `SIMILARITY_ELIMINATE_DUPLICATES_DEFAULT` | No | `true` | Default duplicate elimination |
| `SIMILARITY_RADIUS_DEFAULT` | No | `false` | Default radius similarity |

## Web Server Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_ENV` | No | `production` | Flask environment |
| `ENABLE_PROXY_FIX` | No | `false` | Enable ProxyFix middleware |
| `SECRET_KEY` | No | Auto-generated | Flask secret key |

## Multi-Server Playlist Sync

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLAYLIST_PRIMARY_SERVER` | No | - | Primary server type |
| `PLAYLIST_SECONDARY_SERVERS` | No | - | Comma-separated secondary servers |
| `PLAYLIST_SYNC_ENABLED` | No | `true` | Enable playlist sync |

## Worker Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WORKER_URL` | No | - | Remote worker URL |
| `WORKER_POSTGRES_HOST` | No | - | Worker PostgreSQL host |
| `WORKER_REDIS_URL` | No | - | Worker Redis URL |
| `MAX_QUEUED_ANALYSIS_JOBS` | No | `150` | Max RQ queue size |

## Environment Example

See `deployment/.env.example` for a complete example configuration file.
