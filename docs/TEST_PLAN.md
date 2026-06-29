# ReelBatch Editor — Test Plan

## Testing Strategy

ReelBatch Editor requires testing at multiple levels:
1. **Unit tests** for individual components
2. **Integration tests** for workflows
3. **Manual UI tests** for user experience
4. **Performance tests** for export speed
5. **Compatibility tests** for different video formats

## Test Environment

### Development Machine
- OS: Windows 10/11
- GPU: NVIDIA RTX 4060 (for NVENC testing)
- Python: 3.10+
- FFmpeg: Latest stable build

### Test Assets
Create a test video suite with:
- Vertical videos (9:16 aspect ratio)
- Different resolutions: 720x1280, 1080x1920, 1440x2560
- Different codecs: H.264, H.265
- Different durations: 5s, 15s, 30s, 60s
- Videos with logo/watermark in various positions
- Sample logo images (PNG with transparency)

## Unit Tests

### Coordinate Conversion Tests
**File:** `tests/test_coordinates.py`

Test cases:
- [ ] Convert normalized (0-100) to pixels for various resolutions
- [ ] Convert pixels back to normalized
- [ ] Round-trip conversion accuracy
- [ ] Edge cases: 0%, 100%, negative values, values > 100
- [ ] Different aspect ratios
- [ ] Validation of coordinate ranges

### Selection Model Tests
**File:** `tests/test_selection.py`

Test cases:
- [ ] Create selection with valid normalized coordinates
- [ ] Reject invalid coordinates (negative, > 100)
- [ ] Reject zero/negative width or height
- [ ] Convert selection to pixels for different video sizes
- [ ] Serialization to/from JSON
- [ ] Copy/clone selection

### Video Item Tests
**File:** `tests/test_video_item.py`

Test cases:
- [ ] Create video item with valid path
- [ ] Extract metadata using OpenCV
- [ ] Handle missing or corrupt video files
- [ ] Store and retrieve export status
- [ ] Generate output filename
- [ ] Handle duplicate filenames

### FFmpeg Command Generation Tests
**File:** `tests/test_processor.py`

Test cases:
- [x] Generate blur command with correct filter
- [x] Generate logo overlay command with correct positioning
- [x] Generate zoom/crop command with correct scale
- [x] Use normalized coordinates in commands
- [x] Generate NVENC commands when GPU available
- [x] Generate CPU commands as fallback
- [x] Map quality presets to encoder-specific arguments
- [ ] Escape special characters in paths
- [ ] Handle paths with spaces

### Preset Tests
**File:** `tests/test_preset.py`

Test cases:
- [x] Create preset with selection and mode
- [x] Serialize preset to JSON
- [x] Deserialize preset from JSON
- [ ] Handle missing or invalid preset files
- [ ] Validate preset data structure
- [ ] Copy/clone preset

### Settings Persistence Tests
**File:** `tests/test_app_settings.py`

Test cases:
- [x] Load default settings when no settings file exists
- [x] Save app settings to JSON
- [x] Restore app settings from JSON
- [ ] Handle invalid settings files gracefully

## Integration Tests

### Import Workflow Tests
**File:** `tests/test_import_workflow.py`

Test cases:
- [ ] Import single MP4 file
- [ ] Import multiple MP4 files
- [ ] Import non-video files (should reject)
- [ ] Import corrupt video files (should handle gracefully)
- [ ] Video list updates correctly
- [ ] Preview frame extracted for first video
- [ ] Video metadata displayed correctly

### Selection Workflow Tests
**File:** `tests/test_selection_workflow.py`

Test cases:
- [ ] Draw rectangle on preview canvas
- [ ] Selection coordinates stored as normalized
- [ ] Selection visible on canvas
- [ ] Clear selection
- [ ] Resize selection
- [ ] Move selection
- [ ] Selection persists across video changes

### Export Workflow Tests
**File:** `tests/test_export_workflow.py`

Test cases:
- [ ] Export single video with blur
- [ ] Export single video with logo overlay
- [ ] Export single video with zoom/crop
- [ ] Export multiple videos in batch
- [ ] Export with custom output folder
- [ ] Export with filename conflicts (auto-increment)
- [ ] Cancel export during processing
- [ ] Export progress updates correctly
- [ ] Export completes successfully
- [ ] Output video is valid and playable
- [x] Validate blur requires a selection
- [x] Validate logo/image requires both a selection and a supported image file
- [x] Validate zoom/crop does not require a selection

