# Multi-Server Playlist Sync

This feature enables syncing playlists from a primary media server to one or more secondary servers. It's designed for setups where multiple media servers share the same music library mount (identical file paths).

## Overview

When you create a playlist on your primary server (e.g., Plex), the sync feature automatically creates the same playlist on all configured secondary servers (e.g., Jellyfin, Navidrome) by mapping track IDs via file paths.

## Requirements

- All configured servers must access the **same music library** with **identical file paths**
- Secondary servers must be properly configured with their respective credentials
- The track mapping cache must be built (happens automatically on first sync)

## Configuration

Add the following environment variables to your `.env` file:

```env
# Primary server for audio analysis (defaults to MEDIASERVER_TYPE if not set)
PLAYLIST_PRIMARY_SERVER=plex

# Secondary servers to sync playlists to (comma-separated)
PLAYLIST_SECONDARY_SERVERS=jellyfin,navidrome

# Enable/disable playlist sync globally (default: true)
PLAYLIST_SYNC_ENABLED=true
```

### Supported Servers

The following servers can be configured as primary or secondary:
- `plex`
- `jellyfin`
- `emby`
- `navidrome`
- `lyrion`
- `mpd`

### Library Filtering (MUSIC_LIBRARIES)

The `MUSIC_LIBRARIES` setting affects both analysis and sync:

- **Primary server**: Only libraries listed will be analyzed and added to the database
- **Secondary servers**: When building the track mapping, only tracks from listed libraries will be indexed

**Important considerations:**

1. If library names match across all servers, use the same `MUSIC_LIBRARIES` value
2. If library names differ, leave `MUSIC_LIBRARIES` empty (scans all libraries) for best sync compatibility
3. Tracks outside the configured libraries won't be synced, even if they exist on all servers

```env
# Example: Same library name "Music" on all servers
MUSIC_LIBRARIES=Music

# Example: Leave empty for full compatibility when library names differ
MUSIC_LIBRARIES=
```

### Example Configurations

**Plex as primary, Jellyfin as secondary:**
```env
MEDIASERVER_TYPE=plex
PLAYLIST_PRIMARY_SERVER=plex
PLAYLIST_SECONDARY_SERVERS=jellyfin

# Primary server credentials
PLEX_URL=http://192.168.1.100:32400
PLEX_TOKEN=your_plex_token

# Secondary server credentials (required for sync)
JELLYFIN_URL=http://192.168.1.100:8096
JELLYFIN_USER_ID=your_user_id
JELLYFIN_TOKEN=your_jellyfin_token
```

**Jellyfin as primary, sync to both Plex and Navidrome:**
```env
MEDIASERVER_TYPE=jellyfin
PLAYLIST_PRIMARY_SERVER=jellyfin
PLAYLIST_SECONDARY_SERVERS=plex,navidrome

# Configure all three servers...
```

## How It Works

### Track ID Mapping

Each media server assigns its own unique IDs to tracks. The sync feature uses file paths as the common identifier:

1. When sync is first triggered, the system fetches all songs from configured servers
2. For each song, it extracts the file path and server-specific track ID
3. This mapping is stored in the `track_server_mapping` database table
4. When syncing a playlist, track IDs are converted using this mapping

### Lazy Loading

The track mapping cache is built **on first sync request** rather than at startup. This avoids slow startup times for large libraries.

### Sync Process

When a playlist is created:

1. Playlist is created on the primary server with primary server track IDs
2. If sync is enabled, the system:
   - Retrieves file paths for the primary server track IDs
   - Looks up corresponding track IDs for each secondary server
   - Creates the playlist on each secondary server with converted IDs
3. Any unmapped tracks are logged but don't block the sync

## API Endpoints

### GET /api/playlist-sync/status

Returns the current sync configuration.

**Response:**
```json
{
  "enabled": true,
  "primary_server": "plex",
  "secondary_servers": ["jellyfin", "navidrome"],
  "sync_active": true
}
```

### GET /api/playlist-sync/stats

Returns statistics about the track mapping cache.

**Response:**
```json
{
  "total_paths": 15000,
  "servers": {
    "plex": 15000,
    "jellyfin": 14950,
    "navidrome": 14980
  },
  "last_updated": "2024-01-15T10:30:00"
}
```

### POST /api/playlist-sync/refresh

Refreshes the track mapping cache for all or specific secondary servers.

**Request Body (optional):**
```json
{
  "server": "jellyfin"
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "jellyfin": {
      "total_songs": 15000,
      "mapped_count": 15000
    }
  }
}
```

### GET /api/playlist-sync/enabled

Quick check if sync is active.

**Response:**
```json
{
  "enabled": true
}
```

## Features with Sync Support

Playlist sync works with all features that create playlists:

| Feature | Description |
|---------|-------------|
| Clustering | Automatic playlists from audio analysis clustering |
| Instant Playlist | Quick playlist creation from any feature |
| Similar Songs | Playlists based on song similarity |
| Artist Similarity | Playlists based on artist similarity |
| Song Path | Musical journey between two songs |
| Song Alchemy | Blended song characteristics |
| Playlist Builder | Smart filter and manual playlist creation |
| Extend Playlist | Extended versions of existing playlists |
| Sonic Fingerprint | Playlists based on listening history |

## Controlling Sync Behavior

### Global Toggle

