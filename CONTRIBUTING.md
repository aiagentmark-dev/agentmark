# Contributing to agentmark

agentmark is an open standard. Contributions are welcome across three areas:

## 1. Specification feedback

The most valuable contribution right now is stress-testing [SPEC.md](SPEC.md).

- Are the failure modes in §4 complete? What attacks are missing?
- Is the manifest schema in §7 sufficient? What fields are missing?
- Is the verification algorithm in §8 correct and complete?
- Are there edge cases in the provider integrations (§9) we haven't considered?

Open an issue with the `spec` label.

## 2. Provider integrations

Currently supported: Anthropic, OpenAI, local (Ollama).

Wanted:
- Google Gemini (`sdk/python/agentmark/providers.py`)
- Mistral
- Cohere
- Any other provider that returns a `request_id` header

Each provider needs:
- `call()` method using `with_raw_response` pattern
- Correct header name for `request_id`
- Code extraction from provider-specific response structure
- Tests in `sdk/python/tests/`

## 3. SDK implementations

The Python SDK is the reference implementation. Wanted:

- TypeScript/Node.js SDK
- Go SDK
- Rust SDK

Each SDK must implement the same manifest schema and verification algorithm as the Python reference.

## 4. Framework integrations

Integrations that make agentmark easy to use with popular agent frameworks:

- LangChain
- CrewAI
- AutoGen
- LangGraph
- OpenClaw

## Development setup

```bash
cd sdk/python
pip install -e ".[dev,all]"
pytest tests/
```

## Code of conduct

Be direct, be honest, be kind. This is a technical project — correctness matters more than consensus.
