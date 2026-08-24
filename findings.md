# Findings

## Current Implementation
- pending investigation

## Bug Analysis
- The _ctypes_gdi_capture method uses BitBlt to capture the screen, but it calls GetDIBits on the bitmap while it is still selected into the memory device context (memdc).
- According to Windows GDI documentation, a bitmap must NOT be selected into a DC when calling GetDIBits, otherwise it will fail or return a black image.
- Confirmed via a scratch test that the mean pixel values are ~0, indicating a completely black image (with only the red timestamp being visible).

- The BitBlt call in _ctypes_gdi_capture fails (returns 0) in certain environments (e.g. Session 0 or secure desktop), leaving the bitmap uninitialized (black).
- Because the return value of BitBlt is ignored, _ctypes_gdi_capture returns this black image instead of returning None to trigger the fallbacks (mss, ImageGrab, or synthetic canvas).

## Screen Time Calculation Bug
- User reports the data output for app and web usage time is inaccurate compared to reality.
- Image shows: Total time 8m. Chrome: 2m (34.7%). Google: 1m (58.3%).
- Need to check how time is logged by the agent (polling interval?) and how it is aggregated by the backend.

## Root Cause Analysis
- **App Time:** The agent sends a process log every 15s (\PROCESS_SCAN_INTERVAL = 15\). However, the backend (\logs.py:446\) blindly adds 5 seconds for each log. This causes the total app time to be only 1/3 of the real time.
- **Web Time:** The backend calculates web time by multiplying the number of \BrowserHistory\ records by 15s. However, the agent's \BrowserTracker\ only sends a history record when the window title *changes*. If a user stays on YouTube for 1 hour, it only generates 1 record, which the backend counts as 15 seconds! This is why web time is severely undercounted.

## Proposed Solution
- Change the app time multiplier from 5 to 15 in \ackend_api/routers/logs.py\.
- Instead of using \BrowserHistory\ to calculate web time, use \ProcessLog\ (which correctly samples the active window every 15s). If the \process_name\ is a browser, extract the domain from the \window_title\ using a similar logic to \_infer_url_from_title\, and add 15s to that domain.
- This will make both app and web times perfectly accurate based on the active window sampling.
