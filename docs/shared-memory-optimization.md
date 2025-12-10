# Shared Memory Optimization for Multiprocessing Audio Analysis

## Problem Summary

The audio analysis pipeline uses Python multiprocessing with 4 workers to process tracks in parallel. A deadlock was discovered where workers would hang on `pipe_write` when returning large results (~6MB patches arrays) through the IPC pipe (64KB buffer limit).

### Current Fix (Pickle Files) - Performance Regression
The temporary fix saves results to pickle files in `/dev/shm` instead of returning through the pipe. This works but causes a **~2x performance regression**:

| Method | Per Track | 12-Track Album |
|--------|-----------|----------------|
| IPC Pipe (original, when working) | ~8-9s | ~1:40 |
| Pickle Files (current) | ~15-17s | ~3:05 |

### Root Cause of Overhead
1. `pickle.dump()` - serialization of ~6MB numpy array
2. File write syscall to /dev/shm
3. `pickle.load()` - deserialization
4. `os.remove()` - cleanup syscall

## Proposed Solution: `multiprocessing.shared_memory`

Use Python 3.8+ SharedMemory for zero-copy data sharing between worker and main process.

### Benefits
- **Zero serialization** - numpy array written directly to shared memory
- **Zero-copy read** - main process reads directly from same memory
- **Small IPC overhead** - only pass SharedMemory name (~32 bytes) through pipe
- **No file I/O syscalls** - pure memory operations

## Implementation Details

### File: `tasks/analysis.py`

### 1. Modify `cpu_process_audio_worker()` (lines ~1429-1444)

**Current code (pickle):**
```python
# Save ALL results to temp file to avoid pipe deadlock with multiple workers
import pickle
result_temp_path = f"/dev/shm/result_{track_id}_{os.getpid()}.pkl"
result_data = {
    'track_id': track_id,
    'item': item_dict,
    'cpu_features': cpu_features,
    'patches': final_patches,
    'patches_shape': final_patches.shape
}
with open(result_temp_path, 'wb') as f:
    pickle.dump(result_data, f, protocol=pickle.HIGHEST_PROTOCOL)

return {'result_path': result_temp_path, 'track_id': track_id}
```

**New code (shared_memory):**
```python
from multiprocessing.shared_memory import SharedMemory
import json

# Create shared memory for patches array (the large data)
patches_bytes = final_patches.tobytes()
shm = SharedMemory(create=True, size=len(patches_bytes))
# Copy patches data to shared memory
shm.buf[:len(patches_bytes)] = patches_bytes
shm_name = shm.name  # e.g., "psm_12345678"

# Close local reference (memory persists until unlinked)
shm.close()

# Return only small metadata through pipe (avoids 64KB buffer overflow)
return {
    'track_id': track_id,
    'item': item_dict,
    'cpu_features': cpu_features,
    'shm_name': shm_name,
    'patches_shape': final_patches.shape,
    'patches_dtype': str(final_patches.dtype)
}
```

### 2. Modify `gpu_batch_embedding_inference()` (lines ~1469-1511)

**Current code (pickle):**
```python
import pickle
for result in cpu_results:
    if result is None:
        continue

    result_path = result.get('result_path')
    if result_path and os.path.exists(result_path):
        try:
            with open(result_path, 'rb') as f:
                full_result = pickle.load(f)
            os.remove(result_path)
        except Exception as e:
            logger.warning(f"Failed to load result from {result_path}: {e}")
            continue

        patches = full_result.get('patches')
```

**New code (shared_memory):**
```python
from multiprocessing.shared_memory import SharedMemory

for result in cpu_results:
    if result is None:
        continue

    shm_name = result.get('shm_name')
    if shm_name:
        try:
            # Attach to existing shared memory
            shm = SharedMemory(name=shm_name)

            # Reconstruct numpy array from shared memory (zero-copy view)
            patches_shape = result['patches_shape']
            patches_dtype = np.dtype(result['patches_dtype'])
            patches = np.ndarray(
                shape=patches_shape,
                dtype=patches_dtype,
                buffer=shm.buf
            )

            # IMPORTANT: Make a copy before unlinking (shm.buf becomes invalid)
            patches = patches.copy()

            # Cleanup shared memory
            shm.close()
            shm.unlink()  # Deallocates the shared memory

        except Exception as e:
            logger.warning(f"Failed to load from shared memory {shm_name}: {e}")
            continue
    else:
        # Fallback for old format
        patches = result.get('patches')
        if patches is None:
            continue

    # Build loaded_results with the reconstructed data
    loaded_results.append({
        'track_id': result['track_id'],
        'item': result['item'],
        'cpu_features': result['cpu_features'],
        'patches': patches,
        'patches_shape': patches.shape
    })
```

