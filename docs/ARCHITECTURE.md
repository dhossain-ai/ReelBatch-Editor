# ReelBatch Editor — Architecture

## Technology Stack

### Core Technologies
- **Language:** Python 3.10+
- **GUI Framework:** PySide6 (Qt6)
- **Video Processing:** FFmpeg (via subprocess)
- **Frame Extraction:** OpenCV (cv2)
- **Packaging:** PyInstaller

### External Dependencies
- FFmpeg executable (bundled or system-installed)
- NVIDIA GPU drivers (for NVENC acceleration, optional)

## Project Structure

```
reelbatch-editor/
├── main.py                 # Application entry point
├── src/
│   ├── __init__.py
│   ├── ui/                 # PySide6 UI components
│   │   ├── __init__.py
│   │   ├── main_window.py  # Main application window
│   │   ├── preview_canvas.py  # Video preview with selection
│   │   ├── video_list.py   # Video queue widget
│   │   └── controls.py     # Control panels and buttons
│   ├── video/              # Video processing logic
│   │   ├── __init__.py
│   │   ├── processor.py    # FFmpeg command generation
│   │   ├── worker.py       # Background worker for FFmpeg
│   │   └── preview.py      # OpenCV frame extraction
│   ├── models/             # Data models
│   │   ├── __init__.py
│   │   ├── video_item.py   # Video file metadata
│   │   ├── selection.py    # Rectangle selection model
│   │   └── preset.py       # Preset model
│   └── utils/              # Utilities
│       ├── __init__.py
│       ├── ffmpeg.py       # FFmpeg detection and validation
│       ├── coordinates.py  # Normalized coordinate conversion
│       └── config.py       # App configuration
├── resources/              # UI resources
│   ├── icons/
│   └── styles/
├── docs/                   # Documentation
└── tests/                  # Unit tests
```

## Component Architecture

### UI Layer (PySide6)

#### MainWindow
- Central coordinator for all UI components
- Manages application state
- Handles menu actions and global commands
- Coordinates between video list, preview, and controls
- Restores persisted app settings at startup and saves them when relevant controls change
- Applies presets to the preview selection, processing mode, sliders, encoder, quality, and logo/image path
- Derives the effective export mode from the simplified creator workflow controls:
  - `Area Cleanup` dropdown for blur/logo cleanup
  - `Apply zoom/crop` checkbox for zoom-only exports in this phase
  - `Test Export Current Video` for single-clip validation before batch export

#### PreviewCanvas
- Displays video preview frame
- Handles mouse events for rectangle selection
- Draws selection rectangle overlay
- Converts between screen and normalized coordinates
- Uses the fitted preview image rect, not the full widget bounds, when mapping selection coordinates
- Reuses the same normalized selection overlay while preview playback advances frame-by-frame

#### VideoList
- Displays queue of imported videos
- Shows video metadata (filename, resolution, duration)
- Shows lightweight export status text such as queued, done, CPU fallback, or failed
- Allows reordering and removal
- Signals selection changes to MainWindow

#### Controls
- Guided right-panel sections for:
  - Area Cleanup
  - Transform
  - Output
  - Presets
- Uses conditional visibility so only the controls relevant to the current creator workflow choice are emphasized
- Validates mode-specific requirements (selection, overlay image, zoom-only export)
- Offers output-resolution standardization controls:
  - `Output Resolution` (`Keep original`, `720x1280`, `1080x1920`, `1440x2560`, `Custom`)
  - `Resize Mode` (`Fill & Crop`, `Fit with Padding`)
  - Conditional custom width/height inputs that require positive even integers
- Offers output quality presets (Fast/Balanced/High Quality)
- Surfaces mode-specific help text, slider values, and tooltips without redesigning the layout
- Workflow hint/status area for `Add videos -> Draw area -> Choose options -> Export`
- Export All button, Test Export Current Video button, and progress indicator
- Output folder picker

### Video Processing Layer

#### Processor
- Generates FFmpeg commands based on selected mode
- Handles coordinate conversion (normalized → pixels)
- Resolves the FFmpeg executable once per session/export using this search order:
  - `shutil.which("ffmpeg")`
  - `C:\ffmpeg\bin\ffmpeg.exe`
  - `ffmpeg\bin\ffmpeg.exe` relative to the app/repo root
  - `ffmpeg.exe` relative to the app/repo root
- Supports three processing modes:
  - Blur: Uses FFmpeg `boxblur` or `gblur` filter
  - Logo overlay: Scales the selected image to fit the target rectangle, pads transparently when needed, then uses FFmpeg `overlay`
  - Zoom/crop: Scales the full frame up according to the zoom percentage, then center-crops back to the original dimensions
