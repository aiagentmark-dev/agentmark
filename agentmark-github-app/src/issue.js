/**
 * agentmark — issue.js
 * Handle issues.opened webhook event
 * Issues a challenge token and posts it as a comment
 */

import { issueChallenge, formatChallengeComment } from "./challenge";
import { createGitHubClient } from "./github";

export async function handleIssueOpened(payload, env) {
  const { issue, repository, installation } = payload;

  const owner = repository.owner.login;
  const repo = repository.name;
  const issueNumber = issue.number;
  const issueRef = `${owner}/${repo}#${issueNumber}`;

  console.log(`Handling issue opened: ${issueRef}`);

  // Skip if issue has a "no-agentmark" label
  const labels = (issue.labels || []).map((l) => l.name);
  if (labels.includes("no-agentmark") || labels.includes("human")) {
    console.log(`Skipping ${issueRef} — excluded label`);
    return;
  }

  // Issue the challenge token
  const challenge = await issueChallenge(env.AGENTMARK_KV, {
    issueRef,
    repo: `${owner}/${repo}`,
    issueNumber,
    expectedPipeline: null, // any registered pipeline can pick this up
  });

  // Post comment to issue
  const gh = await createGitHubClient(env, installation.id);
  const comment = formatChallengeComment(
    challenge.token,
    challenge.expires_at,
    issueRef
  );

  await gh.postComment(owner, repo, issueNumber, comment);
  console.log(`Posted challenge token to ${issueRef}`);
}