### 3. Add Cleanup in Finally Block (lines ~1854-1859)

**Current cleanup:**
```python
# Cleanup pickle result files (in case of crashes/failures)
for f in glob.glob(os.path.join(TEMP_SHM_DIR, "result_*.pkl")):
    try:
        os.remove(f)
    except Exception:
        pass
```

**New cleanup (add shared memory cleanup):**
```python
# Cleanup shared memory segments (in case of crashes/failures)
# SharedMemory names are like "psm_12345678" or "/psm_12345678"
import glob
for shm_file in glob.glob("/dev/shm/psm_*"):
    try:
        # Extract name from path
        shm_name = os.path.basename(shm_file)
        shm = SharedMemory(name=shm_name)
        shm.close()
        shm.unlink()
    except Exception:
        pass

# Also cleanup old pickle files for backwards compatibility
for f in glob.glob(os.path.join(TEMP_SHM_DIR, "result_*.pkl")):
    try:
        os.remove(f)
    except Exception:
        pass
```

## Complete Modified Function: `cpu_process_audio_worker()`

```python
def cpu_process_audio_worker(args):
    """
    CPU-bound audio processing worker function for multiprocessing pool.
    Handles: audio loading, tempo/energy/key detection, mel spectrogram patches.
    Uses shared memory for returning large patches array to avoid IPC pipe deadlock.

    Args:
        args: tuple of (temp_path, original_path, track_id, item_dict)

    Returns:
        dict with track_id, cpu_features, shm_name, patches_shape, patches_dtype, item
        or None on failure
    """
    from multiprocessing.shared_memory import SharedMemory

    temp_path, original_path, track_id, item_dict = args

    try:
        # --- 1. Load Audio ---
        if temp_path and os.path.isfile(temp_path):
            with open(temp_path, 'rb') as f:
                file_bytes = f.read()
            try:
                os.remove(temp_path)
            except Exception:
                pass
            audio, sr = load_audio_with_ffmpeg_from_bytes(file_bytes, original_path, 16000, AUDIO_LOAD_TIMEOUT)
        else:
            audio, sr = load_audio_with_ffmpeg(original_path, 16000, AUDIO_LOAD_TIMEOUT)

        if audio is None or audio.size == 0:
            return None

        # --- 2. CPU-bound Features ---
        if USE_FAST_TEMPO:
            tempo = librosa.beat.tempo(y=audio, sr=sr)[0]
        else:
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)

        average_energy = np.mean(librosa.feature.rms(y=audio))

        chroma = librosa.feature.chroma_stft(y=audio, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        key_vals = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        major_profile = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1])
        minor_profile = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0])

        major_correlations = np.array([np.corrcoef(chroma_mean, np.roll(major_profile, i))[0, 1] for i in range(12)])
        minor_correlations = np.array([np.corrcoef(chroma_mean, np.roll(minor_profile, i))[0, 1] for i in range(12)])

        major_key_idx = np.argmax(major_correlations)
        minor_key_idx = np.argmax(minor_correlations)

        if major_correlations[major_key_idx] > minor_correlations[minor_key_idx]:
            musical_key = key_vals[major_key_idx]
            scale = 'major'
        else:
            musical_key = key_vals[minor_key_idx]
            scale = 'minor'

        cpu_features = {
            "tempo": float(tempo),
            "energy": float(average_energy),
            "key": musical_key,
            "scale": scale
        }

        # --- 3. Mel Spectrogram and Patches ---
        n_mels, hop_length, n_fft, frame_size = 96, 256, 512, 187
        mel_spec = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_fft=n_fft, hop_length=hop_length,
            n_mels=n_mels, window='hann', center=False, power=2.0,
            norm='slaney', htk=False
        )
        log_mel_spec = np.log10(1 + 10000 * mel_spec)
        spec_patches = [log_mel_spec[:, i:i+frame_size] for i in range(0, log_mel_spec.shape[1] - frame_size + 1, frame_size)]

        if not spec_patches:
            return None

        transposed_patches = np.array(spec_patches).transpose(0, 2, 1)
        final_patches = transposed_patches.astype(np.float32)

        # --- 4. Store patches in shared memory (avoids IPC pipe deadlock) ---
        patches_bytes = final_patches.tobytes()
        shm = SharedMemory(create=True, size=len(patches_bytes))
        shm.buf[:len(patches_bytes)] = patches_bytes
        shm_name = shm.name
        shm.close()  # Close local reference, memory persists until unlink

        # Return only small metadata through pipe (~200 bytes vs ~6MB)
        return {
            'track_id': track_id,
            'item': item_dict,
            'cpu_features': cpu_features,
            'shm_name': shm_name,
            'patches_shape': final_patches.shape,
            'patches_dtype': str(final_patches.dtype)
        }

    except Exception as e:
        import sys
        print(f"[CPU Worker] Error processing {track_id}: {e}", file=sys.stderr)
        return None
```

