# tasks/playlist_sync.py
"""
Multi-Server Playlist Sync Module

This module provides functionality to sync playlists across multiple media servers.
It uses file paths as the common identifier since all servers share the same music library mount.

Key concepts:
- Primary server: The server used for audio analysis (where track IDs originate)
- Secondary servers: Servers to sync playlists to (using path-based ID mapping)
- Track mapping: A cache that maps file paths to track IDs for each server type
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import config

# Import server-specific functions for fetching songs and creating playlists
from tasks.mediaserver_jellyfin import (
    get_all_songs as jellyfin_get_all_songs,
    create_playlist as jellyfin_create_playlist,
)
from tasks.mediaserver_navidrome import (
    get_all_songs as navidrome_get_all_songs,
    create_playlist as navidrome_create_playlist,
)
from tasks.mediaserver_lyrion import (
    get_all_songs as lyrion_get_all_songs,
    create_playlist as lyrion_create_playlist,
)
from tasks.mediaserver_mpd import (
    get_all_songs as mpd_get_all_songs,
    create_playlist as mpd_create_playlist,
)
from tasks.mediaserver_emby import (
    get_all_songs as emby_get_all_songs,
    create_playlist as emby_create_playlist,
)
from tasks.mediaserver_plex import (
    get_all_songs as plex_get_all_songs,
    create_playlist as plex_create_playlist,
)

logger = logging.getLogger(__name__)

# Server function mappings
SERVER_GET_ALL_SONGS = {
    'jellyfin': jellyfin_get_all_songs,
    'navidrome': navidrome_get_all_songs,
    'lyrion': lyrion_get_all_songs,
    'mpd': mpd_get_all_songs,
    'emby': emby_get_all_songs,
    'plex': plex_get_all_songs,
}

SERVER_CREATE_PLAYLIST = {
    'jellyfin': jellyfin_create_playlist,
    'navidrome': navidrome_create_playlist,
    'lyrion': lyrion_create_playlist,
    'mpd': mpd_create_playlist,
    'emby': emby_create_playlist,
    'plex': plex_create_playlist,
}

# ID field names vary by server
SERVER_ID_FIELD = {
    'jellyfin': 'Id',
    'navidrome': 'id',
    'lyrion': 'id',
    'mpd': 'file',  # MPD uses file path as ID
    'emby': 'Id',
    'plex': 'Id',
}

# Path field names (most use 'Path', navidrome uses lowercase 'path')
SERVER_PATH_FIELD = {
    'jellyfin': 'Path',
    'navidrome': 'Path',  # Converted in get_all_songs
    'lyrion': 'url',  # Lyrion uses 'url' for file path
    'mpd': 'file',
    'emby': 'Path',
    'plex': 'Path',
}


def _normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent comparison across servers.
    Handles differences in path separators and case sensitivity.
    """
    if not path:
        return ""
    # Convert to forward slashes and lowercase for consistent comparison
    normalized = path.replace('\\', '/').lower()
    # Remove any leading/trailing whitespace
    return normalized.strip()


def _get_secondary_servers() -> List[str]:
    """
    Get list of secondary servers from configuration.
    Returns empty list if sync is disabled or no secondary servers configured.
    """
    if not config.PLAYLIST_SYNC_ENABLED:
        return []

    secondary_str = config.PLAYLIST_SECONDARY_SERVERS
    if not secondary_str:
        return []

    # Parse comma-separated list and validate server types
    servers = [s.strip().lower() for s in secondary_str.split(',') if s.strip()]
    valid_servers = [s for s in servers if s in SERVER_GET_ALL_SONGS]

    # Filter out primary server if accidentally included
    primary = config.PLAYLIST_PRIMARY_SERVER.lower()
    valid_servers = [s for s in valid_servers if s != primary]

    return valid_servers


def is_sync_enabled() -> bool:
    """Check if playlist sync is enabled and properly configured."""
    return config.PLAYLIST_SYNC_ENABLED and len(_get_secondary_servers()) > 0


def get_sync_status() -> Dict:
    """
    Get current sync configuration status.
    Returns a dict with primary server, secondary servers, and enabled status.
    """
    return {
        'enabled': config.PLAYLIST_SYNC_ENABLED,
        'primary_server': config.PLAYLIST_PRIMARY_SERVER,
        'secondary_servers': _get_secondary_servers(),
        'sync_active': is_sync_enabled(),
    }


# ##############################################################################
# TRACK MAPPING CACHE (Lazy Loading)
# ##############################################################################

def _get_db_connection():
    """Get a database connection for track mapping operations."""
    import psycopg2
    from config import DATABASE_URL
    return psycopg2.connect(DATABASE_URL)


