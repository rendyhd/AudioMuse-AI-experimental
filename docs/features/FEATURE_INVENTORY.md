# AudioMuse-AI Feature Inventory

## Core Features

### 1. Audio Analysis
**Status**: Production
**Location**: `app_analysis.py`, `tasks/analysis.py`
**Description**: Analyzes audio files to extract features and generate ML embeddings.

**Capabilities**:
- Fetches tracks from configured media server
- Downloads and loads audio (FFmpeg or librosa)
- Extracts audio features: tempo, energy, spectral characteristics
- Generates 200-dimensional embeddings via ONNX MusicNN models
- Predicts mood scores (danceable, aggressive, happy, party, relaxed, sad)
- Stores embeddings and features in PostgreSQL
- Builds/updates Voyager HNSW index for similarity search
- Supports batch processing with configurable album limits
- GPU-accelerated ONNX inference (CUDA)
- Multiprocessing for CPU-bound audio processing

**UI**: Main dashboard at `/`

### 2. Intelligent Clustering & Playlist Generation
**Status**: Production
**Location**: `app_clustering.py`, `tasks/clustering.py`, `tasks/clustering_gpu.py`
**Description**: Uses evolutionary Monte Carlo search to find optimal clustering parameters for playlist generation.

**Capabilities**:
- Multiple clustering algorithms: KMeans, DBSCAN, GMM, Spectral
- Evolutionary parameter optimization (5000+ iterations default)
- Batched RQ job execution for parallelization
- Configurable scoring weights (diversity, purity, silhouette, etc.)
- Stratified sampling by genre for balanced representation
- AI-powered playlist naming (Gemini, Mistral, OpenAI, Ollama)
- GPU-accelerated clustering via RAPIDS cuML
- Automatic playlist creation on media server
- Rating-based filtering

**UI**: Clustering section on main dashboard

### 3. Song Similarity Search
**Status**: Production
**Location**: `app_voyager.py`, `tasks/voyager_manager.py`
**Description**: Finds similar songs using Voyager HNSW index.

**Capabilities**:
- Approximate nearest neighbor search (Voyager)
- Multiple distance metrics: angular (cosine), euclidean, dot product
- Duplicate filtering by distance threshold
- Name/artist deduplication
- Artist cap per result (MAX_SONGS_PER_ARTIST)
- Mood similarity filtering
- Rating-based filtering
- "Radius similarity" mode with bucketed greedy walk for better variety
- Instant playlist creation on media server

**UI**: `/similarity` page

### 4. Artist Similarity
**Status**: Production
**Location**: `app_artist_similarity.py`, `tasks/artist_gmm_manager.py`
**Description**: Finds similar artists using GMM-based clustering.

**Capabilities**:
- Gaussian Mixture Model per-artist embedding
- Aggregates song embeddings by artist
- Finds similar artists based on centroid distances
- Returns songs from similar artists

**UI**: `/artist_similarity` page

### 5. Music Path Generation
**Status**: Production
**Location**: `app_path.py`, `tasks/path_manager.py`
**Description**: Creates musical journeys between two songs.

**Capabilities**:
- Pathfinding using centroid-based navigation
- Configurable path length
- Duplicate filtering options
- Smooth transitions between musical styles

**UI**: `/path` page

### 6. Song Alchemy (Blending)
**Status**: Production
**Location**: `app_alchemy.py`, `tasks/song_alchemy.py`
**Description**: Blends song characteristics by vector arithmetic.

**Capabilities**:
- Add/subtract song embeddings
- Temperature-based probabilistic sampling
- Create "synthetic" songs from multiple sources
- Find real songs matching blended vectors

**UI**: `/alchemy` page

### 7. 2D Music Map Visualization
**Status**: Production
**Location**: `app_map.py`, `app_helper.py`
**Description**: Visualizes entire music library in 2D space.

**Capabilities**:
- UMAP/PCA dimensionality reduction
- Pre-computed projections stored in database
- Color-coded by genre/mood
- Interactive pan/zoom
- Click-to-play integration

**UI**: `/map` page

### 8. Sonic Fingerprint
**Status**: Production
**Location**: `app_sonic_fingerprint.py`
**Description**: Analyzes user listening patterns.

**Capabilities**:
- Aggregates listening history
- Generates user "fingerprint" embedding
- Suggests music matching user preferences

