# app_playlist_sync.py
"""
Flask Blueprint for Multi-Server Playlist Sync API endpoints.

Provides endpoints for:
- Checking sync configuration status
- Refreshing track mapping cache
- Viewing mapping statistics
"""

from flask import Blueprint, jsonify, request
import logging

from tasks.playlist_sync import (
    get_sync_status,
    is_sync_enabled,
    refresh_mapping_for_server,
    refresh_all_secondary_mappings,
    get_mapping_stats,
)

logger = logging.getLogger(__name__)

# Create a Blueprint for playlist sync related routes
playlist_sync_bp = Blueprint('playlist_sync_bp', __name__, template_folder='templates')


@playlist_sync_bp.route('/api/playlist-sync/status', methods=['GET'])
def get_status():
    """
    Get the current playlist sync configuration status.
    ---
    tags:
      - Playlist Sync
    responses:
      200:
        description: Current sync configuration
        content:
          application/json:
            schema:
              type: object
              properties:
                enabled:
                  type: boolean
                  description: Whether sync is globally enabled
                primary_server:
                  type: string
                  description: The primary server type
                secondary_servers:
                  type: array
                  items:
                    type: string
                  description: List of secondary server types
                sync_active:
                  type: boolean
                  description: Whether sync is actually active (enabled + has secondary servers)
    """
    try:
        status = get_sync_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"Failed to get sync status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@playlist_sync_bp.route('/api/playlist-sync/stats', methods=['GET'])
def get_stats():
    """
    Get statistics about the track mapping cache.
    ---
    tags:
      - Playlist Sync
    responses:
      200:
        description: Mapping cache statistics
        content:
          application/json:
            schema:
              type: object
              properties:
                total_paths:
                  type: integer
                  description: Total number of file paths in the mapping
                servers:
                  type: object
                  description: Count of mapped tracks per server
                last_updated:
                  type: string
                  description: ISO timestamp of last mapping update
    """
    try:
        stats = get_mapping_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Failed to get mapping stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@playlist_sync_bp.route('/api/playlist-sync/refresh', methods=['POST'])
def refresh_mappings():
    """
    Refresh the track mapping cache for all secondary servers.
    ---
    tags:
      - Playlist Sync
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              server:
                type: string
                description: Optional - specific server to refresh (e.g., 'jellyfin'). If not provided, refreshes all secondary servers.
    responses:
      200:
        description: Refresh results
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                results:
                  type: object
                  description: Results per server with total_songs and mapped_count
    """
    try:
        data = request.get_json() or {}
        server = data.get('server')

        if server:
            # Refresh specific server
            total, mapped = refresh_mapping_for_server(server.lower())
            results = {server: {'total_songs': total, 'mapped_count': mapped}}
        else:
            # Refresh all secondary servers
            raw_results = refresh_all_secondary_mappings()
            results = {
                server: {'total_songs': total, 'mapped_count': mapped}
                for server, (total, mapped) in raw_results.items()
            }

        return jsonify({
            'success': True,
            'results': results
        })

    except Exception as e:
        logger.error(f"Failed to refresh mappings: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@playlist_sync_bp.route('/api/playlist-sync/enabled', methods=['GET'])
def check_enabled():
    """
    Quick check if playlist sync is enabled and active.
    ---
    tags:
      - Playlist Sync
    responses:
      200:
        description: Sync enabled status
        content:
          application/json:
            schema:
              type: object
              properties:
                enabled:
                  type: boolean
    """
    return jsonify({'enabled': is_sync_enabled()})