def _build_path_to_id_map_for_server(server_type: str) -> Dict[str, str]:
    """
    Build a mapping from normalized file paths to track IDs for a specific server.
    This fetches all songs from the server and creates the mapping.
    """
    logger.info(f"Building path-to-ID mapping for {server_type}...")

    get_songs_func = SERVER_GET_ALL_SONGS.get(server_type)
    if not get_songs_func:
        logger.error(f"Unknown server type: {server_type}")
        return {}

    try:
        songs = get_songs_func()
        logger.info(f"Fetched {len(songs)} songs from {server_type}")
    except Exception as e:
        logger.error(f"Failed to fetch songs from {server_type}: {e}", exc_info=True)
        return {}

    id_field = SERVER_ID_FIELD.get(server_type, 'Id')
    path_field = SERVER_PATH_FIELD.get(server_type, 'Path')

    path_to_id = {}
    for song in songs:
        # Handle both uppercase and lowercase field names
        track_id = song.get(id_field) or song.get(id_field.lower()) or song.get('Id') or song.get('id')
        path = song.get(path_field) or song.get(path_field.lower()) or song.get('Path') or song.get('path')

        if track_id and path:
            normalized = _normalize_path(path)
            if normalized:
                path_to_id[normalized] = str(track_id)

    logger.info(f"Built mapping with {len(path_to_id)} entries for {server_type}")
    return path_to_id


