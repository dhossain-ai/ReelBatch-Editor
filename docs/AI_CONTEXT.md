# ReelBatch Editor — AI Context

## Project Summary

ReelBatch Editor is a Windows desktop batch video editing tool for short vertical reels. The goal is to help creators process many videos at once by applying the same cleanup or branding operation to all imported clips.

The app is not intended to be a full timeline video editor like CapCut or Premiere. It is a focused batch automation tool.

## Main Use Case

The user creates many short AI-generated reel videos. These videos often have a logo or watermark in the same fixed area. Manually editing each video in CapCut takes too much time.

The app should allow the user to:

1. Import multiple MP4 videos.
2. Preview a video frame.
3. Select the logo/watermark area once.
4. Apply one operation to all videos:

   * blur selected area,
   * cover selected area with a custom logo/image,
   * zoom/crop the video slightly.
5. Export all processed videos automatically.

## Current Target Platform

Windows desktop only.

Future platforms such as Android or macOS are not part of the MVP.

## Preferred Tech Stack

* Python
* PySide6 for GUI
* FFmpeg for video processing
* OpenCV only for reading preview frames and video dimensions
* PyInstaller later for Windows EXE packaging

## Product Scope

This is a batch video processor, not a general video editor.

MVP should include:

* multi-video import,
* output folder selection,
* preview canvas,
* rectangle selection,
* blur selected area,
* logo/image overlay,
* zoom/crop,
* batch export,
* progress/status display,
* preset save/load.

Do not add timeline editing, audio editing, Android support, cloud upload, AI generation, or complex effects in the MVP.

## Coordinate Rule

Selection coordinates must be stored as normalized percentages of video width and height, not absolute pixels. This allows the same selected area to work on videos with different resolutions.

Example:
{
"x_percent": 82.5,
"y_percent": 4.0,
"width_percent": 14.0,
"height_percent": 6.0
}

During export, convert these normalized values back to real pixel coordinates for each video.

## Export Engine

The app should generate FFmpeg commands and run them through Python subprocess.

The UI should not perform heavy video processing directly. Heavy work must happen in a background worker/thread so the UI does not freeze.

## Development Principle

Build functionality first, then polish UI.

Start with rectangle selection only. Polygon and brush tools are future features.
