# Task Plan: Fix Black Screenshots

## Goal
Fix the issue where screenshots taken by the agent are completely black.

## Phases
- [x] Phase 1: Investigate current screenshot mechanism
- [x] Phase 2: Reproduce the issue with a failing test (TDD)
- [x] Phase 3: Implement fix to capture actual screen content
- [x] Phase 4: Verify test passes
- [x] Phase 5: Refactor and clean up

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|

## Task Plan: Fix App and Web Usage Time Calculation

## Goal
Fix the logic for calculating app and web usage time to ensure it accurately reflects real usage.

## Phases
- [x] Phase 1: Investigate current calculation logic for screen time (both agent side and backend side).
- [x] Phase 2: Identify discrepancies (polling vs exact time, aggregation bugs, overlapping times, timezone issues, etc.).
- [x] Phase 3: Write failing tests (TDD) that reproduce the inaccurate calculation.
- [x] Phase 4: Fix `backend_api/routers/logs.py` to use 15s instead of 5s for app time.
- [x] Phase 5: Fix `backend_api/routers/logs.py` to calculate web time from `ProcessLog` instead of `BrowserHistory`.
- [x] Phase 6: Verify tests pass (GREEN).
