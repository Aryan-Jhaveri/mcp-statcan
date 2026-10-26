---
description: Set up Postman MCP Server. Authenticate via OAuth or API key, verify connection, select workspace.
---

# First-Run Configuration

Walk the user through Postman MCP setup. Validate everything works before moving on to other Postman tasks.

## Workflow

### Step 1: Check MCP Connection

Verify the Postman MCP Server is available by calling `getAuthenticatedUser`.

**If it works:** Skip to Step 4 (workspace verification).

**If it fails:** Check whether `mcp__postman__authenticate` is available.
- Available → offer the user a choice: **OAuth (recommended)** or **API key**. Default to OAuth unless they ask for API key.
- Not available → the MCP server isn't loaded. Show the "MCP tools not available" error below and stop.

### Step 2: OAuth Authentication (Recommended)

Present:
```
Let's connect your Postman account via OAuth — no key copying required.

I'll generate an authorization URL. Open it in your browser, sign in, and paste the callback URL back here.
```

1. Call `mcp__postman__authenticate` — it returns an authorization URL.
2. Show the URL:
   ```
   Open this URL in your browser:
   <authorization URL>

   After you authorize, your browser will redirect to a localhost URL.
   The page may not load — that's expected. Copy the full URL from the address bar and paste it here.
   ```
3. Wait for the user to paste the callback URL.
4. Call `mcp__postman__complete_authentication` with the pasted URL as `callback_url`.
5. The MCP server may restart after saving the OAuth token, temporarily dropping the connection. This is expected.
   - Wait a few seconds, then retry `getAuthenticatedUser` up to 3 times with short pauses between attempts.
   - If tools become unavailable (server disconnected), tell the user:
     ```
     The MCP server is restarting after saving your credentials — this is normal.
     Give it a moment and I'll retry the connection...
     ```
   - If tools are still unavailable after retries:
     ```
     The server hasn't reconnected yet. Restart your agent, then ask me to check the Postman connection again.
     Your OAuth token is already saved — you won't need to re-authorize.
     ```
6. Once `getAuthenticatedUser` succeeds, proceed to Step 4.

**If OAuth fails:** "OAuth didn't complete. You can try again or use an API key instead — just say 'use API key'." → offer Step 3.

### Step 3: API Key Authentication (Alternative)

Present:
```
Let's set up Postman using an API key.

1. Go to: https://go.postman.co/settings/me/api-keys
2. Click "Generate API Key"
3. Name it "Claude Code"
4. Copy the key (starts with PMAK-)

Then set it as an environment variable:

  export POSTMAN_API_KEY=PMAK-your-key-here

Add it to your shell profile (~/.zshrc or ~/.bashrc) to persist across sessions.
When done, let me know and I'll verify the connection.
```

Wait for the user to confirm they've set the key. Then verify with `getAuthenticatedUser`.

**If 401:** "API key was rejected. Check for extra spaces or generate a new one at https://go.postman.co/settings/me/api-keys"

**If timeout:** "Can't reach the Postman MCP Server. Check your network and https://status.postman.com"

### Step 4: Workspace Verification

After successful connection (either auth method):

1. Call `getWorkspaces` to list workspaces.
2. Call `getCollections` with the first workspace ID to count collections.
3. Call `getAllSpecs` with the workspace ID to count specs.

Present:
```
Connected as: <user name>

Your workspaces:
  - My Workspace (personal) — 12 collections, 3 specs
  - Team APIs (team) — 8 collections, 5 specs

You're all set.
```

If workspace is empty:
```
Your workspace is empty. You can ask me to:
  - Push a local OpenAPI spec to Postman
  - Search for APIs across your org's resources or the public Postman network
```

### Step 5: Suggest a First Task

Based on what the user has:

**Has collections:**
```
Try asking me to:
  - Find APIs across your workspace
  - Run collection tests
```

**Has specs but no collections:**
```
Try asking me to:
  - Generate a collection from one of your specs
```

**Empty workspace:**
```
Try asking me to:
  - Import an OpenAPI spec from your project
```

## Error Handling

- **MCP tools not available:** "The Postman MCP Server isn't connected in this agent. If the Postman plugin is installed, sign in to its MCP server from the agent's MCP settings; otherwise install the plugin for this agent and restart it. https://github.com/postmanlabs/postman-plugin#install has the install steps for each agent."
- **OAuth callback invalid:** "That URL doesn't look right — make sure you copied the full address bar URL including `?code=` and `&state=`."
- **OAuth flow expired:** "The authorization URL has expired. I'll generate a fresh one." Then repeat Step 2.
- **MCP server disconnected after OAuth:** The server restarts after saving credentials. Retry `getAuthenticatedUser` up to 3 times. If still unavailable, tell the user to restart their agent — the token is saved, no re-auth needed.
- **API key not set:** Walk through Step 3 above.
- **401 Unauthorized:** "Authentication failed. I can re-authenticate you via OAuth, or you can generate a new API key at https://go.postman.co/settings/me/api-keys." Then offer Step 2 or Step 3.
- **Network timeout:** "Can't reach the Postman MCP Server. Check your network and https://status.postman.com for outages."
- **Plan limitations:** "Some features (team workspaces, monitors) require a paid Postman plan. Core workflows work on all plans."
