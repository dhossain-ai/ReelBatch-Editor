# ReelBatch Editor — Status

## Current Stage

Phase 5: Blur export workflow complete. Ready for logo overlay and zoom/crop export work.

## Phase 2 Completed (UI Skeleton)

- [x] Created PySide6 app skeleton with main.py entry point
- [x] Implemented modern dark theme UI layout with three panels
- [x] Added video queue widget with placeholder list and buttons
- [x] Added preview canvas widget (ready for rectangle selection)
- [x] Added edit settings panel with all controls
- [x] Added processing mode dropdown (blur/logo/zoom)
- [x] Added encoder selection (Auto/CPU/NVIDIA)
- [x] Added output folder picker
- [x] Added preset save/load buttons
- [x] Added progress bar and status display
- [x] Added export button
- [x] Created comprehensive dark theme stylesheet
- [x] Added placeholder signal handlers for all buttons
- [x] App launches successfully from `python main.py`

## Phase 3 Completed (Video Import & Preview)

- [x] Added opencv-python dependency to requirements.txt
- [x] Created core/video_probe.py with VideoInfo dataclass
- [x] Implemented video metadata reading using OpenCV
- [x] Implemented preview frame extraction (prefers 1 second, falls back to first frame)
- [x] Added BGR to RGB conversion for Qt compatibility
- [x] Updated video queue to display metadata (filename — resolution — duration)
- [x] Added video selection signal to queue widget
- [x] Implemented duplicate file detection in queue
- [x] Updated preview canvas to display QImage with aspect ratio preservation
- [x] Added preview scaling for different video resolutions
- [x] Implemented video import via QFileDialog with multiple file selection
- [x] Added support for .mp4, .mov, .mkv, .avi file formats
- [x] Automatic preview of first imported video
- [x] Preview updates when user selects different video in queue
- [x] Clear queue resets preview canvas
- [x] Added error handling for unreadable video files
- [x] Added user-friendly error messages for import failures
- [x] Status bar shows import results and selected video info

## Phase 4 Completed (Rectangle Selection)

- [x] Added mouse-driven rectangle selection on the preview canvas
- [x] Limited selection to the displayed video image area
- [x] Handled scaled previews with letterboxing/padding correctly
- [x] Stored selection as normalized video percentages
- [x] Ignored tiny accidental selections below the drag threshold
- [x] Kept selection visible after mouse release and window resize
- [x] Added preview canvas selection signal and public selection API
- [x] Added Selection controls and values to the Edit Settings panel
- [x] Preserved normalized selection when switching videos in the queue
- [x] Added unit tests for preview-to-video coordinate conversion math

## Phase 5 Completed (Blur Export)

- [x] Added FFmpeg availability checks with user-facing error handling
- [x] Added encoder detection for h264_nvenc, h264_qsv, h264_amf, and libx264
- [x] Implemented Auto encoder mode with NVIDIA preference and CPU fallback
- [x] Implemented blur export command generation using filter_complex
- [x] Converted normalized selection coordinates to clamped video pixel rectangles
- [x] Preserved audio when present and exported video-only when audio is missing
- [x] Added unique `_blurred.mp4` output naming with numeric collision suffixes
- [x] Added background batch export worker so the UI stays responsive
- [x] Added export validation for queue, output folder, mode, and selection
- [x] Added per-file failure handling and final export summary reporting
- [x] Added unit tests for FFmpeg command generation and encoder selection logic

## Current Goal

Implement the remaining export modes that reuse the normalized selection data.

## Next Steps

1. Implement logo/image overlay export using the normalized selection rectangle
2. Implement zoom/crop export mode
3. Persist selection and mode settings in presets
4. Improve export reporting and optional cancellation controls
5. Package the Windows build after export modes are complete

## MVP Features

* [x] Create PySide6 app skeleton
* [x] Add modern main window layout
* [x] Add video import button
* [x] Add video queue/list
* [x] Extract preview frame from first video
* [x] Add preview canvas
* [x] Allow rectangle selection on preview
* [x] Store rectangle as normalized percentages
* [x] Add output folder picker
* [x] Add blur selected area export mode
* [ ] Add logo/image overlay export mode
* [ ] Add zoom/crop export mode
* [x] Add batch export progress
* [x] Add error handling
* [x] Add preset save/load
* [ ] Package as Windows EXE

## Current Decisions

* Target platform: Windows only for MVP
* UI: PySide6
* Video engine: FFmpeg
* Preview/dimensions: OpenCV
* Packaging: PyInstaller
* First selection tool: rectangle only
* Selection storage: normalized percentages with preview-space clamping
* First export mode: blur selected area only
* Auto encoder mode: prefer NVENC, retry with libx264 on failure when available

## Not in MVP

* Android APK
* Polygon mask
* Brush mask
* Timeline editor
* Audio editor
* Cloud upload
* AI video generation
