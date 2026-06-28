# ReelBatch Editor — Status

## Current Stage

Phase 2: UI skeleton complete. Ready for video processing implementation.

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

## Current Goal

Implement video import and preview functionality (Phase 3).

## Next Steps

1. Implement video file import using QFileDialog
2. Add OpenCV integration for preview frame extraction
3. Display video metadata in the queue
4. Implement rectangle selection on preview canvas
5. Store selection as normalized percentages

## MVP Features

* [x] Create PySide6 app skeleton
* [x] Add modern main window layout
* [x] Add video import button
* [x] Add video queue/list
* [ ] Extract preview frame from first video
* [x] Add preview canvas
* [ ] Allow rectangle selection on preview
* [ ] Store rectangle as normalized percentages
* [x] Add output folder picker
* [ ] Add blur selected area export mode
* [ ] Add logo/image overlay export mode
* [ ] Add zoom/crop export mode
* [x] Add batch export progress
* [ ] Add error handling
* [x] Add preset save/load
* [ ] Package as Windows EXE

## Current Decisions

* Target platform: Windows only for MVP
* UI: PySide6
* Video engine: FFmpeg
* Preview/dimensions: OpenCV
* Packaging: PyInstaller
* First selection tool: rectangle only

## Not in MVP

* Android APK
* Polygon mask
* Brush mask
* Timeline editor
* Audio editor
* Cloud upload
* AI video generation
