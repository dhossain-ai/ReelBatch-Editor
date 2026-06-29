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
- [ ] Generate logo overlay command with correct positioning
- [ ] Generate zoom/crop command with correct scale
- [x] Use normalized coordinates in commands
- [x] Generate NVENC commands when GPU available
- [x] Generate CPU commands as fallback
- [ ] Escape special characters in paths
- [ ] Handle paths with spaces

### Preset Tests
**File:** `tests/test_preset.py`

Test cases:
- [ ] Create preset with selection and mode
- [ ] Serialize preset to JSON
- [ ] Deserialize preset from JSON
- [ ] Handle missing or invalid preset files
- [ ] Validate preset data structure
- [ ] Copy/clone preset

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
- [ ] Can draw rectangle with mouse
- [ ] Rectangle appears while drawing
- [ ] Rectangle remains after drawing
- [ ] Can clear selection
- [ ] Preview scales with window size

#### Controls
- [ ] Processing mode selector works (blur/logo/zoom)
- [ ] Settings panel changes based on mode
- [ ] Blur intensity slider works
- [ ] Logo file picker works
- [ ] Zoom percentage slider works
- [x] Output folder picker works
- [ ] Export button is enabled when ready

#### Export
- [x] Progress bar appears during export
- [x] Progress updates for each video
- [x] Status text shows current operation
- [ ] Cancel button stops export
- [x] Success message appears on completion
- [x] Error message appears on failure
- [ ] Output folder opens on completion (optional)

### Phase 5 Manual Export Tests

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

#### Blur Export Validation
1. [ ] Try exporting with no videos imported and confirm a readable validation error
2. [ ] Try exporting without selecting an output folder and confirm a readable validation error
3. [ ] Try exporting without a selection rectangle and confirm a readable validation error
4. [ ] Switch the processing mode away from blur and confirm export is blocked for this phase

#### Encoder Behavior
1. [ ] With FFmpeg unavailable on PATH, confirm the app shows a clear FFmpeg error and does not crash
2. [ ] With NVENC available, export in `Auto` mode and confirm export succeeds
3. [ ] With NVENC unavailable, export in `Auto` mode and confirm the app uses `libx264`
4. [ ] Select `NVIDIA - h264_nvenc` when NVENC is unavailable and confirm a clear error appears
5. [ ] Force a failure in Auto NVENC mode and confirm the app retries that file with CPU when `libx264` is available

#### Filename Collision Handling
1. [ ] Export one file twice to the same folder
2. [ ] Confirm outputs are named like `video_blurred.mp4` and `video_blurred_1.mp4`

#### Partial Failure Handling
1. [ ] Export a batch where one file is intentionally invalid or unreadable
2. [ ] Confirm the remaining files still export
3. [ ] Confirm the final summary includes success and failure counts without dumping huge FFmpeg logs

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
