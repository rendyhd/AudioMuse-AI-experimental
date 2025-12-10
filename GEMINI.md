# AudioMuse-AI Context Guide

## Project Overview
**AudioMuse-AI** is an open-source, self-hosted application that brings AI-powered sonic analysis and automatic playlist generation to personal music libraries. It integrates with media servers like **Jellyfin**, **Navidrome**, **LMS**, **Lyrion**, and **Emby**.

**Key Features:**
*   **Sonic Analysis:** Uses Librosa and ONNX (MusicNN) to analyze audio files locally.
*   **Clustering & Playlists:** Generates playlists based on mood, sonic similarity, and "song alchemy" (mixing tracks).
*   **Visualization:** 2D map of the music collection.
*   **AI Naming:** Uses LLMs (Gemini, Mistral, Ollama, OpenAI) to name generated playlists.

## Architecture & Tech Stack

### Core Components
*   **Backend:** Python with **Flask** (`app.py`).
*   **Task Queue:** **Redis Queue (RQ)** handles heavy lifting (analysis, clustering) asynchronously (`rq_worker.py`).
*   **Database:** **PostgreSQL** stores analysis data, task status, and app state.
*   **Cache/Broker:** **Redis** serves as the message broker for RQ and caching layer.
*   **Frontend:** HTML/CSS/JS served by Flask (templates in `templates/`, assets in `static/`).

### Key Libraries
*   **Audio/ML:** `librosa`, `onnx`, `scikit-learn`, `numpy`, `scipy`.
*   **Similarity:** `voyager` (Approximate Nearest Neighbors).
*   **LLM Integration:** `google-generativeai`, `mistralai`, `requests` (for Ollama/OpenAI).
*   **Containerization:** Docker, Docker Compose.

## Directory Structure

*   **`app.py`**: Main entry point for the Flask web application and API.
*   **`tasks/`**: Contains the core business logic and background tasks (e.g., `analysis.py`, `clustering.py`, `voyager_manager.py`).
*   **`ai.py`**: Handles interactions with LLMs (Gemini, Mistral, Ollama).
*   **`config.py`**: Default configuration parameters.
*   **`deployment/`**: Docker Compose files (`docker-compose.yaml`, `docker-compose-navidrome.yaml`, etc.) and Kubernetes/Podman configs.
*   **`templates/` & `static/`**: Frontend code.
*   **`tests/`**: Pytest-based unit and integration tests.
*   **`requirements/`**: Python dependency files (`common.txt`, `cpu.txt`, `gpu.txt`).

## Development & Usage

### Building and Running
The project is designed to run in **Docker**.

1.  **Environment Setup:**
    *   Copy `deployment/.env.example` to `deployment/.env`.
    *   Configure media server credentials (URL, User ID, Token/Password) and API keys in `.env`.

2.  **Run with Docker Compose:**
    ```bash
    # For Jellyfin
    docker compose -f deployment/docker-compose.yaml up -d

    # For Navidrome
    docker compose -f deployment/docker-compose-navidrome.yaml up -d
    
    # Rebuild local changes
    docker compose -f deployment/docker-compose.yaml up -d --build
    ```

### Local Development (Non-Docker)
While Docker is preferred, you can run components locally for debugging, provided you have Redis and Postgres accessible.
1.  Install dependencies: `pip install -r requirements/common.txt`
2.  Set environment variables (refer to `config.py` or `.env`).
3.  Run Flask: `python app.py`
4.  Run Worker: `python rq_worker.py`

### Testing
Automated tests are configured with `pytest`.

```bash
# Run all tests
pytest

# Run specific test category
pytest -m unit
pytest -m integration
```

## Contribution Guidelines
*   **Conventions:** Follow standard Python (PEP 8) and project-specific patterns.
*   **Compatibility:** Changes must support **both Intel and ARM** architectures.
*   **Media Servers:** Verify changes against at least one supported media server (Jellyfin/Navidrome).
*   **Pull Requests:** Open Draft PRs for early feedback. Ensure core features (Analysis, Instant Playlist, etc.) are tested.

## Key Files for Context
*   `config.py`: Understanding configuration options.
*   `tasks/analysis.py`: How audio analysis is performed.
*   `tasks/clustering.py`: Logic for generating playlists.
*   `app.py`: API endpoints and routing.
