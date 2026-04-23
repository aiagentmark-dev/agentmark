/**
 * agentmark GitHub App — Cloudflare Worker
 *
 * Handles two GitHub webhook events:
 *   issues.opened     → issue a challenge token, post as comment
 *   pull_request.opened / synchronize → verify agentmark manifest
 *
 * Environment variables (set in Cloudflare dashboard):
 *   GITHUB_APP_ID         — GitHub App ID
 *   GITHUB_PRIVATE_KEY    — GitHub App private key (PEM, RSA)
 *   GITHUB_WEBHOOK_SECRET — GitHub webhook secret for payload verification
 *   KV_NAMESPACE          — bound in wrangler.toml as AGENTMARK_KV
 */

import { verifyWebhookSignature } from "./webhook";
import { handleIssueOpened } from "./issue";
import { handlePullRequest } from "./pullrequest";

export default {
  async fetch(request, env, ctx) {
    // Only accept POST requests
    if (request.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      return new Response(JSON.stringify({ status: "ok", version: "1.0.0" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // Only handle webhook path
    if (url.pathname !== "/webhook") {
      return new Response("Not found", { status: 404 });
    }

    // Read body
    const body = await request.text();

    // Verify GitHub webhook signature
    const signature = request.headers.get("x-hub-signature-256");
    if (!signature) {
      return new Response("Missing signature", { status: 401 });
    }

    const valid = await verifyWebhookSignature(
      body,
      signature,
      env.GITHUB_WEBHOOK_SECRET
    );
    if (!valid) {
      return new Response("Invalid signature", { status: 401 });
    }

    // Parse event
    const event = request.headers.get("x-github-event");
    const payload = JSON.parse(body);

    console.log(`Received event: ${event}, action: ${payload.action}`);

    try {
      // Route to handler
      if (event === "issues" && payload.action === "opened") {
        await handleIssueOpened(payload, env);
        return new Response("OK", { status: 200 });
      }

      if (
        event === "pull_request" &&
        (payload.action === "opened" || payload.action === "synchronize")
      ) {
        await handlePullRequest(payload, env);
        return new Response("OK", { status: 200 });
      }

      // Unhandled event — acknowledge and ignore
      return new Response("OK", { status: 200 });
    } catch (err) {
      console.error("Handler error:", err);
      return new Response("Internal error", { status: 500 });
    }
  },
};
