# AudioMuse-AI External Dependencies

## Python Dependencies

### Core Framework
| Package | Version | Purpose |
|---------|---------|---------|
| flask | 3.x | Web framework |
| flasgger | 0.9.x | Swagger/OpenAPI documentation |
| werkzeug | 3.x | WSGI utilities (via Flask) |

### Database & Queue
| Package | Version | Purpose |
|---------|---------|---------|
| psycopg2-binary | 2.9.x | PostgreSQL driver |
| redis | 5.x | Redis client |
| rq | 1.x | Redis Queue job processing |

### Audio Processing
| Package | Version | Purpose |
|---------|---------|---------|
| librosa | 0.11.x | Audio feature extraction |
| numpy | 1.26.x | Numerical computing |
| scipy | 1.15.x | Scientific computing |
| soundfile | 0.13.x | Audio file I/O |
| pydub | - | Audio manipulation |
| resampy | - | High-quality audio resampling |
| numba | 0.60.x | JIT compilation for librosa |

### Machine Learning
| Package | Version | Purpose |
|---------|---------|---------|
| onnx | 1.16+ | ONNX model format |
| onnxruntime | 1.19.x | ONNX Runtime (CPU) |
| onnxruntime-gpu | 1.19.x | ONNX Runtime (CUDA) - optional |
| scikit-learn | 1.7.x | ML algorithms (clustering) |
| umap-learn | 0.5.x | UMAP dimensionality reduction |

### Vector Search
| Package | Version | Purpose |
|---------|---------|---------|
| voyager | 2.x | Spotify's HNSW library |

### GPU Acceleration (Optional)
| Package | Version | Purpose |
|---------|---------|---------|
| cupy | 13.x | CUDA array operations |
| cuml | 24.x | RAPIDS GPU ML algorithms |

### AI Providers
| Package | Version | Purpose |
|---------|---------|---------|
| google-generativeai | 0.8.x | Google Gemini API |
| mistralai | 1.x | Mistral API |
| requests | 2.x | HTTP client (OpenAI/Ollama) |

### Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| ftfy | 6.x | Text encoding fixes |
| python-dotenv | - | Environment variable loading |
| uuid | stdlib | Unique ID generation |

### Testing
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 7.x+ | Test framework |

## System Dependencies

### Required
| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| PostgreSQL | 15+ | Primary database |
| Redis | 7+ | Job queue and pub/sub |
| FFmpeg | 6.x | Audio decoding |

### Optional (GPU Acceleration)
| Dependency | Version | Purpose |
|------------|---------|---------|
| NVIDIA Driver | 535+ | GPU support |
| CUDA | 12.x | GPU compute |
| cuDNN | 8.x | Deep learning primitives |

## Media Server APIs (External)

| Server | API Type | Auth Method |
|--------|----------|-------------|
| Jellyfin | REST | API Token |
| Emby | REST | API Token |
| Navidrome | Subsonic | User/Password |
| Lyrion/LMS | JSON-RPC | None |
| Plex | REST | API Token |

## AI Provider APIs (External)

| Provider | API Type | Auth Method |
|----------|----------|-------------|
| Google Gemini | REST | API Key |
| Mistral | REST | API Key |
| OpenAI/OpenRouter | REST | API Key |
| Ollama | REST | None (self-hosted) |

## Docker Images

The project uses these base images:
- `python:3.11-slim` - Base Python runtime
- `nvidia/cuda:12.x-runtime` - GPU-enabled runtime (optional)

## Model Dependencies

ONNX models are loaded from the `models/` directory:

| Model | Purpose | Input | Output |
|-------|---------|-------|--------|
| MTT MusicNN | Audio embeddings | Spectrogram | 200-dim vector |
| mood_aggressive | Mood prediction | Spectrogram | Score |
| mood_danceable | Mood prediction | Spectrogram | Score |
| mood_happy | Mood prediction | Spectrogram | Score |
| mood_party | Mood prediction | Spectrogram | Score |
| mood_relaxed | Mood prediction | Spectrogram | Score |
| mood_sad | Mood prediction | Spectrogram | Score |