### FFmpeg Integration Tests
**File:** `tests/test_ffmpeg_integration.py`

Test cases:
- [x] Detect FFmpeg installation
- [ ] Detect FFmpeg version
- [x] Detect NVENC support
- [ ] Execute simple FFmpeg command
- [ ] Parse FFmpeg output
- [ ] Handle FFmpeg errors
- [x] Fallback to CPU when NVENC unavailable

## Manual UI Tests

### User Interface Tests
**Checklist:**

#### Main Window
- [ ] Window opens without errors
- [ ] Window title displays correctly
- [ ] Window is resizable
- [ ] Layout adapts to resizing
- [ ] All controls are visible and accessible

#### Video Import
- [ ] Import button opens file dialog
- [ ] File dialog filters for MP4 files
- [ ] Multiple selection works
- [ ] Imported videos appear in list
- [ ] Video list shows filenames
- [ ] Video list shows metadata (resolution, duration)
- [ ] Can remove videos from list
- [ ] Can clear entire list

#### Preview Canvas
- [ ] Preview displays first video frame
- [ ] Preview updates when selecting different video
- [ ] Preview playback controls appear under the preview
- [ ] Play/Pause toggles video-only preview playback
- [ ] Timeline slider scrubs to a new frame
- [ ] Current time / total duration label updates while playing and scrubbing
- [ ] Can draw rectangle with mouse
- [ ] Rectangle appears while drawing
- [ ] Rectangle remains after drawing
- [ ] Rectangle remains visible while preview playback is moving
- [ ] Can clear selection
- [ ] Preview scales with window size

#### Controls
- [ ] Area Cleanup dropdown works (`None`, `Blur selected area`, `Cover with logo/image`)
- [ ] Right settings panel is grouped into Area Cleanup, Transform, Output, and Presets
- [ ] Workflow hint text updates as the user progresses
- [ ] Conditional controls show/hide cleanly for blur and logo/image cleanup
- [ ] Apply zoom/crop checkbox works
- [ ] Blur intensity slider works
- [ ] Logo file picker works
- [ ] Zoom percentage slider works
- [ ] Zoom slider is de-emphasized or disabled when zoom is inactive
- [ ] Output Resolution dropdown works
- [ ] Resize Mode dropdown works
- [ ] Custom width/height inputs appear only when Custom output resolution is selected
- [ ] Output quality dropdown works
- [ ] Encoder help text/tooltips explain Auto NVENC behavior
- [ ] Tooltips appear on key controls
- [x] Output folder picker works
- [ ] Export button is enabled when ready
- [ ] Test Export Current Video button is available when a video is selected

#### Export
- [x] Progress bar appears during export
- [x] Progress updates for each video
- [x] Status text shows current operation
- [ ] Queue items show useful status text during or after export
- [ ] Cancel button stops export
- [x] Success message appears on completion
- [x] Error message appears on failure
- [ ] Output folder opens on completion (optional)

### Phase 7.5 Manual Workflow Tests

#### Preview Playback
1. [ ] Launch the app and import at least one playable video
2. [ ] Select a queue item and confirm the preview loads with playback controls beneath it
3. [ ] Click `Play` and confirm the preview advances frame-by-frame without audio
4. [ ] Click `Pause` and confirm playback stops on the current frame
5. [ ] Confirm the current time / total duration label updates while playing

#### Timeline Scrubbing
1. [ ] Select a video with at least 10 seconds of duration
2. [ ] Drag the timeline slider to several positions
3. [ ] Confirm the preview jumps to the chosen frame
4. [ ] Confirm the current time label matches the scrubbed position
5. [ ] Start playback, scrub to another point, and confirm playback resumes cleanly if it was running before the drag

#### Draw Selection While Paused
1. [ ] Load a video and pause the preview
2. [ ] Draw a rectangle on the preview canvas
3. [ ] Confirm the rectangle remains visible after mouse release
4. [ ] Play the preview and confirm the rectangle stays visible over changing frames
5. [ ] Pause again and resize the window to confirm the rectangle still tracks correctly

