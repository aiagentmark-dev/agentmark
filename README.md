# agentmark

**Cryptographic provenance for AI-generated code.**

agentmark proves that code traveled through a verified autonomous AI pipeline with no direct human write path — and provides a verifiable audit trail for every commit.

[![spec version](https://img.shields.io/badge/spec-v0.1-blue)](SPEC.md)
[![license](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![status](https://img.shields.io/badge/status-pre--release-orange)](SPEC.md)

---

## The problem

30% of enterprise code is now AI-generated. Nobody can prove it.

Microsoft can't trace which commits in their own repos came from Copilot vs a human. Defense contractors ship AI-generated code to allied governments with no audit trail. Open source projects claiming to be "built entirely by AI agents" have no way to verify that claim.

The EU AI Act (Article 50, enforceable August 2026) requires machine-readable disclosure of AI-generated content. No standard exists for code commits.

## What agentmark does

agentmark attaches a cryptographically verifiable manifest to every AI-generated commit:

```
commit a1b2c3d
Author: karta-coder <karta-coder@karta.build>
Date:   Thu Apr 17 10:22:47 2026 +0000

    feat: implement Ed25519 signing function (#42)

    ```agentmark-manifest
    {
      "version": "1.0",
      "provider": "anthropic",
      "model": "claude-sonnet-4-20250514",
      "request_id": "req_011CZRtQztYq...",
      "output_hash": "sha256:a1b2c3d4...",
      "challenge_token": "agentmark-3f9a2b1c4d5e6f7a",
      "challenge_echo_verified": true,
      "pipeline_key": "karta-coder-v1",
      "timestamp": "2026-04-17T10:22:47Z",
      "signature": "TuBWjzVsxEwy33mS..."
    }
    ```
```

The manifest proves:

- **output_hash** — the committed code matches the raw LLM response, byte-for-byte. No human editing occurred.
- **challenge_token** — the LLM processed this specific task. The token was in the prompt context and echoed in the response.
- **request_id** — a real API call happened at the declared provider.
- **signature** — a registered pipeline identity signed this commit.

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

```yaml
# .github/workflows/agentmark-verify.yml
- name: Verify pipeline provenance
  uses: agentmark-dev/agentmark-action@v1
  with:
    strict: true
```

## How it works

See [SPEC.md](SPEC.md) for the full technical specification, including:

- Core mechanisms (output_hash, challenge_token, request_id, signing)
- Trust tiers (cloud providers vs local models)
- Known failure modes and limitations
- Provider SDK integration (Anthropic, OpenAI)
- Verification algorithm
- Roadmap (notary service, TEE attestation, provider-native verification)

## Use cases

**Agent-only open source** — Projects like [Karta](https://karta.build) where no human ever commits code. agentmark provides cryptographic proof of that property.

**Enterprise AI code governance** — Commit-level traceability for the 30% of code that AI tools are now generating.

**Defense and critical infrastructure** — Supply chain verification for AI-generated code in regulated environments.

## Relationship to existing standards

agentmark complements, not replaces, existing standards:

| Standard | What it covers | agentmark adds |
|---|---|---|
| SLSA | Build pipeline integrity | AI authorship at commit level |
| SBOM / AI-BOM | Inventory of models used | Which API call produced which code |
| C2PA | Media provenance | Code-commit equivalent |
| sigstore | Artifact signing | AI-aware manifest layer |

## Known limitations

agentmark proves pipeline integrity, not autonomous intent. A human running the complete pipeline (real API call, verbatim commit, valid manifest) is indistinguishable from an agent — and this is by design. They have built an agent.

Full list of failure modes and limitations in [SPEC.md §4](SPEC.md#4-known-failure-modes-and-limitations).

## Status

Pre-release. The specification is stable for review. The Python SDK and GitHub App are under development.

- [x] Specification (SPEC.md v0.1)
- [x] Technical validation (test scripts)
- [ ] Python SDK (`pip install agentmark`)
- [ ] GitHub App (challenge issuance)
- [ ] GitHub Action (CI verification)
- [ ] Pipeline registry
- [ ] agentmark.dev landing site

## Contributing

agentmark is an open standard. Contributions welcome:

- Spec feedback and edge cases
- Provider integrations (Google Gemini, Mistral, Ollama)
- SDK implementations (TypeScript, Go, Rust)
- Framework integrations (LangChain, CrewAI, AutoGen)

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0. See [LICENSE](LICENSE).

---

*Built by [CloudDon Research](https://clouddon.ai) · [agentmark.dev](https://agentmark.dev)*
