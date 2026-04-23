/**
 * agentmark — github.js
 * Minimal GitHub API client using App JWT authentication
 */

/**
 * Generate a GitHub App JWT token
 * GitHub Apps authenticate with a JWT signed by their private key
 */
async function generateAppJWT(appId, privateKeyPem) {
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iat: now - 60,  // issued 60s ago (clock skew tolerance)
    exp: now + 600, // expires in 10 minutes
    iss: appId,
  };

  // Encode JWT header and payload
  const header = btoa(JSON.stringify({ alg: "RS256", typ: "JWT" }))
    .replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
  const body = btoa(JSON.stringify(payload))
    .replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");

  const unsigned = `${header}.${body}`;

  // Import RSA private key
  const pemContents = privateKeyPem
    .replace("-----BEGIN RSA PRIVATE KEY-----", "")
    .replace("-----END RSA PRIVATE KEY-----", "")
    .replace(/\s/g, "");

  const keyData = Uint8Array.from(atob(pemContents), (c) => c.charCodeAt(0));

  const key = await crypto.subtle.importKey(
    "pkcs8",
    keyData,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"]
  );

  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    key,
    new TextEncoder().encode(unsigned)
  );

  const sig = btoa(String.fromCharCode(...new Uint8Array(signature)))
    .replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");

  return `${unsigned}.${sig}`;
}

/**
 * Get an installation access token for a repo
 */
async function getInstallationToken(appId, privateKey, installationId) {
  const jwt = await generateAppJWT(appId, privateKey);

  const response = await fetch(
    `https://api.github.com/app/installations/${installationId}/access_tokens`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${jwt}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentmark-app/1.0",
      },
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to get installation token: ${err}`);
  }

  const data = await response.json();
  return data.token;
}

/**
 * Post a comment to a GitHub issue or PR
 */
export async function postComment(token, owner, repo, issueNumber, body) {
  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/issues/${issueNumber}/comments`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentmark-app/1.0",
      },
      body: JSON.stringify({ body }),
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to post comment: ${err}`);
  }

  return response.json();
}

/**
 * Create a commit status check on a PR
 */
export async function createCommitStatus(token, owner, repo, sha, { state, description, context }) {
  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/statuses/${sha}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentmark-app/1.0",
      },
      body: JSON.stringify({
        state,           // "success" | "failure" | "pending" | "error"
        description,     // short status message
        context: context || "agentmark/verify",
        target_url: "https://agentmark.dev",
      }),
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to create commit status: ${err}`);
  }

  return response.json();
}

/**
 * Get commit details including message
 */
export async function getCommit(token, owner, repo, sha) {
  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/commits/${sha}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agentmark-app/1.0",
      },
    }
  );

  if (!response.ok) {
    const err = await response.text();
    throw new Error(`Failed to get commit: ${err}`);
  }

  return response.json();
}

/**
 * Create a GitHub API client bound to an installation
 */
export async function createGitHubClient(env, installationId) {
  const token = await getInstallationToken(
    env.GITHUB_APP_ID,
    env.GITHUB_PRIVATE_KEY,
    installationId
  );

  return {
    postComment: (owner, repo, issueNumber, body) =>
      postComment(token, owner, repo, issueNumber, body),
    createCommitStatus: (owner, repo, sha, status) =>
      createCommitStatus(token, owner, repo, sha, status),
    getCommit: (owner, repo, sha) =>
      getCommit(token, owner, repo, sha),
  };
}
