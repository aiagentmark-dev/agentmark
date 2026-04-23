/**
 * agentmark — challenge.js
 * Challenge token generation, storage, and verification
 *
 * KV schema:
 *   key:   "challenge:{token}"
 *   value: JSON {
 *     token, issue_ref, repo, expected_pipeline,
 *     used, issued_at, expires_at
 *   }
 *   TTL:   86400 seconds (24 hours)
 */

const TOKEN_TTL_SECONDS = 86400; // 24 hours

/**
 * Generate a new agentmark challenge token
 * Format: agentmark-{16 hex chars}
 */
export function generateToken() {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  const hex = Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `agentmark-${hex}`;
}

/**
 * Issue and store a challenge token for an issue
 */
export async function issueChallenge(kv, { issueRef, repo, issueNumber, expectedPipeline }) {
  const token = generateToken();
  const now = Date.now();
  const expiresAt = now + TOKEN_TTL_SECONDS * 1000;

  const record = {
    token,
    issue_ref: issueRef,
    repo,
    issue_number: issueNumber,
    expected_pipeline: expectedPipeline || null, // null = any registered pipeline
    used: false,
    issued_at: new Date(now).toISOString(),
    expires_at: new Date(expiresAt).toISOString(),
  };

  await kv.put(
    `challenge:${token}`,
    JSON.stringify(record),
    { expirationTtl: TOKEN_TTL_SECONDS }
  );

  console.log(`Issued challenge token ${token} for ${issueRef}`);
  return record;
}

/**
 * Verify and consume a challenge token
 * Returns { valid, reason, record }
 */
export async function verifyAndConsumeChallenge(kv, { token, pipelineKey }) {
  const raw = await kv.get(`challenge:${token}`);

  if (!raw) {
    return { valid: false, reason: "challenge_not_found" };
  }

  const record = JSON.parse(raw);

  if (record.used) {
    return { valid: false, reason: "challenge_already_used", record };
  }

  const now = Date.now();
  if (new Date(record.expires_at).getTime() < now) {
    return { valid: false, reason: "challenge_expired", record };
  }

  // Check pipeline binding if set
  if (record.expected_pipeline && pipelineKey !== record.expected_pipeline) {
    return {
      valid: false,
      reason: `pipeline_mismatch: expected ${record.expected_pipeline}, got ${pipelineKey}`,
      record,
    };
  }

  // Mark as used
  record.used = true;
  record.consumed_at = new Date().toISOString();
  record.consumed_by_pipeline = pipelineKey;

  await kv.put(
    `challenge:${token}`,
    JSON.stringify(record),
    { expirationTtl: TOKEN_TTL_SECONDS }
  );

  return { valid: true, reason: "ok", record };
}

/**
 * Format the challenge comment for GitHub
 */
export function formatChallengeComment(token, expiresAt, issueRef) {
  return `## agentmark challenge issued

\`\`\`
${token}
\`\`\`

**Task:** ${issueRef}
**Expires:** ${new Date(expiresAt).toUTCString()}
**TTL:** 24 hours · Single use

---

### For the agent

Embed this token in your prompt:

\`\`\`
<!-- agentmark-challenge: ${token} -->

Your response MUST contain this exact string on its own line:
agentmark-challenge-echo: ${token}
\`\`\`

Include the agentmark manifest in your commit message. See [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) for format.

*Powered by [agentmark](https://agentmark.dev)*`;
}