#### Switch Videos
1. [ ] Import at least two videos
2. [ ] Start preview playback on the first video
3. [ ] Select a different queue item
4. [ ] Confirm playback stops automatically
5. [ ] Confirm the newly selected video loads with its own preview timeline state
6. [ ] Click `Clear Queue` and confirm preview playback stops, the preview resets, and playback controls return to an empty state

#### Test Export Current Video
1. [ ] Import at least two videos and select one
2. [ ] Choose a valid Area Cleanup or enable `Apply zoom/crop`
3. [ ] Select an output folder and any required logo/image file
4. [ ] Click `Test Export Current Video`
5. [ ] Confirm only the selected video is exported
6. [ ] Confirm the completion summary reports one total file
7. [ ] Confirm the queue item shows a useful completion status such as done or CPU fallback

#### Export All Still Works
1. [ ] Import multiple videos after verifying test export
2. [ ] Run `Export All`
3. [ ] Confirm all queued videos are processed
4. [ ] Confirm queue item statuses update per file
5. [ ] Confirm blur, logo/image, and zoom/crop modes still behave as before

### Phase 7.6 Manual Output Resolution Tests

#### 720x1280 To 1080x1920 Fill & Crop
1. [ ] Import a `720x1280` vertical video
2. [ ] Select `1080x1920` as Output Resolution
3. [ ] Leave Resize Mode on `Fill & Crop`
4. [ ] Run `Test Export Current Video`
5. [ ] Confirm the exported file is `1080x1920` and fills the frame without distortion

#### 720x1280 To 1080x1920 Fit With Padding
1. [ ] Import a `720x1280` vertical video
2. [ ] Select `1080x1920` as Output Resolution
3. [ ] Change Resize Mode to `Fit with Padding`
4. [ ] Run `Test Export Current Video`
5. [ ] Confirm the exported file is `1080x1920`, preserves the whole source frame, and pads empty space cleanly

#### 1080x1920 To 1080x1920
1. [ ] Import a `1080x1920` video
2. [ ] Leave Output Resolution on `1080x1920`
3. [ ] Run `Test Export Current Video`
4. [ ] Confirm the exported file remains `1080x1920`
5. [ ] Confirm there is no aspect-ratio distortion

#### Blur + 1080x1920
1. [ ] Import a video, draw a valid rectangle, and choose `Blur selected area`
2. [ ] Set Output Resolution to `1080x1920`
3. [ ] Run `Test Export Current Video`
4. [ ] Confirm the selected area is blurred and the final output is `1080x1920`

#### Logo Overlay + 1080x1920
1. [ ] Import a video, draw a valid rectangle, and choose `Cover with logo/image`
2. [ ] Pick a supported logo/image file
3. [ ] Set Output Resolution to `1080x1920`
4. [ ] Run `Test Export Current Video`
5. [ ] Confirm the overlay is applied and the final output is `1080x1920`

#### Zoom/Crop + 1080x1920
1. [ ] Import a video and enable `Apply zoom/crop`
2. [ ] Set a zoom value above `100%`
3. [ ] Set Output Resolution to `1080x1920`
4. [ ] Run `Test Export Current Video`
5. [ ] Confirm the zoom/crop effect still applies and the final output is `1080x1920`

### Phase 7 Manual Workflow Tests

#### Preset Save/Load
1. [ ] Launch the app and import at least one video
2. [ ] Draw a rectangle selection and choose a processing mode
3. [ ] Adjust blur/zoom, encoder, and output quality controls
4. [ ] Click `Save Preset`, enter a preset name, and confirm it saves without errors
5. [ ] Optionally export a copy of the preset JSON to another location
6. [ ] Change the mode, sliders, encoder, quality, and selection
7. [ ] Click `Load Preset` and choose the saved preset JSON
8. [ ] Confirm the preview selection, mode, sliders, encoder, quality, and logo/image path are restored
9. [ ] Load a preset whose stored logo/image path no longer exists and confirm a friendly warning appears

#### Settings Persistence
1. [ ] Set a custom output folder, encoder, mode, blur strength, zoom percentage, and quality
2. [ ] Close the app
3. [ ] Relaunch the app
4. [ ] Confirm the previous output folder, encoder, mode, blur strength, zoom percentage, and quality are restored

