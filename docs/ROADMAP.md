# ReelBatch Editor — Roadmap

## Phase 1: MVP (Current)

**Goal:** Windows desktop batch video editor with basic rectangle selection and three processing modes.

### 1.1 Project Setup
- [x] Initialize GitHub repository
- [x] Create documentation structure
- [ ] Set up Python virtual environment
- [ ] Install dependencies (PySide6, OpenCV, FFmpeg)
- [ ] Create basic PySide6 app skeleton
- [ ] Verify FFmpeg integration

### 1.2 Core UI
- [ ] Design main window layout
- [ ] Add video import button and file dialog
- [ ] Create video queue/list widget
- [ ] Add output folder picker
- [ ] Create preview canvas widget
- [ ] Implement rectangle selection tool
- [ ] Add processing mode selector (blur/logo/zoom)
- [ ] Add settings panel for each mode
- [ ] Add export button
- [ ] Add progress bar and status label

### 1.3 Video Processing
- [ ] Extract preview frame using OpenCV
- [ ] Get video dimensions
- [ ] Store rectangle as normalized percentages
- [ ] Generate FFmpeg blur command
- [ ] Generate FFmpeg logo overlay command
- [ ] Generate FFmpeg zoom/crop command
- [ ] Implement background worker for FFmpeg
- [ ] Handle FFmpeg output and errors
- [ ] Update UI from worker thread

### 1.4 Export Features
- [ ] Batch export all videos
- [ ] Show per-video progress
- [ ] Handle export errors gracefully
- [ ] Add cancel button for long exports
- [ ] Auto-increment output filenames if needed

### 1.5 Polish
- [ ] Add preset save/load
- [ ] Improve error messages
- [ ] Add basic validation
- [ ] Test with various video resolutions
- [ ] Test with different aspect ratios
- [ ] Package as Windows EXE with PyInstaller

## Phase 2: GPU Acceleration

**Goal:** Add NVIDIA NVENC support for faster exports.

### 2.1 GPU Detection
- [ ] Detect NVIDIA GPU availability
- [ ] Detect FFmpeg NVENC support
- [ ] Add encoder mode selector (Auto/NVENC/CPU)
- [ ] Implement Auto mode logic (prefer NVENC, fallback to CPU)

### 2.2 NVENC Integration
- [ ] Generate NVENC FFmpeg commands
- [ ] Test NVENC export on RTX 4060
- [ ] Implement fallback mechanism
- [ ] Add encoder status indicator
- [ ] Benchmark CPU vs GPU performance

## Phase 3: Advanced Selection Tools

**Goal:** Add polygon and brush selection for more flexible masking.

### 3.1 Polygon Selection
- [ ] Add polygon drawing tool
- [ ] Store polygon points as normalized coordinates
- [ ] Generate FFmpeg polygon mask commands
- [ ] Test polygon blur/overlay

### 3.2 Brush Selection
- [ ] Add brush/paint tool
- [ ] Create mask from brush strokes
- [ ] Generate FFmpeg mask commands
- [ ] Test brush-based blur/overlay

## Phase 4: Enhanced Features

**Goal:** Add quality-of-life improvements and advanced capabilities.

### 4.1 Presets System
- [ ] Named presets with descriptions
- [ ] Import/export presets
- [ ] Preset templates for common use cases
- [ ] Preset management UI

### 4.2 Batch Operations
- [ ] Process multiple batches in queue
- [ ] Save/load batch configurations
- [ ] Batch rename outputs
- [ ] Apply different operations to different videos

### 4.3 Advanced Export
- [ ] Custom output resolution
- [ ] Quality/bitrate settings
- [ ] Format selection (MP4/MOV/WebM)
- [ ] Frame rate control
- [ ] Audio handling options

## Phase 5: Cross-Platform

**Goal:** Support macOS and Linux.

### 5.1 macOS
- [ ] Test on macOS
- [ ] Handle macOS-specific FFmpeg paths
- [ ] Create macOS app bundle
- [ ] Code signing and notarization

### 5.2 Linux
- [ ] Test on Ubuntu/Debian
- [ ] Create AppImage package
- [ ] Handle FFmpeg dependencies
- [ ] Test on various distributions

## Phase 6: Mobile (Future)

**Goal:** Android app for on-the-go editing.

### 6.1 Android MVP
- [ ] Research Android video editing libraries
- [ ] Design mobile UI
- [ ] Implement core features
- [ ] Test on various Android devices

## Not Planned

The following features are explicitly out of scope for the foreseeable future:

- Timeline editor (use CapCut/Premiere instead)
- Audio editor (use dedicated audio tools)
- Cloud upload integration
- AI video generation
- Social media API integration
- Collaborative editing
- Real-time preview during editing

## Timeline Notes

- Phase 1 (MVP) is the current priority
- Subsequent phases will be planned based on user feedback
- Each phase should be released and tested before starting the next
- Technical debt should be addressed between phases
