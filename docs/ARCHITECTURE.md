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

#### PreviewCanvas
- Displays video preview frame
- Handles mouse events for rectangle selection
- Draws selection rectangle overlay
- Converts between screen and normalized coordinates
- Uses the fitted preview image rect, not the full widget bounds, when mapping selection coordinates

#### VideoList
- Displays queue of imported videos
- Shows video metadata (filename, resolution, duration)
- Allows reordering and removal
- Signals selection changes to MainWindow

#### Controls
- Processing mode selector (blur/logo/zoom)
- Settings panels for each mode
- Export button and progress indicator
- Output folder picker

### Video Processing Layer

#### Processor
- Generates FFmpeg commands based on selected mode
- Handles coordinate conversion (normalized → pixels)
- Supports three processing modes:
  - Blur: Uses FFmpeg `boxblur` or `gblur` filter
  - Logo overlay: Uses FFmpeg `overlay` filter
  - Zoom/crop: Uses FFmpeg `scale` and `crop` filters
- Generates encoder-specific commands (NVENC vs CPU)
- Resolves Auto encoder mode by preferring `h264_nvenc` and falling back to `libx264` when needed

#### Worker
- QThread-based background worker
- Executes FFmpeg commands via subprocess
- Streams FFmpeg output to UI
- Handles process cancellation
- Reports progress and errors
- Ensures UI remains responsive during export
- Continues exporting later files even if one file fails

#### Preview
- Extracts first frame from video using OpenCV
- Gets video dimensions and metadata
- Converts frames to Qt-compatible format
- Caches preview frames for performance

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
- Serializable to/from JSON

### Utilities

#### FFmpeg
- Detects FFmpeg installation
- Validates FFmpeg version
- Checks for NVENC support
- Provides FFmpeg path abstraction

#### Coordinates
- Converts between pixel and normalized coordinates
- Handles aspect ratio calculations
- Validates coordinate ranges

#### Config
- Manages application settings
- Stores recent paths
- Stores user preferences
- Persists to JSON/config file

## Data Flow

### Import Flow
1. User selects MP4 files via file dialog
2. VideoList creates VideoItem instances
3. Preview extracts first frame from first video
4. PreviewCanvas displays frame
5. User draws rectangle on PreviewCanvas
6. Selection stores normalized coordinates

### Export Flow
1. User selects processing mode and settings
2. MainWindow validates queue, output folder, selection, and FFmpeg availability
3. MainWindow resolves the encoder plan (Auto/CPU/NVIDIA)
4. User clicks Export button
5. MainWindow creates a background Worker for the batch
6. Worker generates a blur command for each video via Processor
7. Worker executes FFmpeg in subprocess
8. If Auto mode fails on NVENC, Worker retries that file with `libx264`
9. UI updates progress bar and status text
10. On completion, Worker signals success/failure summary back to MainWindow

## Threading Model

### Main Thread (UI)
- Runs PySide6 event loop
- Handles all UI updates
- Responds to user input
- Must never block

### Worker Threads
- One worker per export operation
- Can run multiple workers in parallel (configurable)
- Communicate with UI via Qt signals/slots
- Use subprocess to run FFmpeg (non-blocking)

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
ffmpeg -i input.mp4 -i logo.png -filter_complex "overlay=x:y" output.mp4

# Zoom/crop example
ffmpeg -i input.mp4 -vf "scale=iw*1.1:ih*1.1,crop=iw:ih:(iw-iw)/2:(ih-ih)/2" output.mp4
```

### NVENC Detection
```python
ffmpeg -encoders
```

The application scans the encoder list for:
- `h264_nvenc`
- `h264_qsv`
- `h264_amf`
- `libx264`

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
- Presets saved to JSON
- Recent paths saved to config
- Selection auto-saved per session

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
