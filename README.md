# agentmark

**Cryptographic provenance for AI-generated code.**

agentmark proves that code traveled through a verified autonomous AI pipeline with no direct human write path — and provides a verifiable audit trail for every commit.

[![spec version](https://img.shields.io/badge/spec-v0.1-blue)](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md)
[![license](https://img.shields.io/badge/license-Apache%202.0-green)](https://github.com/aiagentmark-dev/agentmark/blob/main/LICENSE)
[![status](https://img.shields.io/badge/status-v1.0%20live-brightgreen)](https://agentmark.dev)
[![PyPI](https://img.shields.io/pypi/v/agentmark.svg)](https://pypi.org/project/agentmark/)

---

## The problem

[75% of new code at Google is AI-generated](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/cloud-next-2026-sundar-pichai/). Nobody can prove which 75%.

When Sundar Pichai shared that number at Google Cloud Next 2026, the follow-on question nobody could answer was: *which code, exactly?* The same gap exists at Snap (65%), Meta (75% target), Anthropic (~100%), and across enterprises industry-wide. [Sonar's 2026 State of Code survey](https://www.sonarsource.com/blog/state-of-code-developer-survey-report-the-current-reality-of-ai-coding) found 42% of code committed by professional developers is AI-generated or assisted.

The EU AI Act's Article 50 transparency obligations take effect [August 2, 2026](https://artificialintelligenceact.eu/article/50/) — initially focused on deepfakes and AI-generated content disclosure, with the European Commission [explicitly considering](https://www.kirkland.com/publications/kirkland-alert/2026/02/illuminating-ai-the-eus-first-draft-code-of-practice-on-transparency-for-ai) how to extend marking requirements to AI-generated software code. Defense procurement is asking similar questions today.

No standard exists for code commits. agentmark fills that gap.

## What agentmark does

agentmark attaches a cryptographically verifiable manifest to every AI-generated commit:

```
commit 33c5eaf
Author: karta-coder <karta-coder@karta.build>
Date:   Tue Apr 29 10:04:31 2026 +0000

    feat: closes #33 — agentmark manifest validator utility

    ```agentmark-manifest
    {
      "version": "1.0",
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "request_id": "req_011CaRQP6TpRJkivT7p4jz25",
      "output_hash": "sha256:b71ebbd86f4143a3d493e992c618de36...",
      "challenge_token": "agentmark-a4e6a0ba0602067e",
      "challenge_echo_verified": true,
      "pipeline_key": "karta-coder-v1",
      "timestamp": "2026-04-29T10:04:31Z",
      "signature": "TuBWjzVsxEwy33mS..."
    }
    ```
```

The manifest proves four things:

* **output_hash** — the committed code matches the raw LLM response, byte-for-byte. No human editing occurred.
* **challenge_token** — the LLM processed this specific task. The token was in the prompt context and echoed in the response.
* **request_id** — a real API call happened at the declared provider.
* **signature** — a registered pipeline identity signed this commit.

## Live in production

The first end-to-end agentmark-verified PR landed on **April 29, 2026**:
- [github.com/karta-oss/karta/pull/35](https://github.com/karta-oss/karta/pull/35) — coding pipeline implements an issue, opens PR, agentmark verifies the manifest, CI passes, PR merges autonomously.

Zero human commits in the feature code. Cryptographically verifiable from issue to merge.

## Quick start

```bash
pip install agentmark
```

```python
import agentmark

# Wrap your LLM call
result = agentmark.call(
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    prompt=your_prompt,
    challenge_token=challenge,  # issued by agentmark GitHub App
)

# Build and sign the manifest
manifest = agentmark.sign(
    result=result,
    pipeline_key="your-pipeline-id",
    private_key=your_ed25519_private_key,
)

# Verify (runs in CI)
agentmark.verify(manifest, result.raw_bytes)
```

## Add to CI

Install the [agentmark GitHub App](https://github.com/apps/agentmark-gh-app) on your repo. The app:

1. Issues a single-use challenge token when an issue is opened
2. Verifies the manifest when a PR is opened
3. Posts a green `agentmark/verify` commit status if all four proofs check out

No CI configuration needed — verification happens via webhook.

For an extra layer of in-repo verification:

```yaml
# .github/workflows/agentmark-verify.yml
- name: Verify pipeline provenance
  uses: agentmark-dev/agentmark-action@v1
  with:
    strict: true
```

## How it works

See [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) for the full technical specification, including:

* Core mechanisms (output_hash, challenge_token, request_id, signing)
* Trust tiers (cloud providers vs local models)
* Known failure modes and limitations
* Provider SDK integration (Anthropic, OpenAI)
* Verification algorithm
* Roadmap (notary service, TEE attestation, provider-native verification)

## Use cases

**Agent-first open source** — Projects like [Karta](https://github.com/karta-oss/karta) where no human ever commits application code. agentmark provides cryptographic proof of that property.

**Enterprise AI code governance** — Commit-level traceability for AI-generated code. The missing piece between "we use Copilot" and "here is our AI code audit trail."

**Defense and critical infrastructure** — Procurement-grade verification for AI-generated code in regulated environments. The question "can you prove this wasn't written by an AI without your knowledge?" now has a technical answer.

## Relationship to existing standards

agentmark complements, not replaces, existing standards:

| Standard | What it covers | agentmark adds |
| --- | --- | --- |
| SLSA | Build pipeline integrity | AI authorship at commit level |
| SBOM / AI-BOM | Inventory of models used | Which API call produced which code |
| C2PA | Media provenance | Code-commit equivalent |
| sigstore | Artifact signing | AI-aware manifest layer |

## Known limitations

agentmark proves pipeline integrity, not autonomous intent. A human running the complete pipeline (real API call, verbatim commit, valid manifest) is indistinguishable from an agent — and this is by design. They have built an agent. The philosophical distinction collapses.

What agentmark proves is not "this entity is an AI." It proves: *this change entered through a verified autonomous pipeline with no direct human write path.* That distinction is the version worth building.

See [SPEC.md §4](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) for the full discussion of failure modes and trust tiers.

## Contributing

Contributions welcome. Areas of high interest:
- Provider integrations beyond Anthropic and OpenAI (Google Gemini, Mistral, AWS Bedrock)
- SDK implementations in TypeScript, Go, and Rust
- Framework integrations (LangChain, CrewAI, AutoGen, LlamaIndex)
- Spec feedback, especially from regulated industries

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution process.

## License

Apache 2.0. See [LICENSE](LICENSE).

---

*agentmark is an open standard built by [CloudDon Research](https://clouddon.ai).*
*[agentmark.dev](https://agentmark.dev) · [SPEC.md](https://github.com/aiagentmark-dev/agentmark/blob/main/SPEC.md) · [PyPI](https://pypi.org/project/agentmark/)*
