# tasks/mediaserver_plex.py

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import os
import time
import config
from requests.exceptions import ChunkedEncodingError, ConnectionError, Timeout

logger = logging.getLogger(__name__)

# Timeout tuple: (connect_timeout, read_timeout)
# Short connect timeout, very long read timeout for large FLAC files
REQUESTS_TIMEOUT = (30, 600)  # 30s connect, 10min read

# Create a session with automatic retries for transient failures
def _create_download_session():
    """Creates a requests session with retry strategy for downloads."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=1,  # Single connection per download
        pool_maxsize=1
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ##############################################################################
# PLEX IMPLEMENTATION
# ##############################################################################

# Standard Plex headers for all requests
def _get_plex_headers():
    """Returns standard Plex headers for API requests."""
    return {
        "X-Plex-Token": config.PLEX_TOKEN,
        "Accept": "application/json",
        "X-Plex-Client-Identifier": "audiomuse-ai",
        "X-Plex-Product": "AudioMuse-AI",
        "X-Plex-Version": config.APP_VERSION,
    }


def _get_target_library_ids():
    """
    Parses config for library names and returns their section keys for filtering.
    Uses case-insensitive matching against the server's music libraries.
    """
    library_names_str = getattr(config, 'MUSIC_LIBRARIES', '')

    if not library_names_str.strip():
        return None

    target_names_lower = {name.strip().lower() for name in library_names_str.split(',') if name.strip()}

    # Fetch all library sections from Plex
    url = f"{config.PLEX_URL}/library/sections"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        sections = data.get('MediaContainer', {}).get('Directory', [])

        # Build a case-insensitive map for music libraries only
        # In Plex, music libraries have type="artist"
        library_map = {
            section['title'].lower(): {'name': section['title'], 'key': section['key']}
            for section in sections
            if section.get('type') == 'artist'
        }

        available_music_libraries = [lib['name'] for lib in library_map.values()]
        logger.info(f"Available Plex music libraries found: {available_music_libraries}")

        # Match user's config against the map
        found_libraries = []
        unfound_names = []
        for target_name in target_names_lower:
            if target_name in library_map:
                found_libraries.append(library_map[target_name])
            else:
                unfound_names.append(target_name)

        if unfound_names:
            logger.warning(f"Plex config specified library names that were not found: {list(unfound_names)}")

        if not found_libraries:
            logger.warning(f"No matching music libraries found for configured names: {list(target_names_lower)}. No albums will be analyzed.")
            return set()

        music_library_keys = {lib['key'] for lib in found_libraries}
        found_names_original_case = [lib['name'] for lib in found_libraries]

        logger.info(f"Filtering analysis to {len(music_library_keys)} Plex libraries: {found_names_original_case}")
        return music_library_keys

    except Exception as e:
        logger.error(f"Failed to fetch or parse Plex library sections: {e}", exc_info=True)
        return set()


def _get_all_music_library_keys():
    """
    Returns all music library section keys from Plex.
    Used when no specific libraries are configured.
    """
    url = f"{config.PLEX_URL}/library/sections"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        sections = data.get('MediaContainer', {}).get('Directory', [])

        # Filter for music libraries (type="artist")
        music_keys = [section['key'] for section in sections if section.get('type') == 'artist']
        logger.info(f"Found {len(music_keys)} music libraries in Plex")
        return music_keys

    except Exception as e:
        logger.error(f"Failed to fetch Plex library sections: {e}", exc_info=True)
        return []


def _select_best_artist(item, title="Unknown"):
    """
    Selects the best artist field from Plex item, prioritizing track artists over album artists.
    In Plex:
    - originalTitle = track artist (when different from album artist)
    - grandparentTitle = album artist
    Returns tuple: (artist_name, artist_id)
    """
    # Priority: originalTitle (track artist) > grandparentTitle (album artist) > fallback
    if item.get('originalTitle'):
        track_artist = item['originalTitle']
        artist_id = item.get('grandparentRatingKey')  # Use album artist's ID as fallback
        used_field = 'originalTitle'
    elif item.get('grandparentTitle'):
        track_artist = item['grandparentTitle']
        artist_id = item.get('grandparentRatingKey')
        used_field = 'grandparentTitle'
    else:
        track_artist = 'Unknown Artist'
        artist_id = None
        used_field = 'fallback'

    return track_artist, artist_id


def _convert_plex_track_to_common_format(plex_item):
    """
    Converts a Plex track item to the common format used by AudioMuse-AI.
    Includes star rating conversion from 0-10 to 0-5 scale.
    """
    title = plex_item.get('title', 'Unknown')
    artist_name, artist_id = _select_best_artist(plex_item, title)

    # Extract file path from Media structure
    file_path = ''
    media = plex_item.get('Media', [])
    if media and len(media) > 0:
        parts = media[0].get('Part', [])
        if parts and len(parts) > 0:
            file_path = parts[0].get('file', '')

    # Convert user rating from 0-10 to 0-5 scale
    user_rating = plex_item.get('userRating')
    rating = None
    if user_rating is not None:
        rating = float(user_rating) / 2.0  # Convert 0-10 to 0-5

    return {
        'Id': str(plex_item.get('ratingKey', '')),
        'Name': title,
        'AlbumArtist': plex_item.get('grandparentTitle', 'Unknown Artist'),
        'SongArtist': plex_item.get('originalTitle') or plex_item.get('grandparentTitle', 'Unknown Artist'),
        'Album': plex_item.get('parentTitle', 'Unknown Album'),
        'ArtistId': str(artist_id) if artist_id else None,
        'AlbumId': str(plex_item.get('parentRatingKey', '')),
        'Path': file_path,
        'Rating': rating,
        'DateCreated': plex_item.get('addedAt'),  # Unix timestamp
        # Store the part key for downloading
        '_plex_part_key': media[0]['Part'][0].get('key') if media and media[0].get('Part') else None,
    }


# --- ADMIN/GLOBAL PLEX FUNCTIONS ---
def get_recent_albums(limit):
    """
    Fetches a list of the most recently added albums from Plex.
    If MUSIC_LIBRARIES is set, it will only return albums from those libraries.
    """
    target_library_keys = _get_target_library_ids()

    # Case 1: Config is set, but no matching libraries were found. Scan nothing.
    if isinstance(target_library_keys, set) and not target_library_keys:
        logger.warning("Library filtering is active, but no matching libraries were found on the server. Returning no albums.")
        return []

    all_albums = []
    fetch_all = (limit == 0)

    # Determine which library keys to scan
    if target_library_keys is None:
        # No config set, scan all music libraries
        library_keys = _get_all_music_library_keys()
        logger.info("Scanning all Plex music libraries for recent albums.")
    else:
        library_keys = list(target_library_keys)
        logger.info(f"Scanning {len(library_keys)} specific Plex libraries for recent albums.")

    for section_key in library_keys:
        start_index = 0
        page_size = 500

        while True:
            # Plex uses type=9 for albums, sorted by addedAt descending
            url = f"{config.PLEX_URL}/library/sections/{section_key}/all"
            params = {
                "type": 9,  # Albums
                "sort": "addedAt:desc",
            }
            headers = _get_plex_headers()
            headers["X-Plex-Container-Start"] = str(start_index)
            headers["X-Plex-Container-Size"] = str(page_size)

            try:
                r = requests.get(url, headers=headers, params=params, timeout=REQUESTS_TIMEOUT)
                r.raise_for_status()
                data = r.json()

                albums_on_page = data.get('MediaContainer', {}).get('Metadata', [])

                if not albums_on_page:
                    break

                # Convert Plex album format to common format
                for album in albums_on_page:
                    all_albums.append({
                        'Id': str(album.get('ratingKey', '')),
                        'Name': album.get('title', 'Unknown Album'),
                        'AlbumArtist': album.get('parentTitle', 'Unknown Artist'),
                        'DateCreated': album.get('addedAt'),
                        'Type': 'MusicAlbum',
                        '_plex_library_key': section_key,
                    })

                start_index += len(albums_on_page)

                if len(albums_on_page) < page_size:
                    break

            except Exception as e:
                logger.error(f"Plex get_recent_albums failed for library {section_key}: {e}", exc_info=True)
                break

    # Sort by DateCreated if we fetched from multiple libraries
    if len(library_keys) > 1:
        all_albums.sort(key=lambda x: x.get('DateCreated', 0) or 0, reverse=True)

    # Apply the final limit if one was specified
    if not fetch_all:
        return all_albums[:limit]

    return all_albums


def get_tracks_from_album(album_id):
    """Fetches all audio tracks for a given album ratingKey from Plex."""
    # Handle pseudo-album IDs for standalone tracks
    if str(album_id).startswith('standalone_'):
        logger.debug(f"Skipping tracks fetch for pseudo-album: {album_id}")
        return []

    url = f"{config.PLEX_URL}/library/metadata/{album_id}/children"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        tracks = data.get('MediaContainer', {}).get('Metadata', [])

        # Convert to common format
        result = []
        for track in tracks:
            if track.get('type') == 'track':
                result.append(_convert_plex_track_to_common_format(track))

        return result
    except Exception as e:
        logger.error(f"Plex get_tracks_from_album failed for album {album_id}: {e}", exc_info=True)
        return []


def _map_path_for_direct_access(plex_path):
    """
    Maps a Plex file path to the container's mounted path.
    Uses DIRECT_FILE_PATH_MAPPING config (format: "plex_prefix:container_prefix").
    Returns the mapped path, or the original path if no mapping is configured.
    """
    mapping = getattr(config, 'DIRECT_FILE_PATH_MAPPING', '')
    if not mapping or ':' not in mapping:
        return plex_path

    # Parse mapping (format: "plex_prefix:container_prefix")
    parts = mapping.split(':', 1)
    if len(parts) != 2:
        return plex_path

    plex_prefix, container_prefix = parts
    if plex_path.startswith(plex_prefix):
        return plex_path.replace(plex_prefix, container_prefix, 1)

    return plex_path


def download_track(temp_dir, item):
    """
    Gets a track file for analysis. Tries direct file access first (if enabled),
    falls back to HTTP download if direct access fails or is disabled.
    """
    track_name = item.get('Name', 'Unknown')
    track_id = item.get('Id') or item.get('ratingKey')
    file_path = item.get('Path', '')

    # --- Try Direct File Access First (if enabled) ---
    if getattr(config, 'ENABLE_DIRECT_FILE_ACCESS', False) and file_path:
        mapped_path = _map_path_for_direct_access(file_path)
        if os.path.isfile(mapped_path):
            logger.info(f"Direct file access: '{track_name}' at '{mapped_path}'")
            return mapped_path
        else:
            logger.debug(f"Direct file access failed for '{track_name}': '{mapped_path}' not found, falling back to HTTP")

    # --- HTTP Download Fallback ---
    # Get retry settings from config
    max_retries = getattr(config, 'DOWNLOAD_RETRY_ATTEMPTS', 3)
    base_delay = getattr(config, 'DOWNLOAD_RETRY_BASE_DELAY', 2.0)

    for attempt in range(max_retries + 1):
        try:
            # Get file extension from path
            file_extension = os.path.splitext(file_path)[1] or '.tmp'

            # Use the part key if available, otherwise fetch metadata to get it
            part_key = item.get('_plex_part_key')
            if not part_key:
                # Fetch track metadata to get download URL
                meta_url = f"{config.PLEX_URL}/library/metadata/{track_id}"
                r = requests.get(meta_url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
                r.raise_for_status()
                data = r.json()

                track_data = data.get('MediaContainer', {}).get('Metadata', [{}])[0]
                media = track_data.get('Media', [])
                if media and len(media) > 0:
                    parts = media[0].get('Part', [])
                    if parts and len(parts) > 0:
                        part_key = parts[0].get('key')

            if not part_key:
                logger.error(f"Could not find download URL for track {track_name}")
                return None

            # Download the file
            download_url = f"{config.PLEX_URL}{part_key}"
            local_filename = os.path.join(temp_dir, f"{track_id}{file_extension}")

            # Use a dedicated session with connection pooling for more reliable downloads
            session = _create_download_session()
            try:
                headers = _get_plex_headers()
                headers['Connection'] = 'keep-alive'  # Maintain connection for large files

                with session.get(download_url, headers=headers, stream=True, timeout=REQUESTS_TIMEOUT) as r:
                    r.raise_for_status()

                    # Get expected content length for verification
                    expected_length = r.headers.get('Content-Length')
                    bytes_written = 0

                    with open(local_filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):  # 8KB chunks
                            if chunk:
                                f.write(chunk)
                                bytes_written += len(chunk)

                    # Verify download completeness using Content-Length
                    if expected_length is not None:
                        expected_length = int(expected_length)
                        if bytes_written < expected_length:
                            # Incomplete download - raise to trigger retry
                            raise ChunkedEncodingError(
                                f"Incomplete download: {bytes_written} bytes written, {expected_length} expected"
                            )
            finally:
                session.close()

            logger.info(f"Downloaded '{track_name}' to '{local_filename}' ({bytes_written} bytes)")
            return local_filename

        except (ChunkedEncodingError, ConnectionError, Timeout) as e:
            # These are retryable network errors
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8 seconds
                logger.warning(f"Download failed for '{track_name}' (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.1f}s...")
                time.sleep(delay)
                # Clean up partial file if it exists
                local_filename = os.path.join(temp_dir, f"{track_id}{file_extension}")
                if os.path.exists(local_filename):
                    try:
                        os.remove(local_filename)
                    except:
                        pass
            else:
                logger.error(f"Failed to download track '{track_name}' after {max_retries + 1} attempts: {e}", exc_info=True)
                return None
        except Exception as e:
            # Non-retryable errors
            logger.error(f"Failed to download track '{track_name}': {e}", exc_info=True)
            return None

    return None


def get_all_songs():
    """Fetches all songs from Plex music libraries."""
    target_library_keys = _get_target_library_ids()

    if isinstance(target_library_keys, set) and not target_library_keys:
        logger.warning("Library filtering is active, but no matching libraries were found.")
        return []

    all_tracks = []

    # Determine which library keys to scan
    if target_library_keys is None:
        library_keys = _get_all_music_library_keys()
    else:
        library_keys = list(target_library_keys)

    for section_key in library_keys:
        start_index = 0
        page_size = 1000

        while True:
            # Use allLeaves to get all tracks in the library
            url = f"{config.PLEX_URL}/library/sections/{section_key}/allLeaves"
            params = {"type": 10}  # Tracks
            headers = _get_plex_headers()
            headers["X-Plex-Container-Start"] = str(start_index)
            headers["X-Plex-Container-Size"] = str(page_size)

            try:
                r = requests.get(url, headers=headers, params=params, timeout=REQUESTS_TIMEOUT)
                r.raise_for_status()
                data = r.json()

                tracks_on_page = data.get('MediaContainer', {}).get('Metadata', [])

                if not tracks_on_page:
                    break

                for track in tracks_on_page:
                    all_tracks.append(_convert_plex_track_to_common_format(track))

                start_index += len(tracks_on_page)

                if len(tracks_on_page) < page_size:
                    break

            except Exception as e:
                logger.error(f"Plex get_all_songs failed for library {section_key}: {e}", exc_info=True)
                break

    return all_tracks


def get_all_playlists():
    """Fetches all audio playlists from Plex."""
    url = f"{config.PLEX_URL}/playlists"
    params = {
        "playlistType": "audio",
        "smart": "0"  # Only regular playlists, not smart playlists
    }
    try:
        r = requests.get(url, headers=_get_plex_headers(), params=params, timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        playlists = data.get('MediaContainer', {}).get('Metadata', [])

        # Convert to common format
        result = []
        for playlist in playlists:
            result.append({
                'Id': str(playlist.get('ratingKey', '')),
                'Name': playlist.get('title', ''),
                'Type': 'Playlist',
            })

        return result
    except Exception as e:
        logger.error(f"Plex get_all_playlists failed: {e}", exc_info=True)
        return []


def get_playlist_by_name(playlist_name):
    """Finds a Plex playlist by its exact name."""
    playlists = get_all_playlists()
    for playlist in playlists:
        if playlist.get('Name') == playlist_name:
            return playlist
    return None


def _get_server_machine_identifier():
    """Gets the Plex server machine identifier needed for playlist creation."""
    url = f"{config.PLEX_URL}/"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data.get('MediaContainer', {}).get('machineIdentifier')
    except Exception as e:
        logger.error(f"Failed to get Plex server machine identifier: {e}", exc_info=True)
        return None


def _get_library_section_uuid(section_key):
    """Gets the library section UUID needed for URI format."""
    url = f"{config.PLEX_URL}/library/sections/{section_key}"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data.get('MediaContainer', {}).get('librarySectionUUID')
    except Exception as e:
        logger.error(f"Failed to get library section UUID: {e}", exc_info=True)
        return None


def create_playlist(base_name, item_ids):
    """
    Creates a new playlist on Plex.
    Plex uses URI format for adding items, not direct IDs.
    """
    if not item_ids:
        logger.warning(f"Cannot create playlist '{base_name}' with no items")
        return

    machine_id = _get_server_machine_identifier()
    if not machine_id:
        logger.error("Failed to create playlist: could not get server machine identifier")
        return

    # Build the URI string for all tracks
    # Format: server://{machineIdentifier}/com.plexapp.plugins.library/library/metadata/{ratingKey}
    uris = []
    for item_id in item_ids:
        uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{item_id}"
        uris.append(uri)

    uri_string = ",".join(uris)

    url = f"{config.PLEX_URL}/playlists"
    params = {
        "type": "audio",
        "title": base_name,
        "smart": "0",
        "uri": uri_string,
    }

    try:
        r = requests.post(url, headers=_get_plex_headers(), params=params, timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        logger.info(f"Created Plex playlist '{base_name}'")
    except Exception as e:
        logger.error(f"Exception creating Plex playlist '{base_name}': {e}", exc_info=True)


def delete_playlist(playlist_id):
    """Deletes a playlist on Plex."""
    url = f"{config.PLEX_URL}/playlists/{playlist_id}"
    try:
        r = requests.delete(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        logger.info(f"Deleted Plex playlist {playlist_id}")
        return True
    except Exception as e:
        logger.error(f"Exception deleting Plex playlist ID {playlist_id}: {e}", exc_info=True)
        return False


# --- USER-SPECIFIC PLEX FUNCTIONS (Admin-only for now) ---
def get_top_played_songs(limit, user_creds=None):
    """
    Fetches the top N most played songs from Plex.
    Plex uses viewCount for play count, sorted descending.
    """
    # For admin-only mode, we ignore user_creds
    target_library_keys = _get_target_library_ids()

    if isinstance(target_library_keys, set) and not target_library_keys:
        return []

    all_tracks = []

    if target_library_keys is None:
        library_keys = _get_all_music_library_keys()
    else:
        library_keys = list(target_library_keys)

    for section_key in library_keys:
        url = f"{config.PLEX_URL}/library/sections/{section_key}/allLeaves"
        params = {
            "type": 10,  # Tracks
            "sort": "viewCount:desc",
        }
        headers = _get_plex_headers()
        headers["X-Plex-Container-Size"] = str(limit)

        try:
            r = requests.get(url, headers=headers, params=params, timeout=REQUESTS_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            tracks = data.get('MediaContainer', {}).get('Metadata', [])

            for track in tracks:
                # Only include tracks that have been played
                if track.get('viewCount', 0) > 0:
                    converted = _convert_plex_track_to_common_format(track)
                    converted['PlayCount'] = track.get('viewCount', 0)
                    all_tracks.append(converted)

        except Exception as e:
            logger.error(f"Plex get_top_played_songs failed for library {section_key}: {e}", exc_info=True)

    # Sort by play count and limit
    all_tracks.sort(key=lambda x: x.get('PlayCount', 0), reverse=True)
    return all_tracks[:limit]


def get_last_played_time(item_id, user_creds=None):
    """
    Fetches the last played time for a specific track from Plex.
    Returns the lastViewedAt timestamp (Unix timestamp).
    """
    # For admin-only mode, we ignore user_creds
    url = f"{config.PLEX_URL}/library/metadata/{item_id}"
    try:
        r = requests.get(url, headers=_get_plex_headers(), timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        track = data.get('MediaContainer', {}).get('Metadata', [{}])[0]
        last_viewed = track.get('lastViewedAt')

        # Convert Unix timestamp to ISO format if present
        if last_viewed:
            from datetime import datetime
            return datetime.utcfromtimestamp(last_viewed).isoformat() + "Z"
        return None
    except Exception as e:
        logger.error(f"Plex get_last_played_time failed for item {item_id}: {e}", exc_info=True)
        return None


def create_instant_playlist(playlist_name, item_ids, user_creds=None, add_instant_suffix=True):
    """
    Creates an instant playlist on Plex.
    For admin-only mode, user_creds is ignored.
    """
    final_playlist_name = f"{playlist_name.strip()}_instant" if add_instant_suffix else playlist_name.strip()

    if not item_ids:
        logger.warning(f"Cannot create instant playlist '{final_playlist_name}' with no items")
        return None

    machine_id = _get_server_machine_identifier()
    if not machine_id:
        logger.error("Failed to create instant playlist: could not get server machine identifier")
        return None

    # Build the URI string for all tracks
    uris = []
    for item_id in item_ids:
        uri = f"server://{machine_id}/com.plexapp.plugins.library/library/metadata/{item_id}"
        uris.append(uri)

    uri_string = ",".join(uris)

    url = f"{config.PLEX_URL}/playlists"
    params = {
        "type": "audio",
        "title": final_playlist_name,
        "smart": "0",
        "uri": uri_string,
    }

    try:
        r = requests.post(url, headers=_get_plex_headers(), params=params, timeout=REQUESTS_TIMEOUT)
        r.raise_for_status()
        data = r.json()

        # Return playlist info
        playlist = data.get('MediaContainer', {}).get('Metadata', [{}])[0]
        logger.info(f"Created Plex instant playlist '{final_playlist_name}'")
        return {
            'Id': str(playlist.get('ratingKey', '')),
            'Name': final_playlist_name,
        }
    except Exception as e:
        logger.error(f"Exception creating Plex instant playlist '{final_playlist_name}': {e}", exc_info=True)
        return None


def _get_recent_standalone_tracks(limit, target_library_keys):
    """
    Gets recent standalone tracks that might not be in proper albums.
    Useful for music discovery on servers with incomplete metadata.
    """
    all_tracks = []

    if target_library_keys is None:
        library_keys = _get_all_music_library_keys()
    elif isinstance(target_library_keys, set) and not target_library_keys:
        return []
    else:
        library_keys = list(target_library_keys)

    for section_key in library_keys:
        url = f"{config.PLEX_URL}/library/sections/{section_key}/allLeaves"
        params = {
            "type": 10,  # Tracks
            "sort": "addedAt:desc",
        }
        headers = _get_plex_headers()
        headers["X-Plex-Container-Size"] = str(limit)

        try:
            r = requests.get(url, headers=headers, params=params, timeout=REQUESTS_TIMEOUT)
            r.raise_for_status()
            data = r.json()

            tracks = data.get('MediaContainer', {}).get('Metadata', [])

            for track in tracks:
                converted = _convert_plex_track_to_common_format(track)
                all_tracks.append(converted)

        except Exception as e:
            logger.error(f"Plex _get_recent_standalone_tracks failed for library {section_key}: {e}", exc_info=True)

    # Sort by date added and limit
    all_tracks.sort(key=lambda x: x.get('DateCreated', 0) or 0, reverse=True)
    return all_tracks[:limit]


def get_recent_music_items(limit):
    """
    Gets both recent albums AND recent standalone tracks for comprehensive music discovery.
    This ensures no music is missed during analysis, even if metadata is incomplete.
    Returns a list combining album objects and standalone track objects.
    """
    target_library_keys = _get_target_library_ids()

    # Get recent albums (existing functionality)
    albums = get_recent_albums(limit)

    # Get recent standalone tracks
    standalone_limit = min(limit, 100) if limit > 0 else 100
    standalone_tracks = _get_recent_standalone_tracks(standalone_limit, target_library_keys)

    # Create pseudo-albums for standalone tracks to maintain compatibility
    pseudo_albums = []
    for track in standalone_tracks:
        pseudo_album = {
            'Id': f"standalone_{track['Id']}",
            'Name': f"Standalone: {track.get('Name', 'Unknown')}",
            'Type': 'PseudoAlbum',
            'StandaloneTrack': track,
            'DateCreated': track.get('DateCreated', ''),
            'AlbumArtist': track.get('AlbumArtist', 'Unknown Artist')
        }
        pseudo_albums.append(pseudo_album)

    # Combine albums and pseudo-albums
    combined = albums + pseudo_albums

    # Sort by DateCreated
    combined.sort(key=lambda x: x.get('DateCreated', 0) or 0, reverse=True)

    # Apply limit if specified
    if limit > 0:
        return combined[:limit]

    return combined