def _save_mapping_to_db(path_to_id: Dict[str, str], server_type: str) -> int:
    """
    Save the path-to-ID mapping to the database for a specific server.
    Returns the number of records updated/inserted.
    """
    if not path_to_id:
        return 0

    # Map server type to database column
    column_map = {
        'plex': 'plex_id',
        'jellyfin': 'jellyfin_id',
        'emby': 'emby_id',
        'navidrome': 'navidrome_id',
        'lyrion': 'lyrion_id',
        'mpd': 'mpd_id',
    }

    column = column_map.get(server_type)
    if not column:
        logger.error(f"Unknown server type for database column: {server_type}")
        return 0

    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()

        count = 0
        for path, track_id in path_to_id.items():
            # Upsert: insert or update if exists
            cur.execute(f"""
                INSERT INTO track_server_mapping (file_path, {column}, last_updated)
                VALUES (%s, %s, %s)
                ON CONFLICT (file_path)
                DO UPDATE SET {column} = EXCLUDED.{column}, last_updated = EXCLUDED.last_updated
            """, (path, track_id, datetime.utcnow()))
            count += 1

        conn.commit()
        logger.info(f"Saved {count} mappings for {server_type} to database")
        return count

    except Exception as e:
        logger.error(f"Failed to save mapping to database: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return 0
    finally:
        if conn:
            conn.close()


def _load_mapping_from_db(server_type: str) -> Dict[str, str]:
    """
    Load the path-to-ID mapping from the database for a specific server.
    Returns a dict mapping normalized paths to track IDs.
    """
    column_map = {
        'plex': 'plex_id',
        'jellyfin': 'jellyfin_id',
        'emby': 'emby_id',
        'navidrome': 'navidrome_id',
        'lyrion': 'lyrion_id',
        'mpd': 'mpd_id',
    }

    column = column_map.get(server_type)
    if not column:
        logger.error(f"Unknown server type for database column: {server_type}")
        return {}

    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT file_path, {column} FROM track_server_mapping WHERE {column} IS NOT NULL")
        rows = cur.fetchall()

        path_to_id = {row[0]: row[1] for row in rows if row[0] and row[1]}
        logger.info(f"Loaded {len(path_to_id)} mappings for {server_type} from database")
        return path_to_id

    except Exception as e:
        logger.error(f"Failed to load mapping from database: {e}", exc_info=True)
        return {}
    finally:
        if conn:
            conn.close()


def refresh_mapping_for_server(server_type: str) -> Tuple[int, int]:
    """
    Refresh the track mapping cache for a specific server.
    Fetches all songs from the server and updates the database.

    Returns: (total_songs, mapped_count)
    """
    logger.info(f"Refreshing mapping cache for {server_type}...")

    path_to_id = _build_path_to_id_map_for_server(server_type)
    if not path_to_id:
        return (0, 0)

    saved = _save_mapping_to_db(path_to_id, server_type)
    return (len(path_to_id), saved)


def refresh_all_secondary_mappings() -> Dict[str, Tuple[int, int]]:
    """
    Refresh the track mapping cache for all secondary servers.
    Returns a dict of server_type -> (total_songs, mapped_count).
    """
    results = {}
    for server_type in _get_secondary_servers():
        results[server_type] = refresh_mapping_for_server(server_type)
    return results


def get_mapping_stats() -> Dict:
    """
    Get statistics about the current mapping cache.
    Returns counts for each server type.
    """
    column_map = {
        'plex': 'plex_id',
        'jellyfin': 'jellyfin_id',
        'emby': 'emby_id',
        'navidrome': 'navidrome_id',
        'lyrion': 'lyrion_id',
        'mpd': 'mpd_id',
    }

    stats = {'total_paths': 0, 'servers': {}}

    conn = None
    try:
        conn = _get_db_connection()
        cur = conn.cursor()

        # Get total paths
        cur.execute("SELECT COUNT(*) FROM track_server_mapping")
        stats['total_paths'] = cur.fetchone()[0]

        # Get count for each server
        for server, column in column_map.items():
            cur.execute(f"SELECT COUNT(*) FROM track_server_mapping WHERE {column} IS NOT NULL")
            stats['servers'][server] = cur.fetchone()[0]

        # Get last updated time
        cur.execute("SELECT MAX(last_updated) FROM track_server_mapping")
        last_updated = cur.fetchone()[0]
        stats['last_updated'] = last_updated.isoformat() if last_updated else None

        return stats

    except Exception as e:
        logger.error(f"Failed to get mapping stats: {e}", exc_info=True)
        return stats
    finally:
        if conn:
            conn.close()


# ##############################################################################
# CORE SYNC FUNCTIONS
# ##############################################################################

def _get_paths_for_primary_ids(primary_item_ids: List[str]) -> Dict[str, str]:
    """
    Get file paths for track IDs from the primary server.
    Returns a dict mapping track_id -> normalized_path.
    """
    primary_server = config.PLAYLIST_PRIMARY_SERVER.lower()

    # Load mapping from database for primary server
    mapping = _load_mapping_from_db(primary_server)

    # If no mapping exists, build it
    if not mapping:
        logger.info(f"No mapping found for primary server {primary_server}, building cache...")
        path_to_id = _build_path_to_id_map_for_server(primary_server)
        _save_mapping_to_db(path_to_id, primary_server)
        mapping = path_to_id

    # Invert the mapping: path -> id becomes id -> path
    id_to_path = {v: k for k, v in mapping.items()}

    # Get paths for requested IDs
    result = {}
    for track_id in primary_item_ids:
        track_id_str = str(track_id)
        if track_id_str in id_to_path:
            result[track_id_str] = id_to_path[track_id_str]

    return result


def _resolve_ids_for_server(normalized_paths: List[str], server_type: str) -> List[str]:
    """
    Resolve normalized file paths to track IDs for a specific server.
    Returns a list of track IDs in the same order as the input paths.
    Missing tracks are excluded.
    """
    # Load mapping from database
    mapping = _load_mapping_from_db(server_type)

    # If no mapping exists, build it (lazy loading)
    if not mapping:
        logger.info(f"No mapping found for {server_type}, building cache...")
        path_to_id = _build_path_to_id_map_for_server(server_type)
        _save_mapping_to_db(path_to_id, server_type)
        mapping = path_to_id

    # Resolve paths to IDs
    resolved_ids = []
    missing_count = 0
    for path in normalized_paths:
        if path in mapping:
            resolved_ids.append(mapping[path])
        else:
            missing_count += 1

    if missing_count > 0:
        logger.warning(f"Could not resolve {missing_count}/{len(normalized_paths)} paths for {server_type}")

    return resolved_ids


def sync_playlist_to_secondary_servers(
    playlist_name: str,
    primary_item_ids: List[str],
    sync_enabled: bool = True
) -> Dict[str, dict]:
    """
    Sync a playlist from the primary server to all secondary servers.

    Args:
        playlist_name: Name of the playlist to create
        primary_item_ids: List of track IDs from the primary server
        sync_enabled: If False, skip syncing (respects user toggle)

    Returns:
        Dict mapping server_type -> result dict with 'success', 'tracks_synced', 'error'
    """
    results = {}

    # Check if sync is enabled
    if not sync_enabled or not is_sync_enabled():
        logger.debug("Playlist sync is disabled or not configured")
        return results

    if not primary_item_ids:
        logger.warning("No track IDs provided for playlist sync")
        return results

    secondary_servers = _get_secondary_servers()
    if not secondary_servers:
        logger.debug("No secondary servers configured")
        return results

    logger.info(f"Syncing playlist '{playlist_name}' with {len(primary_item_ids)} tracks to {secondary_servers}")

    # Get paths for primary server track IDs
    id_to_path = _get_paths_for_primary_ids(primary_item_ids)

    if not id_to_path:
        logger.error("Could not resolve any paths for primary server track IDs")
        return {s: {'success': False, 'tracks_synced': 0, 'error': 'No paths resolved'} for s in secondary_servers}

    # Maintain order: get paths in the same order as primary_item_ids
    ordered_paths = []
    for track_id in primary_item_ids:
        track_id_str = str(track_id)
        if track_id_str in id_to_path:
            ordered_paths.append(id_to_path[track_id_str])

    logger.info(f"Resolved {len(ordered_paths)}/{len(primary_item_ids)} paths from primary server")

    # Sync to each secondary server
    for server_type in secondary_servers:
        try:
            # Resolve paths to IDs for this server
            server_ids = _resolve_ids_for_server(ordered_paths, server_type)

            if not server_ids:
                results[server_type] = {
                    'success': False,
                    'tracks_synced': 0,
                    'error': 'No tracks could be resolved'
                }
                continue

            # Create playlist on this server
            create_func = SERVER_CREATE_PLAYLIST.get(server_type)
            if create_func:
                create_func(playlist_name, server_ids)
                results[server_type] = {
                    'success': True,
                    'tracks_synced': len(server_ids),
                    'error': None
                }
                logger.info(f"Created playlist '{playlist_name}' on {server_type} with {len(server_ids)} tracks")
            else:
                results[server_type] = {
                    'success': False,
                    'tracks_synced': 0,
                    'error': f'No create function for {server_type}'
                }

        except Exception as e:
            logger.error(f"Failed to sync playlist to {server_type}: {e}", exc_info=True)
            results[server_type] = {
                'success': False,
                'tracks_synced': 0,
                'error': str(e)
            }

    return results


def delete_playlist_from_all_servers(playlist_name: str) -> Dict[str, bool]:
    """
    Delete a playlist from primary and all secondary servers.

    Args:
        playlist_name: Name of the playlist to delete

    Returns:
        Dict mapping server_type -> success boolean
    """
    from tasks.mediaserver_jellyfin import (
        get_playlist_by_name as jellyfin_get_playlist,
        delete_playlist as jellyfin_delete_playlist,
    )
    from tasks.mediaserver_navidrome import (
        get_playlist_by_name as navidrome_get_playlist,
        delete_playlist as navidrome_delete_playlist,
    )
    from tasks.mediaserver_lyrion import (
        get_playlist_by_name as lyrion_get_playlist,
        delete_playlist as lyrion_delete_playlist,
    )
    from tasks.mediaserver_mpd import (
        get_playlist_by_name as mpd_get_playlist,
        delete_playlist as mpd_delete_playlist,
    )
    from tasks.mediaserver_emby import (
        get_playlist_by_name as emby_get_playlist,
        delete_playlist as emby_delete_playlist,
    )
    from tasks.mediaserver_plex import (
        get_playlist_by_name as plex_get_playlist,
        delete_playlist as plex_delete_playlist,
    )

    get_playlist_funcs = {
        'jellyfin': jellyfin_get_playlist,
        'navidrome': navidrome_get_playlist,
        'lyrion': lyrion_get_playlist,
        'mpd': mpd_get_playlist,
        'emby': emby_get_playlist,
        'plex': plex_get_playlist,
    }

    delete_funcs = {
        'jellyfin': jellyfin_delete_playlist,
        'navidrome': navidrome_delete_playlist,
        'lyrion': lyrion_delete_playlist,
        'mpd': mpd_delete_playlist,
        'emby': emby_delete_playlist,
        'plex': plex_delete_playlist,
    }

    results = {}

    # Get all servers to delete from (primary + secondary)
    all_servers = [config.PLAYLIST_PRIMARY_SERVER.lower()] + _get_secondary_servers()
    # Remove duplicates while preserving order
    seen = set()
    unique_servers = []
    for s in all_servers:
        if s not in seen:
            seen.add(s)
            unique_servers.append(s)

    for server_type in unique_servers:
        try:
            get_func = get_playlist_funcs.get(server_type)
            delete_func = delete_funcs.get(server_type)

            if not get_func or not delete_func:
                results[server_type] = False
                continue

            playlist = get_func(playlist_name)
            if playlist:
                playlist_id = playlist.get('Id') or playlist.get('id')
                if playlist_id:
                    success = delete_func(playlist_id)
                    results[server_type] = success if success is not None else True
                    if results[server_type]:
                        logger.info(f"Deleted playlist '{playlist_name}' from {server_type}")
                else:
                    results[server_type] = False
            else:
                # Playlist doesn't exist, consider it a success
                results[server_type] = True
                logger.debug(f"Playlist '{playlist_name}' not found on {server_type}")

        except Exception as e:
            logger.error(f"Failed to delete playlist from {server_type}: {e}", exc_info=True)
            results[server_type] = False

    return results
