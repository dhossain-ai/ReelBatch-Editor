# ReelBatch Editor — Status

## Current Stage

Project initialized on GitHub. MVP planning is in progress.

## Current Goal

Build a Windows desktop MVP that can import multiple MP4 reels, let the user select a fixed rectangular logo/watermark area, then batch export processed videos.

## MVP Features

* [ ] Create PySide6 app skeleton
* [ ] Add modern main window layout
* [ ] Add video import button
* [ ] Add video queue/list
* [ ] Extract preview frame from first video
* [ ] Add preview canvas
* [ ] Allow rectangle selection on preview
* [ ] Store rectangle as normalized percentages
* [ ] Add output folder picker
* [ ] Add blur selected area export mode
* [ ] Add logo/image overlay export mode
* [ ] Add zoom/crop export mode
* [ ] Add batch export progress
* [ ] Add error handling
* [ ] Add preset save/load
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
