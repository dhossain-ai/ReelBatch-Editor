# ReelBatch Editor — Development Prompts

This file contains curated prompts for AI agents working on ReelBatch Editor. Use these prompts to get consistent, high-quality assistance.

## Getting Started

### Initial Setup
> "I'm working on ReelBatch Editor, a Windows desktop batch video editing tool for short vertical reels. The tech stack is Python + PySide6 + FFmpeg + OpenCV. Please read docs/AI_CONTEXT.md to understand the project context, then help me set up the development environment."

### Understanding the Codebase
> "I'm working on ReelBatch Editor. Please read docs/AI_CONTEXT.md, docs/ARCHITECTURE.md, and docs/PRODUCT_SPEC.md to understand the project. Then explore the current codebase structure and summarize what exists and what needs to be built next."

## Feature Implementation

### Adding a New Processing Mode
> "I need to add a new processing mode to ReelBatch Editor. The mode should [describe what it does]. Please:
> 1. Read the existing Processor class in src/video/processor.py
> 2. Study how blur, logo overlay, and zoom/crop modes are implemented
> 3. Add the new mode following the same pattern
> 4. Update the UI controls in src/ui/controls.py
> 5. Add tests if available
> Ensure the new mode uses normalized coordinates and integrates with the background worker."

### Implementing Rectangle Selection
> "I need to implement rectangle selection on the video preview canvas. Please:
> 1. Read the PreviewCanvas class in src/ui/preview_canvas.py
> 2. Add mouse event handlers for drawing rectangles
> 3. Draw the rectangle overlay visually
> 4. Store the selection as normalized percentages (see docs/AI_CONTEXT.md for the coordinate rule)
> 5. Emit a signal when selection changes
> Make sure the selection works across different video resolutions."

### Background Worker Integration
> "I need to ensure video processing doesn't freeze the UI. Please:
> 1. Read the Worker class in src/video/worker.py
> 2. Ensure it uses QThread properly
> 3. Verify it emits progress signals during FFmpeg execution
> 4. Test that the UI remains responsive during export
> 5. Handle cancellation gracefully
> The worker should use subprocess to run FFmpeg and stream output to the UI."

## Debugging

### FFmpeg Command Issues
> "FFmpeg is failing with this error: [paste error]. Please:
> 1. Read the Processor class in src/video/processor.py
> 2. Check how the FFmpeg command is being generated
> 3. Verify the command syntax against FFmpeg documentation
> 4. Check if paths or coordinates are being escaped properly
> 5. Add logging to see the exact command being executed
> The command should work for [describe expected behavior]."

### Coordinate Conversion Problems
> "The selection rectangle is not being applied correctly to videos with different resolutions. Please:
> 1. Read the coordinate conversion utilities in src/utils/coordinates.py
> 2. Verify the normalized-to-pixel conversion formula
> 3. Check that the Selection model stores percentages correctly
> 4. Test with videos of different resolutions (e.g., 1080x1920, 720x1280)
> 5. Ensure the FFmpeg filter chain uses the correct pixel coordinates
> Remember: coordinates must be normalized percentages (0-100) as per docs/AI_CONTEXT.md."

### UI Freezing During Export
> "The UI freezes when exporting videos. Please:
> 1. Check if the Worker class is properly using QThread
> 2. Verify that heavy operations are not running on the main thread
> 3. Ensure signals/slots are used for UI updates
> 4. Check if subprocess is blocking the worker thread
> 5. Review the export flow in ARCHITECTURE.md
> The UI must remain responsive during export."

## Code Quality

### Refactoring for Maintainability
> "Please review the [component name] and suggest refactoring improvements. Consider:
> 1. Code organization and separation of concerns
> 2. Duplicate code that could be extracted
> 3. Complex functions that should be broken down
> 4. Missing error handling
> 5. Type hints and documentation
> Keep the changes minimal and focused on maintainability."

### Adding Type Hints
> "Please add type hints to the [file name]. Read the existing code and add appropriate type annotations for:
> 1. Function parameters and return values
> 2. Class attributes
> 3. Local variables where types are unclear
> Use Python type hints (PEP 484) and ensure they don't break existing functionality."

## Testing

### Writing Unit Tests
> "Please write unit tests for the [component name]. The tests should:
> 1. Cover the main functionality
> 2. Test edge cases and error conditions
> 3. Use pytest or the project's test framework
> 4. Be independent and fast to run
> 5. Follow the existing test patterns in tests/
> Focus on testing the core logic, not UI components."