Set `PLAYLIST_SYNC_ENABLED=false` in your environment to disable sync globally.

### Per-Request Toggle

All playlist creation functions accept a `sync_enabled` parameter:

```python
from tasks.mediaserver import create_instant_playlist

# Sync enabled (default)
create_instant_playlist("My Playlist", track_ids)

# Sync disabled for this specific call
create_instant_playlist("My Playlist", track_ids, sync_enabled=False)
```

## Database Schema

The feature uses a single table for track mapping:

```sql
CREATE TABLE track_server_mapping (
    file_path TEXT PRIMARY KEY,
    plex_id TEXT,
    jellyfin_id TEXT,
    emby_id TEXT,
    navidrome_id TEXT,
    lyrion_id TEXT,
    mpd_id TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

## Direct File Access (Performance Optimization)

For faster audio analysis, you can enable direct file access which reads files directly from a mounted volume instead of downloading via HTTP. This bypasses network issues (IncompleteRead errors) and is 10-100x faster.

### Configuration

```env
# Enable direct file access
ENABLE_DIRECT_FILE_ACCESS=true

# Optional: Path mapping if server paths differ from container paths
# Format: "server_path_prefix:container_path_prefix"
DIRECT_FILE_PATH_MAPPING=/mnt/plex/music:/data/music
```

### Docker Volume Mount

You must mount your music library in the Docker container. Add to `docker-compose.yaml`:

```yaml
volumes:
  - /path/to/music:/data/Music:ro  # Read-only mount
```

### Platform-Specific Notes

#### Linux / macOS
Direct file access works seamlessly. Mount your music directory and ensure paths match what your media server reports.

#### Windows with Docker Desktop

Docker Desktop on Windows/WSL2 has **limited support for network shares**:

- **Mapped drive letters (Z:\)**: Not accessible from Docker. WSL2 doesn't inherit Windows drive mappings.
- **UNC paths (\\\\server\\share)**: May work with CIFS volume driver, but requires credentials.
- **Local paths (C:\\Music)**: Work via `/mnt/c/Music` inside WSL2.

**Workarounds for Windows network shares:**

1. **Run Docker on the media server**: If your Plex/Jellyfin server is a Linux machine, run AudioMuse-AI there for direct filesystem access.

2. **WSL2 manual mount**: Mount the share inside WSL2, then use that path:
   ```bash
   # In WSL2
   sudo mkdir -p /mnt/music
   sudo mount -t cifs //192.168.1.70/Media /mnt/music -o username=user,password=pass
   ```
   Then use `/mnt/music` in docker-compose.

3. **CIFS volume driver with credentials**:
   ```bash
   docker volume create \
     --driver local \
     --opt type=cifs \
     --opt device="//192.168.1.70/Media/Music" \
     --opt "o=username=user,password=pass" \
     music-share
   ```

4. **Continue with HTTP downloads**: The retry mechanism handles most failures. Set these for better reliability:
   ```env
   DOWNLOAD_RETRY_ATTEMPTS=3
   DOWNLOAD_RETRY_BASE_DELAY=2.0
   MAX_PARALLEL_DOWNLOADS=2
   ```

### Fallback Behavior

When direct file access is enabled but a file isn't found at the mapped path, the system automatically falls back to HTTP download. This allows partial configurations where some files are accessible directly and others require download.

## Troubleshooting

### Playlists not syncing

1. Check if sync is enabled: `GET /api/playlist-sync/status`
2. Verify secondary servers are configured in `PLAYLIST_SECONDARY_SERVERS`
3. Check that secondary server credentials are correct
4. Review application logs for sync errors

### Many tracks not mapped

1. Ensure all servers access the same music library mount
2. Check that file paths are identical across servers
3. Refresh the mapping cache: `POST /api/playlist-sync/refresh`
4. Check `/api/playlist-sync/stats` for mapping counts

### Slow first sync

The first sync builds the mapping cache by fetching all songs from each server. For large libraries (10,000+ tracks), this may take a minute or two. Subsequent syncs use the cached mapping and are fast.

### Path mismatches

If servers use different mount points (e.g., `/music` vs `/data/music`), file paths won't match. Ensure all servers are configured to use identical paths to your music library.

## Architecture

### Files

| File | Purpose |
|------|---------|
| `config.py` | Sync configuration variables |
| `tasks/playlist_sync.py` | Core sync logic and track mapping |
| `tasks/mediaserver.py` | Dispatcher with sync integration |
| `app_playlist_sync.py` | API endpoints blueprint |
| `app_helper.py` | Database table definition |

### Flow Diagram

```
User creates playlist
        │
        ▼
┌─────────────────────────────────────┐
│  mediaserver.create_playlist()      │
│  or create_instant_playlist()       │
└─────────────────────────────────────┘
        │
        ├──────────────────────────────┐
        ▼                              ▼
┌───────────────────┐     ┌─────────────────────────┐
│ Create on Primary │     │ playlist_sync.          │
│ Server (Plex)     │     │ sync_to_secondary()     │
└───────────────────┘     └─────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ Jellyfin  │   │ Navidrome │   │   Emby    │
            │ (convert  │   │ (convert  │   │ (convert  │
            │  IDs)     │   │  IDs)     │   │  IDs)     │
            └───────────┘   └───────────┘   └───────────┘
```