**UI**: `/sonic_fingerprint` page

### 9. AI Chat Interface
**Status**: Production
**Location**: `app_chat.py`, `ai.py`
**Description**: Natural language interface for playlist creation.

**Capabilities**:
- Multi-step conversation with AI
- Intent understanding (artist similarity, genre, mood, temporal)
- Execution plan generation
- Database query integration
- Multiple AI providers: Gemini, Mistral, OpenAI, Ollama
- Vibe matching for creative requests

**UI**: `/chat` page

### 10. Playlist Builder (Extend Playlist)
**Status**: Production
**Location**: `app_extend_playlist.py`
**Description**: Interactive playlist building with smart filters.

**Capabilities**:
- Seed song selection
- Similarity search with filters
- Manual track curation
- Drag-and-drop reordering
- Save to media server
- Track weight configuration

**UI**: `/extend_playlist` page

### 11. Scheduled Tasks (Cron)
**Status**: Production
**Location**: `app_cron.py`
**Description**: Schedule recurring analysis and clustering jobs.

**Capabilities**:
- Configurable cron expressions
- Analysis scheduling
- Clustering scheduling
- Enable/disable individual jobs
- Last run tracking

**UI**: `/cron` page

### 12. Collection Management
**Status**: Production
**Location**: `app_collection.py`, `tasks/collection_manager.py`
**Description**: Manage track collections and queues.

**Capabilities**:
- Create/edit collections
- Add/remove tracks
- Queue management
- Export to playlist

**UI**: `/collection` page

### 13. Waveform Visualization
**Status**: Production
**Location**: `app_waveform.py`
**Description**: Display audio waveforms.

**Capabilities**:
- Generate waveform data
- Interactive visualization
- Seek position display

**UI**: Embedded in various pages

### 14. Multi-Server Playlist Sync
**Status**: Beta (feat/playlist-builder branch)
**Location**: `app_playlist_sync.py`, `tasks/playlist_sync.py`
**Description**: Sync playlists across multiple media servers.

**Capabilities**:
- Primary/secondary server configuration
- Track mapping by file path
- Bidirectional sync support
- Jellyfin, Navidrome, Emby, Plex support

**UI**: Configuration via environment variables

## Media Server Integrations

### Jellyfin
**Status**: Production
**Location**: `tasks/mediaserver_jellyfin.py`
- Full support: albums, tracks, playlists, download

### Navidrome
**Status**: Production
**Location**: `tasks/mediaserver_navidrome.py`
- Subsonic API compatible
- Full support: albums, tracks, playlists

### Emby
**Status**: Production
**Location**: `tasks/mediaserver_emby.py`
- Similar to Jellyfin API
- Full support: albums, tracks, playlists

### Lyrion (LMS)
**Status**: Production
**Location**: `tasks/mediaserver_lyrion.py`
- JSON-RPC API
- Full support: albums, tracks, playlists

### Plex
**Status**: Beta
**Location**: `tasks/mediaserver_plex.py`
- REST API with XML responses
- Library browsing, track download, playlist creation

## AI Provider Integrations

### Google Gemini
**Status**: Production
**Location**: `ai.py`
- Playlist naming, chat interface

### Mistral
**Status**: Production
**Location**: `ai.py`
- Playlist naming, chat interface

### OpenAI / OpenRouter
**Status**: Production
**Location**: `ai.py`
- GPT models via OpenAI-compatible API
- Playlist naming, chat interface

### Ollama (Self-hosted)
**Status**: Production
**Location**: `ai.py`
- Local LLM deployment
- Playlist naming, chat interface

## Feature Matrix

| Feature | Web UI | REST API | GPU Support | Multi-Server |
|---------|--------|----------|-------------|--------------|
| Audio Analysis | Yes | Yes | Yes (ONNX) | - |
| Clustering | Yes | Yes | Yes (cuML) | - |
| Song Similarity | Yes | Yes | - | - |
| Artist Similarity | Yes | Yes | - | - |
| Music Path | Yes | Yes | - | - |
| Song Alchemy | Yes | Yes | - | - |
| 2D Map | Yes | Yes | - | - |
| AI Chat | Yes | Yes | - | - |
| Playlist Builder | Yes | Yes | - | - |
| Cron Jobs | Yes | Yes | - | - |
| Playlist Sync | - | Yes | - | Yes |
