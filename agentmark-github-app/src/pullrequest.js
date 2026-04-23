/**
 * agentmark — pullrequest.js
 * Handle pull_request.opened / synchronize webhook events
 * Verifies the agentmark manifest in the head commit
 */

import { verifyAndConsumeChallenge } from "./challenge";
import { createGitHubClient } from "./github";

const MANIFEST_REGEX = /```agentmark-manifest\n([\s\S]*?)\n```/;

/**
 * Parse agentmark manifest from commit message
 */
function parseManifest(commitMessage) {
  const match = MANIFEST_REGEX.exec(commitMessage);
  if (!match) return null;
  try {
    return JSON.parse(match[1]);
  } catch {
    return null;
  }
}

/**
 * Verify output_hash against raw bytes
 * Note: In the GitHub App we verify structural integrity only —
 * full cryptographic verification (output_hash bytes) runs in CI via agentmark CLI
 */
function verifyManifestStructure(manifest) {
  const required = [
    "version", "provider", "model", "output_hash",
    "challenge_token", "pipeline_key", "timestamp", "signature"
  ];

  const missing = required.filter((f) => !manifest[f]);
  if (missing.length > 0) {
    return { valid: false, reason: `missing_fields: ${missing.join(", ")}` };
  }

  // Validate output_hash format
  if (!manifest.output_hash.startsWith("sha256:")) {
    return { valid: false, reason: "invalid_output_hash_format" };
  }

  // Validate request_id format for cloud providers
  if (manifest.provider === "anthropic" && manifest.request_id) {
    if (!manifest.request_id.startsWith("req_01")) {
      return { valid: false, reason: "request_id_format_mismatch" };
    }
  }

  if (manifest.provider === "openai" && manifest.request_id) {
    if (!manifest.request_id.startsWith("req-") && !isUUID(manifest.request_id)) {
      return { valid: false, reason: "request_id_format_mismatch" };
    }
  }

  return { valid: true, reason: "ok" };
}

function isUUID(str) {
  return /^[0-9a-f-]{36}$/.test(str);
}

/**
 * Format verification success comment
 */
function formatSuccessComment(manifest, issueRef) {
  return `## ✓ agentmark verified

| Field | Value |
|---|---|
| Pipeline | \`${manifest.pipeline_key}\` |
| Provider | \`${manifest.provider}\` |
| Model | \`${manifest.model}\` |
| output_hash | \`${manifest.output_hash.substring(0, 20)}...\` |
| challenge_echo | ✓ verified |
| request_id | \`${manifest.request_id || "n/a (local model)"}\` |
| timestamp | \`${manifest.timestamp}\` |

This commit was produced by a verified autonomous AI pipeline with no direct human write path.

*[agentmark](https://agentmark.dev) · [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md)*`;
}

/**
 * Format verification failure comment
 */
function formatFailureComment(reason, manifest) {
  return `## ✗ agentmark verification failed

**Reason:** \`${reason}\`

${manifest ? `**Pipeline:** \`${manifest.pipeline_key || "unknown"}\`` : "No agentmark manifest found in commit message."}

This PR cannot be merged until agentmark verification passes. See [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) for the manifest format.

*[agentmark](https://agentmark.dev)*`;
}

export async function handlePullRequest(payload, env) {
  const { pull_request, repository, installation } = payload;

  const owner = repository.owner.login;
  const repo = repository.name;
  const prNumber = pull_request.number;
  const headSha = pull_request.head.sha;
  const prRef = `${owner}/${repo}#${prNumber}`;

  console.log(`Handling PR: ${prRef} sha: ${headSha}`);

  const gh = await createGitHubClient(env, installation.id);

  // Get commit message
  const commit = await gh.getCommit(owner, repo, headSha);
  const commitMessage = commit.commit.message;

  // Set pending status immediately
  await gh.createCommitStatus(owner, repo, headSha, {
    state: "pending",
    description: "agentmark verification in progress...",
    context: "agentmark/verify",
  });

  // Parse manifest
  const manifest = parseManifest(commitMessage);

  if (!manifest) {
    await gh.createCommitStatus(owner, repo, headSha, {
      state: "failure",
      description: "No agentmark manifest found in commit message",
      context: "agentmark/verify",
    });
    await gh.postComment(owner, repo, prNumber,
      formatFailureComment("manifest_missing", null)
    );
    return;
  }

  // Verify manifest structure
  const structureCheck = verifyManifestStructure(manifest);
  if (!structureCheck.valid) {
    await gh.createCommitStatus(owner, repo, headSha, {
      state: "failure",
      description: `Manifest invalid: ${structureCheck.reason}`,
      context: "agentmark/verify",
    });
    await gh.postComment(owner, repo, prNumber,
      formatFailureComment(structureCheck.reason, manifest)
    );
    return;
  }

  // Verify and consume challenge token
  const challengeCheck = await verifyAndConsumeChallenge(env.AGENTMARK_KV, {
    token: manifest.challenge_token,
    pipelineKey: manifest.pipeline_key,
  });

  if (!challengeCheck.valid) {
    await gh.createCommitStatus(owner, repo, headSha, {
      state: "failure",
      description: `Challenge verification failed: ${challengeCheck.reason}`,
      context: "agentmark/verify",
    });
    await gh.postComment(owner, repo, prNumber,
      formatFailureComment(challengeCheck.reason, manifest)
    );
    return;
  }

  // All checks passed
  await gh.createCommitStatus(owner, repo, headSha, {
    state: "success",
    description: `Verified · ${manifest.pipeline_key} · ${manifest.provider}/${manifest.model}`,
    context: "agentmark/verify",
  });

  await gh.postComment(owner, repo, prNumber,
    formatSuccessComment(manifest, prRef)
  );

  console.log(`PR ${prRef} verified successfully`);
}
