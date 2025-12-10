# AudioMuse-AI API Surface

## API Overview

- **Base URL**: `http://localhost:8000` (configurable)
- **Documentation**: Swagger UI at `/apidocs`
- **Format**: JSON (request/response)
- **Authentication**: None (designed for local/private network use)

## Analysis Endpoints

### POST `/api/analysis/start`
Start the audio analysis pipeline.

**Request Body**:
```json
{
  "num_recent_albums": 0,      // 0 = all albums
  "music_libraries": "Music"    // Comma-separated library names
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "uuid",
  "task_type": "main_analysis"
}
```

### POST `/api/analysis/cancel`
Cancel running analysis task.

**Request Body**:
```json
{
  "task_id": "uuid"
}
```

## Clustering Endpoints

### POST `/api/clustering/start`
Start clustering and playlist generation.

**Request Body**:
```json
{
  "clustering_method": "kmeans",
  "num_clusters_min": 5,
  "num_clusters_max": 25,
  "clustering_runs": 5000,
  "top_n_playlists": 8,
  "ai_model_provider": "GEMINI",
  "min_rating": 3.5
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "uuid",
  "task_type": "main_clustering"
}
```

## Similarity Endpoints

### POST `/api/similarity/find`
Find similar songs by item ID.

**Request Body**:
```json
{
  "item_id": "jellyfin-item-id",
  "n": 50,
  "eliminate_duplicates": true,
  "mood_similarity": true,
  "radius_similarity": true,
  "min_rating": 3.0
}
```

**Response**:
```json
{
  "results": [
    {
      "item_id": "uuid",
      "title": "Song Title",
      "author": "Artist Name",
      "distance": 0.123
    }
  ]
}
```

### POST `/api/similarity/search`
Search tracks by title and artist.

**Request Body**:
```json
{
  "title": "partial title",
  "artist": "partial artist",
  "limit": 15
}
```

### POST `/api/similarity/instant_playlist`
Create instant playlist from similar songs.

**Request Body**:
```json
{
  "item_id": "seed-song-id",
  "n": 50,
  "playlist_name": "My Playlist"
}
```

## Artist Similarity Endpoints

### POST `/api/artist/similar`
Find similar artists.

**Request Body**:
```json
{
  "artist_name": "Artist Name",
  "n": 10
}
```

### GET `/api/artist/list`
Get all artists in the database.

## Path Endpoints

### POST `/api/path/generate`
Generate musical path between two songs.

**Request Body**:
```json
{
  "start_item_id": "uuid",
  "end_item_id": "uuid",
  "path_length": 10
}
```

## Alchemy Endpoints

### POST `/api/alchemy/blend`
Blend songs by vector arithmetic.

**Request Body**:
```json
{
  "add_item_ids": ["uuid1", "uuid2"],
  "subtract_item_ids": ["uuid3"],
  "n": 20,
  "temperature": 0.5
}
```

## Map Endpoints

### GET `/api/map/data`
Get 2D projection data for all songs.

**Response**:
```json
{
  "points": [
    {
      "item_id": "uuid",
      "x": 0.123,
      "y": 0.456,
      "title": "Song",
      "artist": "Artist",
      "genre": "Rock"
    }
  ]
}
```

### GET `/api/map/artist_data`
Get 2D projection data for artists.

## Chat Endpoints

### POST `/api/chat/message`
Send message to AI chat.

**Request Body**:
```json
{
  "message": "Create a playlist of energetic rock songs",
  "session_id": "optional-session-uuid"
}
```

**Response**:
```json
{
  "response": "AI response text",
  "tracks": [...],
  "session_id": "uuid"
}
```

## Playlist Builder Endpoints

### GET `/api/playlist/weights`
Get track weight configuration.

### POST `/api/playlist/create`
Create playlist on media server.

**Request Body**:
```json
{
  "name": "Playlist Name",
  "track_ids": ["uuid1", "uuid2", "uuid3"]
}
```

## Collection Endpoints

### GET `/api/collection/list`
List all collections.

### POST `/api/collection/create`
Create new collection.

### POST `/api/collection/{id}/add`
Add tracks to collection.

### DELETE `/api/collection/{id}`
Delete collection.

## Cron Endpoints

### GET `/api/cron/jobs`
List all scheduled jobs.

### POST `/api/cron/jobs`
Create scheduled job.

### PUT `/api/cron/jobs/{id}`
Update scheduled job.

### DELETE `/api/cron/jobs/{id}`
Delete scheduled job.

## Task Status Endpoints

### GET `/api/task/{task_id}`
Get task status by ID.

**Response**:
```json
{
  "task_id": "uuid",
  "task_type": "main_analysis",
  "status": "PROGRESS",
  "progress": 45,
  "details": {
    "message": "Analyzing album 10 of 22",
    "log": [...]
  }
}
```

### GET `/api/active_tasks`
Get all active tasks.

### GET `/api/last_task`
Get most recent task.

## Index Management Endpoints

### POST `/api/index/rebuild`
Trigger index rebuild.

### GET `/api/index/status`
Get index status.

## Waveform Endpoints

### GET `/api/waveform/{item_id}`
Get waveform data for a track.

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error message",
  "details": "Optional detailed information"
}
```

**Common HTTP Status Codes**:
- `200 OK` - Success
- `202 Accepted` - Task enqueued
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - Resource not found
- `409 Conflict` - Task already running
- `500 Internal Server Error` - Server error

## Rate Limiting

No rate limiting is implemented (designed for private network use).

## WebSocket Endpoints

None currently - uses polling for task status updates.

## External API Calls

The application makes outbound calls to:
1. **Media Server APIs** (Jellyfin, Navidrome, Emby, Lyrion, Plex)
2. **AI Provider APIs** (Gemini, Mistral, OpenAI/OpenRouter, Ollama)
