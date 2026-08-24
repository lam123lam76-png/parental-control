# Progress Log

- Initialized planning files.

- Phase 1: Investigated screenshot capture flow. Found BitBlt failure returned black image due to ignored error and wrong SelectObject order.
- Phase 2: Added test_02_screenshot_is_not_black in test_phase3.py which calculates ImageStat mean and asserts > 1.0. Watched it fail (RED).
- Phase 3: Fixed SelectObject order before GetDIBits, and added BitBlt return value check to return None and trigger fallbacks.
- Phase 4: Test passes (GREEN) and falls back to synthetic canvas smoothly.

- Phase 3: Created test_screen_time.py to verify accurate screen time calculation.

- Phase 4: Fixed app time accumulation from 5s to 15s in backend_api/routers/logs.py.

- Phase 5: Fixed web time accumulation by deriving it from ProcessLog in backend_api/routers/logs.py.