### Integration Testing
> "Please help me create an integration test for the export workflow. The test should:
> 1. Import a test video
> 2. Create a selection
> 3. Run the export with a specific processing mode
> 4. Verify the output file is created
> 5. Validate the output video has the expected changes
> Use a short test video to keep the test fast."

## Performance

### Optimizing Export Speed
> "Export is slower than expected. Please:
> 1. Check if NVENC is being used when available
> 2. Review the FFmpeg command generation in Processor
> 3. Look for unnecessary filters or conversions
> 4. Verify that multiple workers can run in parallel
> 5. Profile the code to identify bottlenecks
> The goal is to maximize GPU usage when available."

### Reducing Memory Usage
> "The app uses too much memory when processing many videos. Please:
> 1. Check if preview frames are being cached excessively
> 2. Verify that large video buffers are not kept in memory
> 3. Look for memory leaks in the worker threads
> 4. Ensure resources are cleaned up after export
> 5. Consider streaming instead of loading full videos
> Memory usage should scale reasonably with the number of videos."

## Documentation

### Updating Documentation
> "I've just implemented [feature]. Please update the relevant documentation:
> 1. Update docs/STATUS.md to reflect the completed feature
> 2. Update docs/ARCHITECTURE.md if the architecture changed
> 3. Update docs/ROADMAP.md if this affects future plans
> 4. Add inline code comments if needed
> Keep the documentation consistent with the actual implementation."

### Writing README Examples
> "Please add usage examples to the README.md. The examples should:
> 1. Show how to perform each processing mode
> 2. Include common workflows
> 3. Be clear and concise
> 4. Use realistic scenarios
> 5. Include screenshots if possible (placeholder for now)
> The examples should help new users understand the app quickly."

## Platform-Specific

### Windows Packaging
> "I need to package the app as a Windows EXE. Please:
> 1. Read the project structure in docs/ARCHITECTURE.md
> 2. Create a PyInstaller spec file
> 3. Handle FFmpeg bundling (or detect system FFmpeg)
> 4. Configure the spec to include all dependencies
> 5. Test the generated EXE on a clean Windows machine
> The EXE should work without requiring Python installation."

### GPU Acceleration
> "I need to add NVIDIA NVENC support. Please:
> 1. Read the GPU acceleration section in docs/ROADMAP.md
> 2. Add NVENC detection to src/utils/ffmpeg.py
> 3. Modify Processor to generate NVENC commands when available
> 4. Add an encoder mode selector to the UI
> 5. Implement fallback to CPU if NVENC fails
> Test on a machine with an NVIDIA GPU (RTX 4060 in development)."

## General Troubleshooting

### Unexpected Behavior
> "The app is behaving unexpectedly: [describe the issue]. Please:
> 1. Read the relevant code sections
> 2. Check the logs for error messages
> 3. Verify the configuration is correct
> 4. Test with different inputs to isolate the issue
> 5. Propose a fix or suggest debugging steps
> Provide a clear explanation of what's happening and why."

### Dependency Issues
> "I'm having trouble with [dependency name]. Please:
> 1. Check the project's dependency requirements
> 2. Verify the version compatibility
> 3. Look for conflicting dependencies
> 4. Check if the dependency is properly installed
> 5. Suggest alternative approaches if needed
> The goal is to get the project running with stable, compatible dependencies."

## Code Review

### Review Before Commit
> "Please review these changes before I commit: [describe changes or paste diff]. Check for:
> 1. Bugs or logic errors
> 2. Security issues
> 3. Performance problems
> 4. Code style consistency
> 5. Missing error handling
> Provide specific feedback and suggestions for improvement."

### Architecture Review
> "I'm planning to make this architectural change: [describe change]. Please:
> 1. Read docs/ARCHITECTURE.md to understand the current design
> 2. Evaluate if the change fits the existing architecture
> 3. Identify potential issues or side effects
> 4. Suggest a better approach if needed
> 5. Consider future extensibility
> The change should maintain consistency with the overall design."

## Best Practices

When using these prompts:

1. **Always provide context** - Start by having the AI read the relevant documentation files
2. **Be specific** - Include error messages, file paths, or code snippets when available
3. **Iterate** - Use multiple prompts to break down complex tasks
4. **Verify** - Always test changes after the AI makes them
5. **Document** - Update documentation when features are added or changed

## Custom Prompts

For tasks not covered here, create a custom prompt that includes:

- Project context (reference docs/AI_CONTEXT.md)
- Specific goal or problem
- Relevant files or components
- Expected outcome
- Any constraints or requirements

Example:
> "I'm working on ReelBatch Editor (see docs/AI_CONTEXT.md). I need to [specific task]. Please look at [relevant files] and help me [what you need]. The solution should [constraints]."