- Supports an optional final output-standardization step after the main processing mode:
  - `Fill & Crop`: `scale=target_w:target_h:force_original_aspect_ratio=increase:flags=lanczos,crop=target_w:target_h`
  - `Fit with Padding`: `scale=target_w:target_h:force_original_aspect_ratio=decrease:flags=lanczos,pad=target_w:target_h:(ow-iw)/2:(oh-ih)/2`
- Applies standardization to blur, logo/image, and zoom/crop exports without generating intermediate files
- Generates encoder-specific commands (NVENC vs CPU)
- Maps output-quality presets to encoder-specific preset/CRF/CQ arguments
- Resolves Auto encoder mode by preferring `h264_nvenc` and falling back to `libx264` when needed

#### Worker
- QThread-based background worker
- Executes FFmpeg commands via subprocess
- Streams FFmpeg output to UI
- Handles process cancellation
- Reports progress and errors
- Ensures UI remains responsive during export
- Continues exporting later files even if one file fails
- Dispatches blur, logo/image, and zoom/crop exports through the same encoder/fallback pipeline
- Writes compact timestamped export logs to a user-writable logs folder

#### Preview
- Extracts first frame from video using OpenCV
- Gets video dimensions and metadata
- Converts frames to Qt-compatible format
- Caches preview frames for performance

#### Preview Playback
- Uses one OpenCV `VideoCapture` for the currently selected queue item
- Drives frame advancement with a UI-thread `QTimer`
- Keeps playback intentionally simple: video-only, no audio, no Qt Multimedia dependency
- Supports play/pause, timeline scrubbing, current/total time display, and clean reset on video switch or queue clear
- Reapplies the normalized rectangle overlay after every displayed frame so the selection stays visible while playing and scrubbing

### Data Models

#### VideoItem
- Stores video file path
- Stores video metadata (resolution, duration, codec)
- Stores export status
- Stores output path

#### Selection
- Stores rectangle as normalized percentages
- Provides conversion methods (normalized ↔ pixels)
- Validates selection bounds

#### Preset
- Stores selection coordinates
- Stores processing mode
- Stores mode-specific settings
- Stores output resolution, resize mode, and custom dimensions
- Serializable to/from JSON
- Saves to the user's app-data presets folder by default and can also be exported/imported as standalone JSON files

### Utilities

#### FFmpeg
- Detects FFmpeg installation from PATH, a common Windows install path, or future bundled executable locations
- Validates FFmpeg version
- Checks for NVENC support
- Provides a cached resolved FFmpeg path abstraction that is reused for encoder probing and export subprocesses

#### Coordinates
- Converts between pixel and normalized coordinates
- Handles aspect ratio calculations
- Validates coordinate ranges

#### Config
- Manages application settings
- Stores recent paths
- Stores user preferences
- Stores output-resolution standardization preferences
- Persists to JSON/config file

#### Logging
- Writes timestamped batch export logs in app data
- Records export start/end, selected mode, encoder request, fallback events, and FFmpeg error snippets
- Keeps log files compact enough to be practical for debugging

## Data Flow

### Import Flow
1. User selects MP4 files via file dialog
2. VideoList creates VideoItem instances
3. Preview extracts first frame from first video
4. PreviewCanvas displays frame
5. User draws rectangle on PreviewCanvas
6. Selection stores normalized coordinates

### Preview Playback Flow
1. User selects a video from the queue
2. MainWindow opens a dedicated OpenCV `VideoCapture`
3. MainWindow seeks to an initial preview frame near 1 second
4. `QTimer` advances playback by reading the next frame from the same capture
5. Each frame is converted to `QImage` and displayed on `PreviewCanvas`
6. The saved normalized selection is redrawn over the current frame
7. Timeline scrubbing seeks the capture to a requested frame, updates the preview, and optionally resumes playback
8. Switching videos or clearing the queue stops the timer, releases the capture, and resets playback controls

### Export Flow
1. User chooses Area Cleanup and/or Transform settings in the simplified workflow UI
2. MainWindow validates queue, output folder, FFmpeg availability, and any mode-specific requirements
3. MainWindow derives the effective existing export mode:
   - blur selected area
   - cover with logo/image
   - zoom/crop
4. FFmpeg discovery resolves the executable path once and surfaces it in status/log output for debugging
5. Blur and logo/image modes require a normalized rectangle selection
6. Logo/image mode also requires a supported overlay file (`.png`, `.jpg`, `.jpeg`, `.webp`)
7. Zoom/crop mode uses the zoom percentage slider and does not require a selection
8. Output Resolution and Resize Mode are resolved into optional final standardization settings
9. MainWindow resolves the encoder plan (Auto/CPU/NVIDIA)
10. User clicks `Export All` or `Test Export Current Video`
11. MainWindow creates a background Worker for the selected export scope
12. Worker generates the per-video FFmpeg command for the selected mode via Processor
13. Processor appends the final scale/crop or scale/pad step after the main blur/logo/zoom filter when standardization is enabled
14. Worker executes FFmpeg in subprocess using the resolved executable path
15. If Auto mode fails on NVENC, Worker retries that file with `libx264`
16. Worker writes compact log events for export start/end, resolved FFmpeg path, output standardization choice, per-file results, fallback usage, and failure snippets
17. UI updates progress bar, queue item status text, and status label
18. On completion, Worker signals success/failure summary back to MainWindow
19. MainWindow shows a compact completion dialog with totals, fallback count, output folder, and log file path

