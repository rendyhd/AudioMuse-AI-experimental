# AudioMuse-AI Architecture Working Document

## Quick Reference

| Document | Path | Purpose |
|----------|------|---------|
| Project Structure | `docs/architecture/PROJECT_STRUCTURE.md` | Directory layout, component overview |
| Tech Stack | `docs/architecture/TECH_STACK.md` | Technologies, versions, dependencies |
| External Dependencies | `docs/architecture/DEPENDENCIES.md` | Python packages, system requirements |
| Internal Dependencies | `docs/architecture/INTERNAL_DEPENDENCIES.md` | Module relationships, coupling analysis |
| API Surface | `docs/architecture/API_SURFACE.md` | REST API endpoints |
| Patterns & Conventions | `docs/architecture/PATTERNS_AND_CONVENTIONS.md` | Code patterns, naming conventions |
| Feature Inventory | `docs/features/FEATURE_INVENTORY.md` | All features with status |
| Configuration | `docs/environments/CONFIGURATION_VARIABLES.md` | Environment variables |
| Security Audit | `docs/security/SECURITY_AUDIT.md` | Security considerations |
| Performance Analysis | `docs/quality/PERFORMANCE_ANALYSIS.md` | Bottlenecks, optimization |
| Improvement Backlog | `docs/improvements/IMPROVEMENT_BACKLOG.md` | Prioritized improvements |

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Browser)                            │
│   ┌─────────────────────────────────────────────────────────────────┐  │
│   │  HTML Templates (Jinja2) + Vanilla JS + CSS                     │  │
│   └─────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLASK APPLICATION                               │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│   │ app_analysis │ │app_clustering│ │ app_voyager  │ │  app_chat    │  │
│   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│   │  app_path    │ │ app_alchemy  │ │   app_map    │ │  app_cron    │  │
│   └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │
│                          app_helper.py                                  │
└─────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │                    ▼                    │
         │         ┌─────────────────────┐        │
         │         │   Redis (Queue)     │        │
         │         │   - default queue   │        │
         │         │   - high queue      │        │
         │         │   - pub/sub         │        │
         │         └─────────────────────┘        │
         │                    │                   │
         │                    ▼                   │
         │    ┌───────────────────────────────┐   │
         │    │        RQ WORKERS             │   │
         │    │  ┌───────────────────────┐    │   │
         │    │  │   tasks/analysis.py   │    │   │
         │    │  │   tasks/clustering.py │    │   │
         │    │  │   tasks/voyager_mgr   │    │   │
         │    │  │   tasks/mediaserver   │    │   │
         │    │  └───────────────────────┘    │   │
         │    └───────────────────────────────┘   │
         │                    │                   │
         ▼                    ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PostgreSQL                                      │
│   ┌────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌────────────┐  │
│   │ score  │ │embedding │ │ playlist │ │ task_status │ │voyager_idx │  │
│   └────────┘ └──────────┘ └──────────┘ └─────────────┘ └────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
        ┌───────────────────────────────────────────────────┐
        │              EXTERNAL SERVICES                    │
        │  ┌─────────────┐  ┌─────────────┐                │
        │  │Media Servers│  │ AI Providers │               │
        │  │ - Jellyfin  │  │ - Gemini    │               │
        │  │ - Navidrome │  │ - Mistral   │               │
        │  │ - Emby      │  │ - OpenAI    │               │
        │  │ - Lyrion    │  │ - Ollama    │               │
        │  │ - Plex      │  └─────────────┘               │
        │  └─────────────┘                                │
        └───────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Audio Analysis Flow
```
Media Server → Album List → Track Download → Audio Load →
Feature Extraction → ONNX Inference → Embedding Storage →
Voyager Index Build → Redis Publish → Flask Reload
```

### Similarity Search Flow
```
User Query → Flask API → Voyager Query →
Distance Filtering → Deduplication →
Artist Cap → Response
```

### Clustering Flow
```
Clustering Request → Fetch Data → PCA →
Evolutionary Search (parallel RQ jobs) →
Best Parameters → Final Clustering →
AI Naming → Playlist Creation
```

## Key Files Quick Reference

| File | Purpose | Change Impact |
|------|---------|---------------|
| `config.py` | All configuration | HIGH |
| `app_helper.py` | DB, queues, task status | CRITICAL |
| `tasks/analysis.py` | Audio analysis pipeline | CRITICAL |
| `tasks/clustering.py` | Playlist generation | HIGH |
| `tasks/voyager_manager.py` | Similarity search | CRITICAL |
| `tasks/mediaserver.py` | Media server dispatcher | HIGH |
| `ai.py` | AI provider integration | MEDIUM |

## Session Log

### 2025-12-10 - Initial Comprehensive Review

**Completed**:
- Phase 1: Project structure and tech stack documented
- Phase 2: External and internal dependencies mapped
- Phase 3: Features and APIs inventoried
- Phase 4: Configuration variables documented
- Phase 5: Code patterns and conventions analyzed
- Phase 6: Security audit completed
- Phase 7: Performance analysis completed
- Phase 8: Improvement backlog created with scoring
- Phase 9: Master working document created
- Phase 10: Pending CLAUDE.md update

**Key Findings**:
1. Well-structured Flask blueprint architecture
2. Sophisticated GPU optimization for audio analysis
3. Evolutionary clustering with parallel RQ jobs
4. Multiple media server integrations via dispatcher pattern
5. No authentication (private network design)
6. Active development on playlist-builder features

**Recommendations**:
1. Add WebSocket for real-time task updates
2. Implement database connection pooling
3. Add optional API authentication
4. Consider incremental index updates

---

## Change Impact Matrix

When modifying these files, consider the impact:

| Module Changed | Affected Areas |
|----------------|----------------|
| `config.py` | Everything |
| `app_helper.py` | All blueprints, all tasks |
| `tasks/voyager_manager.py` | Similarity, path, alchemy, chat |
| `tasks/mediaserver.py` | Analysis, clustering, playlist sync |
| `tasks/analysis.py` | Only analysis feature |
| `tasks/clustering.py` | Only clustering feature |

## Testing Strategy

Before deploying changes:
1. Run `pytest tests/unit/` for unit tests
2. Test with small library (10-20 albums) first
3. Verify media server integration manually
4. Check GPU functionality if ML code changed
5. Test with all supported media servers if mediaserver code changed
