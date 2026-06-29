# ReelBatch Editor

A Windows desktop batch video editing tool for short vertical reels. Import multiple MP4 videos, select a fixed logo/watermark area once, preview and test the result, then build a clear export recipe with toggleable blur, logo/image overlay, zoom/crop, and output-size standardization before exporting.

## Problem It Solves

Creators who produce many short AI-generated reel videos often need to hide or replace a fixed logo/watermark area that appears in the same position across all videos. Manually editing each video in CapCut or similar editors is time-consuming and inefficient.

ReelBatch Editor automates this process by letting you:
- Import many videos at once
- Preview and scrub through a clip before exporting
- Select the target area once
- Apply the same edit to all videos automatically
- Test one clip before committing to the full batch
- Export processed videos in batch

## MVP Features

- **Multi-video import** - Add multiple MP4 files to the processing queue
- **Video queue/list** - View and manage imported videos with metadata
- **Guided export recipe workflow** - Follow `Add videos -> Draw area -> Choose options -> Export`
- **Preview canvas** - See and scrub through preview frames to identify logo/watermark areas
- **Preview playback** - Play/pause video-only preview with an OpenCV-based timeline
- **Rectangle selection** - Draw a rectangular selection over the target area
- **Normalized coordinates** - Selection stored as percentages, works across different resolutions
- **Blur export** - Export MP4 files with the selected rectangle blurred via FFmpeg
- **Logo/image overlay export** - Cover the selected rectangle with a user-selected image
- **Zoom/crop export** - Scale the video up and center-crop back to the original dimensions
- **Toggle-based export recipe** - Turn Area Cleanup, Zoom/crop, and Output Size on or off independently
- **Live recipe summary** - See exactly what will apply before starting export
- **Encoder selection** - Auto prefers NVIDIA NVENC and falls back to CPU/libx264 when needed
- **Stacked export pipeline** - Apply blur or logo cleanup, then optional zoom/crop, then optional output-size standardization in one FFmpeg command
- **Batch export** - Process all videos automatically with progress display
- **Test export current video** - Export only the selected clip before running the whole queue
- **Output resolution standardization** - Standardize mixed reels to `720x1280`, `1080x1920`, `1440x2560`, or a custom even-numbered size
- **Resize mode control** - Choose `Fill & Crop` for full-frame vertical reels or `Fit with Padding` to preserve the entire source frame
- **Background processing** - UI remains responsive during export
- **Preset save/load** - Save your selections and settings for reuse
- **Remembered workflow settings** - Restore your last recipe toggles, encoder, quality, sliders, and output folder on next launch
- **Output quality presets** - Choose Fast, Balanced, or High Quality without manual bitrate tuning
- **Export logs and polished summaries** - Save compact batch logs and open the output folder directly after export

## Tech Stack

- **Language:** Python 3.10+
- **GUI:** PySide6 (Qt6)
- **Video processing:** FFmpeg
- **Frame extraction:** OpenCV
- **Packaging:** PyInstaller (for Windows EXE)

## Roadmap Summary

### Phase 1: MVP (In Progress)
Windows desktop batch editor with rectangle selection and three processing modes.
- **1.1 Project Setup:** ✅ Complete
- **1.2 Core UI:** ✅ Complete  
- **1.3 Video Processing:** Next
- **1.4 Export Features:** Pending
- **1.5 Polish:** Pending

### Phase 2: GPU Acceleration
Add NVIDIA NVENC support for faster exports with automatic CPU fallback.

### Phase 3: Video Import & Preview
Import multiple videos, read metadata, and preview a frame from the selected clip.

### Phase 4: Advanced Selection
Add polygon and brush selection tools for more flexible masking.

### Phase 5: Enhanced Features
Presets system, batch operations, advanced export options.

### Phase 5: Cross-Platform
macOS and Linux support.

### Not in Scope
Timeline editing, audio editing, Android app, cloud upload, AI video generation.

See [docs/ROADMAP.md](docs/ROADMAP.md) for detailed roadmap.

## Current Status

**Stage:** Phase 7.7 complete - toggle-based export recipes now layer area cleanup, zoom/crop, and output-size standardization in one workflow.

