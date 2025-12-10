# AudioMuse-AI Improvement Backlog

## Scoring Formula

```
Priority = (Impact × 0.30) + (Effort × 0.25) + (Risk × 0.20) + (Urgency × 0.15) + (Confidence × 0.10)
```

- All scores 1-10
- Effort: 10 = minimal effort, 1 = major effort
- Risk: 10 = very safe, 1 = high risk

---

## High Priority (Score > 7.0)

### 1. WebSocket for Real-time Task Updates
**Score: 7.8**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 9 | Eliminates polling, improves UX |
| Effort | 7 | Flask-SocketIO straightforward |
| Risk | 8 | Well-established pattern |
| Urgency | 6 | Polling works but wasteful |
| Confidence | 9 | Standard web pattern |

**Description**: Replace polling for task status with WebSocket push notifications.

**Implementation**:
1. Add Flask-SocketIO dependency
2. Create socket events for task updates
3. Emit updates from `save_task_status()`
4. Update frontend JavaScript

---

### 2. Database Connection Pooling
**Score: 7.5**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 8 | Reduces connection overhead |
| Effort | 7 | psycopg2.pool or SQLAlchemy |
| Risk | 7 | Need careful transaction handling |
| Urgency | 7 | Current approach creates many connections |
| Confidence | 9 | Standard PostgreSQL pattern |

**Description**: Use connection pooling instead of per-request connections.

**Implementation**:
1. Replace `psycopg2.connect()` with pool
2. Update `get_db()` to use pool
3. Configure pool size based on workers
4. Add health check for pool status

---

### 3. API Authentication
**Score: 7.3**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 8 | Required for any public deployment |
| Effort | 6 | Flask-Login or API keys |
| Risk | 7 | Standard security pattern |
| Urgency | 7 | Currently private-network only |
| Confidence | 9 | Well-documented approaches |

**Description**: Add optional API authentication for public deployments.

**Implementation**:
1. Add `AUTH_ENABLED` config option
2. Implement API key authentication
3. Add key management endpoints
4. Update documentation

---

## Medium Priority (Score 5.0-7.0)

### 4. Incremental Index Updates
**Score: 6.8**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 7 | Faster incremental analysis |
| Effort | 5 | Voyager supports add_items() |
| Risk | 6 | Index consistency concerns |
| Urgency | 6 | Full rebuilds work but slow |
| Confidence | 7 | Voyager API supports it |

**Description**: Update Voyager index incrementally instead of full rebuilds.

---

### 5. Playlist Preview/Playback
**Score: 6.5**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 8 | Better UX for playlist building |
| Effort | 5 | Media server streaming integration |
| Risk | 7 | Standard media playback |
| Urgency | 5 | Not blocking core function |
| Confidence | 7 | Depends on media server API |

**Description**: Add in-browser preview playback of tracks and playlists.

---

### 6. Batch Analysis Resumption
**Score: 6.3**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 7 | Resilience to failures |
| Effort | 5 | Track progress per album |
| Risk | 7 | Need careful state management |
| Urgency | 6 | Large runs can fail mid-way |
| Confidence | 8 | Database state tracking |

**Description**: Resume interrupted analysis from last successful album.

---

### 7. Album Cover Art in UI
**Score: 6.0**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 6 | Visual improvement |
| Effort | 8 | Fetch from media server |
| Risk | 9 | Read-only, low risk |
| Urgency | 4 | Nice to have |
| Confidence | 9 | Standard media server API |

**Description**: Display album artwork in similarity results and playlists.

---

### 8. Export/Import Library Data
**Score: 5.8**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 6 | Backup, migration support |
| Effort | 6 | JSON/CSV export |
| Risk | 8 | Read operations only |
| Urgency | 5 | Useful for advanced users |
| Confidence | 9 | Standard data export |

**Description**: Export embeddings, playlists, and configuration for backup/migration.

---

### 9. Multi-language UI
**Score: 5.5**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 6 | Broader audience |
| Effort | 4 | i18n framework integration |
| Risk | 8 | No functional change |
| Urgency | 4 | English-only currently |
| Confidence | 8 | Flask-Babel available |

**Description**: Add internationalization support for UI text.

---

## Low Priority (Score < 5.0)

### 10. Dark Mode Theme
**Score: 4.8**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 5 | User preference |
| Effort | 7 | CSS variables |
| Risk | 9 | No functional change |
| Urgency | 3 | Cosmetic |
| Confidence | 9 | Standard CSS |

**Description**: Add dark mode toggle (partially implemented in current branch).

**Status**: In progress on `feat/playlist-builder` branch

---

### 11. MusicBrainz Integration
**Score: 4.5**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 5 | Better metadata |
| Effort | 4 | API integration |
| Risk | 6 | External dependency |
| Urgency | 3 | Media server metadata usually sufficient |
| Confidence | 7 | Well-documented API |

**Description**: Enrich track metadata from MusicBrainz.

---

### 12. Playlist Collaboration
**Score: 4.2**
| Factor | Score | Notes |
|--------|-------|-------|
| Impact | 5 | Multi-user feature |
| Effort | 3 | Requires auth, sharing |
| Risk | 5 | Complexity increase |
| Urgency | 2 | Single-user design |
| Confidence | 5 | Significant architecture change |

**Description**: Allow multiple users to collaborate on playlists.

---

## Technical Debt

### TD-1: Reduce config.py Size
**Priority**: Medium
**Description**: `config.py` has 100+ variables. Consider grouping into dataclasses or a config schema.

### TD-2: Type Hints
**Priority**: Low
**Description**: Add type hints throughout codebase for better IDE support and static analysis.

### TD-3: Test Coverage
**Priority**: Medium
**Description**: Expand test coverage, especially for clustering and media server modules.

### TD-4: Frontend Modernization
**Priority**: Low
**Description**: Consider migrating to React/Vue for better maintainability (vanilla JS currently).

### TD-5: API Versioning
**Priority**: Low
**Description**: Add API versioning (e.g., `/api/v1/`) for future compatibility.

---

## Recently Completed

- [x] GPU batched inference (v0.8.0)
- [x] Multiprocessing for CPU-bound work (v0.8.0)
- [x] FFmpeg decoder option (v0.8.0)
- [x] Prefetch buffer (v0.8.0)
- [x] Direct file access (v0.8.0)
- [x] Plex media server support (feat/playlist-builder)
- [x] Multi-server playlist sync (feat/playlist-builder)
- [x] Track weight configuration (feat/playlist-builder)
