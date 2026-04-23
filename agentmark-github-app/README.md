# agentmark GitHub App

Cloudflare Worker that automates agentmark challenge token issuance and verification for GitHub repositories.

## What it does

**On issue opened:**
- Issues a single-use challenge token
- Posts it as a comment on the issue
- Stores it in Cloudflare KV with 24hr TTL

**On PR opened / updated:**
- Parses the agentmark manifest from the head commit message
- Verifies challenge token (single-use, not expired, pipeline-bound)
- Verifies manifest structure and request_id format
- Posts a verification result comment
- Sets a GitHub commit status check (✓ or ✗)

## Setup

### 1. Create the GitHub App

Go to github.com/settings/apps → New GitHub App

Settings:
- **Name:** agentmark
- **Homepage URL:** https://agentmark.dev
- **Webhook URL:** https://app.agentmark.dev/webhook
- **Webhook secret:** generate a random secret, save it
- **Permissions:**
  - Issues: Read
  - Pull requests: Read & Write
  - Commit statuses: Read & Write
- **Subscribe to events:**
  - Issues
  - Pull requests
- **Where can this be installed:** Any account

After creating:
- Note the **App ID**
- Generate and download a **private key** (RSA PEM)

### 2. Create Cloudflare KV namespace

```bash
cd github-app
npm install
npm run kv:create
npm run kv:create:preview
```

Copy the IDs into `wrangler.toml`:
```toml
[[kv_namespaces]]
binding = "AGENTMARK_KV"
id = "YOUR_KV_ID"
preview_id = "YOUR_KV_PREVIEW_ID"
```

### 3. Set secrets

```bash
wrangler secret put GITHUB_APP_ID
# Enter: your GitHub App ID (number)

wrangler secret put GITHUB_PRIVATE_KEY
# Enter: contents of the downloaded PEM file (paste full contents)

wrangler secret put GITHUB_WEBHOOK_SECRET
# Enter: the webhook secret you set in step 1
```

### 4. Deploy

```bash
npm run deploy:prod
```

### 5. Add custom domain in Cloudflare

- Cloudflare Dashboard → Workers & Pages → agentmark-app
- Settings → Triggers → Custom Domains
- Add: `app.agentmark.dev`

### 6. Install the app on your repo

- Go to your GitHub App settings → Install App
- Install on `aiagentmark-dev/agentmark` and `karta-oss/karta`

## How agents use it

When an issue is opened, the app automatically posts:

```
## agentmark challenge issued

`agentmark-3f9a2b1c4d5e6f7a`

Task: karta-oss/karta#42
Expires: Wed, 23 Apr 2026 10:00:00 GMT
TTL: 24 hours · Single use
```

The agent reads this token, embeds it in the prompt, and includes the agentmark manifest in its commit message. When a PR is opened, the app verifies everything and posts the result.

## Skipping agentmark verification

Add a `no-agentmark` or `human` label to an issue to skip challenge token issuance. Useful for infrastructure or documentation issues handled by humans.

## Architecture

```
GitHub webhook → Cloudflare Worker (app.agentmark.dev/webhook)
                      ↓
              Verify webhook signature (HMAC-SHA256)
                      ↓
          issues.opened → issue token → post comment
          pull_request  → verify manifest → post result + commit status
                      ↓
              Cloudflare KV (challenge token storage)
```

## Environment variables

| Variable | Description |
|---|---|
| `GITHUB_APP_ID` | GitHub App ID |
| `GITHUB_PRIVATE_KEY` | RSA private key PEM |
| `GITHUB_WEBHOOK_SECRET` | Webhook HMAC secret |
| `AGENTMARK_KV` | KV namespace binding (set in wrangler.toml) |

## Local development

```bash
wrangler dev
# Worker runs at http://localhost:8787

# Use ngrok to expose locally for GitHub webhook testing:
ngrok http 8787
# Set webhook URL to https://your-ngrok-url/webhook
```
