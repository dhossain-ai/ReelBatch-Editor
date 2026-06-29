# ReelBatch Editor

A Windows desktop batch video editing tool for short vertical reels. Import multiple MP4 videos, select a fixed logo/watermark area once, then automatically apply blur, logo/image overlay, or zoom/crop and export all videos.

## Problem It Solves

Creators who produce many short AI-generated reel videos often need to hide or replace a fixed logo/watermark area that appears in the same position across all videos. Manually editing each video in CapCut or similar editors is time-consuming and inefficient.

ReelBatch Editor automates this process by letting you:
- Import many videos at once
- Select the target area once
- Apply the same edit to all videos automatically
- Export processed videos in batch

## MVP Features

- **Multi-video import** - Add multiple MP4 files to the processing queue
- **Video queue/list** - View and manage imported videos with metadata
- **Preview canvas** - See the first frame of videos to identify logo/watermark areas
- **Rectangle selection** - Draw a rectangular selection over the target area
- **Normalized coordinates** - Selection stored as percentages, works across different resolutions
- **Three processing modes:**
  1. **Blur** - Blur the selected area to hide logos/watermarks
  2. **Logo overlay** - Cover the selected area with your own logo or image
  3. **Zoom/crop** - Slightly zoom and crop the video
- **Batch export** - Process all videos automatically with progress display
- **Background processing** - UI remains responsive during export
- **Preset save/load** - Save your selections and settings for reuse

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

**Stage:** Phase 4 complete - normalized rectangle selection is now implemented on the preview canvas.

**Progress:**
- [x] GitHub repository initialized
- [x] Documentation structure created
- [x] Core UI implementation (PySide6 with dark theme)
- [x] Video import, metadata reading, and preview integration
- [x] Rectangle selection overlay with normalized percentage storage
- [x] Selection values shown in the Edit Settings panel
- [x] Coordinate conversion tests for scaled and letterboxed previews
- [ ] FFmpeg processing/export functionality
- [ ] Windows EXE packaging

The app now supports importing multiple videos, previewing frames, drawing a reusable rectangle selection, and keeping that selection consistent across resize events and video switches.

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

Heavy video processing runs in background threads to keep the UI responsive.

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

The app will launch with a modern dark UI showing the video queue, preview canvas, and edit settings panels.

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