#### Export Summary And Logs
1. [ ] Run a successful export and confirm the final summary shows total, successful, failed, fallback count when applicable, output folder, and log file path
2. [ ] Confirm the summary offers an `Open Output Folder` action when the folder exists
3. [ ] Open the generated log file and confirm it includes export start/end, selected mode, encoder request, input paths, output paths, and any fallback events
4. [ ] Trigger a failed export and confirm the log file contains a compact FFmpeg error snippet rather than a huge raw dump

### Phase 6 Manual Export Tests

#### Blur Export Happy Path
1. [ ] Launch the app and import at least 3 videos
2. [ ] Draw a rectangle selection over a visible logo/watermark area
3. [ ] Leave processing mode on `Blur selected area`
4. [ ] Select an output folder
5. [ ] Leave encoder on `Auto - Prefer NVIDIA NVENC`
6. [ ] Click `Export All`
7. [ ] Verify the progress bar reaches the total number of files
8. [ ] Verify the final summary reports the correct success count
9. [ ] Open the output folder and confirm files end with `_blurred.mp4`
10. [ ] Play the outputs and confirm only the selected rectangle is blurred

#### Logo/Image Overlay Happy Path
1. [ ] Launch the app and import at least 3 videos
2. [ ] Draw a rectangle selection over the target area
3. [ ] Switch processing mode to `Cover with logo/image`
4. [ ] Click `Select Logo/Image` and choose a `.png`, `.jpg`, `.jpeg`, or `.webp` file
5. [ ] Select an output folder
6. [ ] Leave encoder on `Auto - Prefer NVIDIA NVENC`
7. [ ] Click `Export All`
8. [ ] Verify the progress bar reaches the total number of files
9. [ ] Verify the final summary lists successful files and any failures clearly
10. [ ] Open the output folder and confirm files end with `_branded.mp4`
11. [ ] Play the outputs and confirm the overlay is positioned inside the selected area
12. [ ] Repeat with a transparent PNG and confirm alpha transparency is preserved

#### Zoom/Crop Happy Path
1. [ ] Launch the app and import at least 3 videos
2. [ ] Switch processing mode to `Zoom/crop`
3. [ ] Do not draw a selection
4. [ ] Set the zoom slider to `108%` or higher
5. [ ] Select an output folder
6. [ ] Click `Export All`
7. [ ] Verify the progress bar reaches the total number of files
8. [ ] Verify the final summary lists successful files and any failures clearly
9. [ ] Open the output folder and confirm files end with `_zoomed.mp4`
10. [ ] Play the outputs and confirm the video is slightly zoomed and center-cropped back to the original dimensions

#### Blur Export Validation
1. [ ] Try exporting with no videos imported and confirm a readable validation error
2. [ ] Try exporting without selecting an output folder and confirm a readable validation error
3. [ ] Try exporting without a selection rectangle and confirm a readable validation error
4. [ ] Switch to `Cover with logo/image` without selecting a logo/image and confirm a readable validation error
5. [ ] Switch to `Cover with logo/image` with an unsupported image type and confirm a readable validation error
6. [ ] Switch to `Zoom/crop` without a selection and confirm export is allowed
7. [ ] Confirm `Fast`, `Balanced`, and `High Quality` all export successfully for at least one processing mode

#### Encoder Behavior
1. [ ] With FFmpeg unavailable on PATH, confirm the app shows a clear FFmpeg error and does not crash
2. [ ] With NVENC available, export in `Auto` mode and confirm export succeeds
3. [ ] With NVENC unavailable, export in `Auto` mode and confirm the app uses `libx264`
4. [ ] Select `NVIDIA - h264_nvenc` when NVENC is unavailable and confirm a clear error appears
5. [ ] Force a failure in Auto NVENC mode and confirm the app retries that file with CPU when `libx264` is available

#### Filename Collision Handling
1. [ ] Export one file twice to the same folder
2. [ ] Confirm blur outputs are named like `video_blurred.mp4` and `video_blurred_1.mp4`
3. [ ] Confirm logo/image outputs are named like `video_branded.mp4` and `video_branded_1.mp4`
4. [ ] Confirm zoom/crop outputs are named like `video_zoomed.mp4` and `video_zoomed_1.mp4`