## Threading Model

### Main Thread (UI)
- Runs PySide6 event loop
- Handles all UI updates
- Responds to user input
- Must never block
- Owns preview playback control because OpenCV frame reads are lightweight and timer-driven for a single selected clip

### Worker Threads
- One worker per export operation
- Can run multiple workers in parallel (configurable)
- Communicate with UI via Qt signals/slots
- Use subprocess to run FFmpeg (non-blocking)
- Remain responsible only for export work, not preview playback

## Coordinate System

### Normalized Coordinates
- All selections stored as percentages (0-100)
- Independent of video resolution
- Format: `{x_percent, y_percent, width_percent, height_percent}`

### Preview-to-Video Mapping
- The preview image is scaled to fit inside the canvas while preserving aspect ratio
- Any leftover space becomes letterboxing/padding and is excluded from selection math
- Mouse drag points are clamped to the displayed image rect before conversion
- Normalized values are computed from the clamped image-relative rectangle, so resizing the window only changes the on-screen projection, not the stored percentages

### Pixel Coordinates
- Used for FFmpeg commands
- Calculated at export time
- Formula: `pixel = (percent / 100) * dimension`
- Width and height are clamped to valid integers and kept at least 2 pixels, preferring even dimensions where practical

## FFmpeg Integration

### Command Generation
```python
# Blur example
ffmpeg -i input.mp4 -filter_complex "[0:v]split[base][tmp];[tmp]crop=w:h:x:y,boxblur=12:1[blurred];[base][blurred]overlay=x:y[outv]" -map [outv] -map 0:a? output_blurred.mp4

# Logo overlay example
ffmpeg -i input.mp4 -i logo.png -filter_complex "[1:v]scale=w:h:force_original_aspect_ratio=decrease,pad=w:h:(ow-iw)/2:(oh-ih)/2:color=0x00000000[logo];[0:v][logo]overlay=x:y:format=auto[outv]" -map [outv] -map 0:a? output_branded.mp4

# Zoom/crop example
ffmpeg -i input.mp4 -filter_complex "[0:v]scale=scaled_w:scaled_h,crop=orig_w:orig_h:(iw-orig_w)/2:(ih-orig_h)/2[outv]" -map [outv] -map 0:a? output_zoomed.mp4

# Blur + final 1080x1920 fill/crop example
ffmpeg -i input.mp4 -filter_complex "[0:v]split[base][tmp];[tmp]crop=w:h:x:y,boxblur=12:1[blurred];[base][blurred]overlay=x:y[preoutv];[preoutv]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920[outv]" -map [outv] -map 0:a? output_blurred_1080x1920.mp4
```

### NVENC Detection
```python
<resolved_ffmpeg_path> -encoders
```

The application scans the encoder list for:
- `h264_nvenc`
- `h264_qsv`
- `h264_amf`
- `libx264`

If discovery fails, the UI shows:

`FFmpeg was not found. Install FFmpeg, add it to PATH, or place it at C:\ffmpeg\bin\ffmpeg.exe.`

### Error Handling
- Parse FFmpeg stderr for errors
- Map common errors to user-friendly messages
- Fallback to CPU encoder if NVENC fails
- Log full FFmpeg output for debugging
- Keep popup summaries readable by truncating the visible failure list

## State Management

### Application State
- Current processing mode
- Current selection
- Video queue
- Export status
- User preferences

### Persistence
- Presets saved to JSON in a writable app-data presets folder
- App settings saved to a writable JSON config file
- Presets can be exported/imported through ordinary JSON files
- Export logs saved to a writable logs folder

## Security Considerations

- Validate all file paths before processing
- Sanitize FFmpeg commands to prevent injection
- Handle malicious video files gracefully
- No network operations in MVP
- All processing local

## Performance Considerations

- Preview frame extraction on-demand (not all videos)
- Cache preview frames in memory
- Limit concurrent workers (default: 2-4)
- Stream FFmpeg output rather than buffering
- Use hardware acceleration when available

## Extension Points

### Future Processing Modes
- Add new mode to Processor
- Add UI controls in Controls
- Extend selection model if needed

### Future Selection Tools
- Polygon selection extends Selection model
- Brush selection adds mask model
- PreviewCanvas handles different drawing modes

### Future Platforms
- Abstract FFmpeg path detection
- Platform-specific packaging
- Conditional imports for optional features