**Progress:**
- [x] GitHub repository initialized
- [x] Documentation structure created
- [x] Core UI implementation (PySide6 with dark theme)
- [x] Video import, metadata reading, and preview integration
- [x] Rectangle selection overlay with normalized percentage storage
- [x] Selection values shown in the Edit Settings panel
- [x] Coordinate conversion tests for scaled and letterboxed previews
- [x] FFmpeg blur, logo/image overlay, and zoom/crop export workflows
- [x] Output folder selection and collision-safe output naming
- [x] Auto encoder selection with NVENC-to-libx264 fallback
- [x] JSON preset save/load with optional preset export/import
- [x] Persistent app settings for recipe toggles, encoder, quality, sliders, and output folder
- [x] Output quality presets for Fast, Balanced, and High Quality
- [x] Output resolution standardization for `Keep original`, `720x1280`, `1080x1920`, `1440x2560`, and custom even-numbered sizes
- [x] Resize modes for `Fill & Crop` and `Fit with Padding`
- [x] Export summary polish with output-folder opening and compact log files
- [x] Reorganized the right panel into Export Recipe, Area Cleanup, Optional Zoom, Output Size, Export Settings, and Presets
- [x] OpenCV-based preview playback with play/pause, scrubbing, and duration labels
- [x] Test Export Current Video button for validating one clip before batch export
- [ ] Windows EXE packaging

The app now supports importing multiple videos, drawing a reusable normalized selection, building a clearer toggle-based export recipe, previewing and scrubbing clips before export, standardizing outputs to common vertical reel sizes, saving reusable presets, test-exporting one selected video, and exporting MP4 outputs in the background while keeping the UI responsive.

See [docs/STATUS.md](docs/STATUS.md) for detailed task checklist.

## Development Notes

### Coordinate System
Selection coordinates are stored as **normalized percentages** (0-100) of video width and height, not absolute pixels. This ensures the same selection works correctly across videos with different resolutions.

Example:
```json
{
  "x_percent": 82.5,
  "y_percent": 4.0,
  "width_percent": 14.0,
  "height_percent": 6.0
}
```

### GPU Acceleration
The app will support NVIDIA NVENC for hardware-accelerated export:
- Default encoder mode: "Auto"
- Auto prefers NVENC when available
- Falls back to CPU/libx264 if NVENC unavailable or fails
- GPU improves speed but CPU fallback ensures compatibility

### Architecture
The app uses a layered architecture:
- **UI layer** (PySide6) - Main window, preview canvas, controls
- **Video processing layer** - FFmpeg command generation, background workers
- **Data models** - Video items, selections, presets
- **Utilities** - FFmpeg detection, coordinate conversion, configuration

Heavy video processing runs in background threads to keep the UI responsive. Preview playback stays lightweight by using OpenCV frame reads plus a `QTimer`, without introducing Qt Multimedia.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture.

## Documentation

- [AI_CONTEXT.md](docs/AI_CONTEXT.md) - Project context and guidelines for AI agents
- [STATUS.md](docs/STATUS.md) - Current development status and task checklist
- [PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) - Product specification and user workflows
- [ROADMAP.md](docs/ROADMAP.md) - Development phases and feature timeline
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical architecture and component design
- [DEV_PROMPTS.md](docs/DEV_PROMPTS.md) - Curated prompts for AI-assisted development
- [TEST_PLAN.md](docs/TEST_PLAN.md) - Testing strategy and test cases

## Getting Started (Development)

### Prerequisites
- Python 3.10 or higher
- FFmpeg (will be bundled or detected)
- NVIDIA GPU with latest drivers (for NVENC, optional)

### Setup
```bash
# Clone the repository
git clone https://github.com/dhossain-ai/ReelBatch-Editor.git
cd "ReelBatch Editor"

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the App
```bash
python main.py
```

The app will launch with a modern dark UI showing the video queue, preview canvas with playback controls, and a creator-focused workflow panel.

## Building Windows EXE

```bash
# Using PyInstaller (to be configured)
pyinstaller main.spec
```

The EXE will include FFmpeg and all dependencies for standalone execution.

## Contributing

This project is currently in early development. Contributions will be welcome after the MVP is released.

## License

To be determined.

## Target Users

- Facebook Reels creators
- TikTok/Shorts creators
- AI video creators
- Social media page managers
- Small content teams processing many short videos

## Success Criteria

The MVP is successful if a user can process at least 10 vertical MP4 reels automatically without manually editing each video one by one.