#### Partial Failure Handling
1. [ ] Export a batch where one file is intentionally invalid or unreadable
2. [ ] Confirm the remaining files still export
3. [ ] Confirm the final summary includes success and failure counts without dumping huge FFmpeg logs
4. [ ] Confirm the log file is saved and includes the failure snippet for the bad file

### User Experience Tests

#### Happy Path
1. [ ] Launch app
2. [ ] Import 5 test videos
3. [ ] Select first video (preview loads)
4. [ ] Draw rectangle over logo area
5. [ ] Select "Blur" mode
6. [ ] Adjust blur intensity
7. [ ] Select output folder
8. [ ] Click Export
9. [ ] Wait for completion
10. [ ] Verify output videos exist
11. [ ] Play output videos to verify blur effect

#### Error Handling
1. [ ] Try to export without importing videos (should show error)
2. [ ] Try to export without selection (should show error for blur/logo)
3. [ ] Try to export without output folder (should show error)
4. [ ] Import corrupt video file (should handle gracefully)
5. [ ] Cancel export mid-way (should stop cleanly)
6. [ ] Disconnect network during export (should not affect local processing)

## Performance Tests

### Export Speed Tests
**File:** `tests/test_performance.py`

Test cases:
- [ ] Export 10 videos with CPU encoder (baseline)
- [ ] Export 10 videos with NVENC (if available)
- [ ] Compare CPU vs GPU speed
- [ ] Measure memory usage during export
- [ ] Test with 50 videos (stress test)
- [ ] Test with 4K resolution videos

### UI Responsiveness Tests
- [ ] UI remains responsive during single export
- [ ] UI remains responsive during batch export
- [ ] Preview canvas updates smoothly
- [ ] No lag when drawing selection rectangle
- [ ] Window remains draggable during export

## Compatibility Tests

### Video Format Tests
Test with various video formats:
- [ ] MP4 (H.264)
- [ ] MP4 (H.265)
- [ ] MOV (ProRes)
- [ ] WebM (VP9)
- [ ] Different frame rates (24, 30, 60 fps)
- [ ] Different bitrates
- [ ] Vertical (9:16)
- [ ] Square (1:1) - should handle or reject
- [ ] Horizontal (16:9) - should handle or reject

### Resolution Tests
- [ ] 720x1280 (HD vertical)
- [ ] 1080x1920 (FHD vertical)
- [ ] 1440x2560 (2K vertical)
- [ ] 2160x3840 (4K vertical)
- [ ] Non-standard resolutions

### Operating System Tests
- [ ] Windows 10
- [ ] Windows 11
- [ ] Different screen DPI settings

## Regression Tests

After each feature addition, run:
- [ ] All existing unit tests
- [ ] All existing integration tests
- [ ] Manual smoke test (import → select → export)
- [ ] Verify previous features still work

## Test Automation

### Continuous Integration
Set up CI to run:
- [ ] Unit tests on every commit
- [ ] Integration tests on every PR
- [ ] Linting and type checking
- [ ] Build verification

### Test Scripts
Create helper scripts:
- `run_tests.py` - Run all tests
- `run_unit_tests.py` - Run only unit tests
- `run_integration_tests.py` - Run only integration tests
- `generate_test_videos.py` - Create test video assets

## Bug Reporting Template

When bugs are found, document:
1. **Description:** What happened
2. **Steps to reproduce:** Exact steps to trigger the bug
3. **Expected behavior:** What should have happened
4. **Actual behavior:** What actually happened
5. **Environment:** OS, Python version, FFmpeg version
6. **Test assets:** Which video/file triggered the issue
7. **Logs:** Error messages or stack traces
8. **Frequency:** Always, sometimes, or one-time

## Test Coverage Goals

- Unit tests: 80%+ code coverage
- Integration tests: Cover all main workflows
- Manual tests: Cover all UI components
- Performance tests: Baseline metrics established

## Test Schedule

### MVP Phase
- Week 1: Set up test framework and test assets
- Week 2: Write unit tests for core components
- Week 3: Write integration tests for workflows
- Week 4: Manual UI testing and bug fixes
- Week 5: Performance and compatibility testing
- Week 6: Regression testing and polish

### Future Phases
- Add tests for new features as they're developed
- Maintain test coverage above 80%
- Run full test suite before each release
- Update test plan as features evolve
