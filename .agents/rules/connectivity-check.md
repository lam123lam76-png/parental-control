
# Connectivity Check Requirements

## Context
When modifying any system components (agent, backend, or web dashboard), it is crucial to verify that the end-to-end connectivity remains intact. Changes to environment variables, network endpoints, or database structures can silently break the WebSocket or REST communication between the Agent, Backend Server, and Web Dashboard.

## Checklist (Mandatory)
Before finishing a task that modifies system files, the agent MUST explicitly follow this checklist:

1. **Verify Backend Server Status**:
   - Check if the backend API is reachable locally or in production.
   - Run a simple health check or curl to the /docs or /api/alerts endpoint.

2. **Verify Agent Connection**:
   - Check the Agent's .env to ensure BACKEND_URL, WS_URL, and SERVER_URL point to the correct environment (production or local).
   - Check the gent_debug.log to confirm the agent successfully connects via WebSocket and does not encounter 401/403/404 or timeout errors.

3. **Verify Web Dashboard Synchronization**:
   - Ensure the Web Dashboard successfully fetches data from the API without 404/CORS/Connection errors.
   - Verify the Agent's 'Online' status accurately reflects on the dashboard.

## Action
If any of these checks fail, you MUST resolve the connectivity issue before claiming the task is complete.