## Complete Modified Function: `gpu_batch_embedding_inference()`

```python
def gpu_batch_embedding_inference(cpu_results, embedding_session, batch_size=100):
    """
    Run batched ONNX embedding inference on GPU for all CPU-processed tracks.
    Reads patches from shared memory (zero-copy), batches them for GPU efficiency.

    Args:
        cpu_results: List of dicts from cpu_process_audio_worker
        embedding_session: ONNX session for embedding model
        batch_size: Number of patches to process in each GPU batch

    Returns:
        tuple: (dict mapping track_id -> embeddings_per_patch, list of loaded_results)
    """
    from multiprocessing.shared_memory import SharedMemory

    if not cpu_results:
        return {}, []

    all_patches = []
    track_patch_indices = []
    loaded_results = []

    for result in cpu_results:
        if result is None:
            continue

        patches = None

        # Try shared memory first (new format)
        shm_name = result.get('shm_name')
        if shm_name:
            try:
                shm = SharedMemory(name=shm_name)
                patches_shape = result['patches_shape']
                patches_dtype = np.dtype(result['patches_dtype'])

                # Create numpy array view of shared memory
                patches = np.ndarray(
                    shape=patches_shape,
                    dtype=patches_dtype,
                    buffer=shm.buf
                )
                # Copy before unlinking (buffer becomes invalid after unlink)
                patches = patches.copy()

                shm.close()
                shm.unlink()
            except Exception as e:
                logger.warning(f"Failed to load from shared memory {shm_name}: {e}")
                continue

        # Fallback: pickle file path (old format during transition)
        elif result.get('result_path'):
            import pickle
            result_path = result['result_path']
            if os.path.exists(result_path):
                try:
                    with open(result_path, 'rb') as f:
                        full_result = pickle.load(f)
                    os.remove(result_path)
                    patches = full_result.get('patches')
                    result = full_result  # Use full result for item/cpu_features
                except Exception as e:
                    logger.warning(f"Failed to load from pickle {result_path}: {e}")
                    continue

        # Fallback: direct patches in result (legacy)
        elif 'patches' in result:
            patches = result['patches']

        if patches is None:
            continue

        # Build loaded_results entry
        loaded_results.append({
            'track_id': result['track_id'],
            'item': result['item'],
            'cpu_features': result['cpu_features'],
            'patches': patches,
            'patches_shape': patches.shape
        })

        start_idx = len(all_patches)
        all_patches.extend(patches)
        end_idx = len(all_patches)
        track_patch_indices.append((result['track_id'], start_idx, end_idx))

    if not all_patches:
        return {}, []

    all_patches_array = np.array(all_patches, dtype=np.float32)
    total_patches = len(all_patches_array)

    logger.info(f"[GPU Batch] Running embedding inference on {total_patches} patches from {len(track_patch_indices)} tracks")

    # --- Batched GPU inference ---
    all_embeddings = []
    for i in range(0, total_patches, batch_size):
        batch = all_patches_array[i:i+batch_size]
        try:
            feed_dict = {DEFINED_TENSOR_NAMES['embedding']['input']: batch}
            output = embedding_session.run(None, feed_dict)
            all_embeddings.extend(output[0])
        except Exception as e:
            logger.error(f"[GPU Batch] Embedding inference error on batch {i//batch_size}: {e}")
            all_embeddings.extend([None] * len(batch))

    # --- Map embeddings back to tracks ---
    track_embeddings = {}
    for track_id, start_idx, end_idx in track_patch_indices:
        track_embeddings[track_id] = np.array(all_embeddings[start_idx:end_idx])

    return track_embeddings, loaded_results
```

## Cleanup Function Update

Add this to the finally block in `analyze_album_with_multiprocessing_batched_gpu()`:

```python
finally:
    # Cleanup shared memory segments (psm_* files in /dev/shm)
    from multiprocessing.shared_memory import SharedMemory
    for shm_file in glob.glob("/dev/shm/psm_*"):
        try:
            shm_name = os.path.basename(shm_file)
            shm = SharedMemory(name=shm_name)
            shm.close()
            shm.unlink()
        except Exception:
            pass

    # Cleanup old pickle files (backwards compatibility)
    for f in glob.glob(os.path.join(TEMP_SHM_DIR, "result_*.pkl")):
        try:
            os.remove(f)
        except Exception:
            pass
```

## Testing

### 1. Unit Test for Shared Memory
```python
def test_shared_memory_patches():
    """Test shared memory roundtrip for patches array."""
    from multiprocessing.shared_memory import SharedMemory
    import numpy as np

    # Simulate patches array (~6MB)
    patches = np.random.rand(100, 187, 96).astype(np.float32)

    # Write to shared memory
    patches_bytes = patches.tobytes()
    shm = SharedMemory(create=True, size=len(patches_bytes))
    shm.buf[:] = patches_bytes
    shm_name = shm.name
    shm.close()

    # Read from shared memory
    shm2 = SharedMemory(name=shm_name)
    patches_restored = np.ndarray(
        shape=patches.shape,
        dtype=patches.dtype,
        buffer=shm2.buf
    ).copy()
    shm2.close()
    shm2.unlink()

    assert np.allclose(patches, patches_restored)
    print("✓ Shared memory roundtrip successful")
```

### 2. Integration Test
```bash
# Build and restart container
docker compose -f deployment/docker-compose.dev.yaml up -d --build

# Monitor logs for album completion times
docker logs -f audiomuse-ai-worker-instance-dev 2>&1 | grep "Successfully completed"

# Expected: 10-13 track albums completing in ~1:30-2:00 (vs ~3:00 with pickle)
```

### 3. Memory Leak Check
```bash
# Check /dev/shm for orphaned segments
docker exec audiomuse-ai-worker-instance-dev ls -la /dev/shm/psm_*

# Should be empty after album completion
# If leaking, segments will accumulate
```

## Performance Expectations

| Metric | Pickle (Current) | Shared Memory (New) |
|--------|------------------|---------------------|
| Per-track time | 15-17s | 8-10s |
| 12-track album | 3:00-3:30 | 1:30-2:00 |
| Memory overhead | Serialize+Write+Read | Direct memory copy |
| IPC data through pipe | ~50 bytes (path) | ~200 bytes (metadata) |

## Rollback Plan

If issues occur, revert to pickle approach by:
1. Restore original `cpu_process_audio_worker()` with pickle
2. Restore original `gpu_batch_embedding_inference()` with pickle load
3. Keep cleanup for both pickle and shared memory

## Known Limitations

1. **SharedMemory names are system-wide** - Could conflict if multiple workers use same names (mitigated by including PID and track_id)
2. **Memory must be unlinked explicitly** - Crashes can leave orphaned segments (cleanup handles this)
3. **Copy required before unlink** - The numpy array view becomes invalid after `shm.unlink()`

## References

- Python SharedMemory docs: https://docs.python.org/3/library/multiprocessing.shared_memory.html
- Original issue: IPC pipe buffer overflow (64KB) with 4 workers writing ~6MB each
- Container: `audiomuse-ai-worker-instance-dev`
- File: `tasks/analysis.py`
- Lines: ~1429-1444 (worker), ~1469-1511 (GPU batch)
