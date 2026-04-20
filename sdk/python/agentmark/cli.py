"""
agentmark.cli — command line interface

Commands:
  agentmark verify          Verify commits in current repo
  agentmark sign            Sign a manifest (for agent pipeline use)
  agentmark challenge       Issue a challenge token
  agentmark register        Register a pipeline key
  agentmark inspect         Inspect a manifest from a commit
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import subprocess
import hashlib


def main():
    parser = argparse.ArgumentParser(
        prog="agentmark",
        description="Cryptographic provenance for AI-generated code",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # verify
    p_verify = sub.add_parser("verify", help="Verify commit pipeline provenance")
    p_verify.add_argument("--commits", help="Commit range e.g. abc123..def456")
    p_verify.add_argument("--strict", action="store_true", default=True,
                          help="Require request_id for cloud providers (default: True)")
    p_verify.add_argument("--no-strict", dest="strict", action="store_false")
    p_verify.add_argument("--registry", default=None, help="Registry URL")
    p_verify.add_argument("--output", default=None, help="Write JSON report to file")
    p_verify.add_argument("--quiet", action="store_true")

    # sign
    p_sign = sub.add_parser("sign", help="Sign a manifest")
    p_sign.add_argument("--manifest", required=True, help="Path to manifest JSON")
    p_sign.add_argument("--key", required=True, help="Path to Ed25519 private key (DER)")
    p_sign.add_argument("--pipeline-key", required=True, help="Registered pipeline ID")

    # challenge
    p_challenge = sub.add_parser("challenge", help="Issue a challenge token")
    p_challenge.add_argument("--task", required=True, help="Task reference e.g. owner/repo#42")

    # register
    p_register = sub.add_parser("register", help="Register a pipeline key")
    p_register.add_argument("--pipeline-id", required=True, help="Pipeline identifier")
    p_register.add_argument("--public-key", required=True, help="Path to Ed25519 public key (DER)")
    p_register.add_argument("--operator", required=True, help="Operator GitHub handle")

    # inspect
    p_inspect = sub.add_parser("inspect", help="Inspect manifest from a commit")
    p_inspect.add_argument("commit", help="Commit hash")

    args = parser.parse_args()

    if args.command == "verify":
        cmd_verify(args)
    elif args.command == "sign":
        cmd_sign(args)
    elif args.command == "challenge":
        cmd_challenge(args)
    elif args.command == "register":
        cmd_register(args)
    elif args.command == "inspect":
        cmd_inspect(args)


def cmd_verify(args):
    from agentmark.manifest import Manifest
    from agentmark.registry import PipelineRegistry
    from agentmark.verifier import run_verification

    registry = PipelineRegistry(registry_url=args.registry)

    # Get commits to verify
    commits = _get_commits(args.commits)
    if not commits:
        _err("No commits to verify.")
        sys.exit(1)

    if not args.quiet:
        print(f"agentmark verify — checking {len(commits)} commit(s)\n")

    results = []
    all_pass = True

    for commit_hash in commits:
        message = _git("log", "--format=%B", "-n1", commit_hash)
        author = _git("log", "--format=%an <%ae>", "-n1", commit_hash)

        try:
            manifest = Manifest.from_commit_message(message)
        except ValueError:
            result = {
                "commit": commit_hash[:12],
                "author": author,
                "valid": False,
                "failure_reason": "manifest_missing",
                "checks": {},
            }
            results.append(result)
            all_pass = False
            if not args.quiet:
                _print_result(result)
            continue

        # Get raw bytes — for now we reconstruct from prompt log if available
        # In production the agent would store raw_bytes alongside the commit
        raw_bytes = _get_raw_bytes(manifest, commit_hash)

        verify_result = run_verification(
            manifest=manifest,
            raw_bytes=raw_bytes,
            registry=registry,
            strict=args.strict,
        )

        result = {
            "commit": commit_hash[:12],
            "author": author,
            "valid": verify_result.valid,
            "failure_reason": verify_result.failure_reason,
            "checks": verify_result.checks,
            "manifest": manifest.to_dict(),
        }
        results.append(result)

        if not verify_result.valid:
            all_pass = False

        if not args.quiet:
            _print_result(result)

    # Summary
    passed = sum(1 for r in results if r["valid"])
    total = len(results)

    if not args.quiet:
        print(f"\n{'─' * 50}")
        print(f"Result: {passed}/{total} commits verified")
        if all_pass:
            print("✓ PIPELINE VERIFIED")
        else:
            print("✗ VERIFICATION FAILED")

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"results": results, "summary": {
                "passed": passed, "total": total, "all_pass": all_pass
            }}, f, indent=2)
        if not args.quiet:
            print(f"\nReport written to {args.output}")

    sys.exit(0 if all_pass else 1)


def cmd_challenge(args):
    from agentmark.challenge import ChallengeRegistry
    registry = ChallengeRegistry()
    token = registry.issue(args.task)
    print(token)


def cmd_inspect(args):
    from agentmark.manifest import Manifest
    message = _git("log", "--format=%B", "-n1", args.commit)
    try:
        manifest = Manifest.from_commit_message(message)
        print(json.dumps(manifest.to_dict(), indent=2))
    except ValueError as e:
        _err(str(e))
        sys.exit(1)


def cmd_sign(args):
    with open(args.manifest) as f:
        data = json.load(f)
    from agentmark.manifest import Manifest
    from agentmark.signing import sign_manifest
    manifest = Manifest(**data)
    with open(args.key, "rb") as f:
        key_bytes = f.read()
    manifest.signature = sign_manifest(key_bytes, manifest)
    print(json.dumps(manifest.to_dict(), indent=2))


def cmd_register(args):
    # TODO: POST to registry API
    print(f"Registering pipeline: {args.pipeline_id}")
    print(f"Operator: {args.operator}")
    print(f"Submit at: https://registry.agentmark.dev/register")
    print(f"\nFor local testing, call registry.register_local(pipeline_id, public_key_bytes)")


# ── helpers ──────────────────────────────────────────────────────────────────

def _git(*args) -> str:
    result = subprocess.run(
        ["git"] + list(args),
        capture_output=True, text=True
    )
    return result.stdout.strip()


def _get_commits(commit_range: str | None) -> list[str]:
    if commit_range:
        out = _git("log", "--format=%H", commit_range)
    else:
        # Default: last commit only
        out = _git("log", "--format=%H", "-n1")
    return [c for c in out.splitlines() if c]


def _get_raw_bytes(manifest, commit_hash: str) -> bytes:
    """
    Retrieve raw LLM response bytes for verification.
    In v1.0 this reads from prompt_log if available.
    In production the agent would store raw_bytes in a content-addressed store.
    """
    if manifest.prompt_log and os.path.exists(manifest.prompt_log):
        with open(manifest.prompt_log, "rb") as f:
            data = json.load(f)
            if "raw_bytes_b64" in data:
                import base64
                return base64.b64decode(data["raw_bytes_b64"])
            if "raw_response" in data:
                return data["raw_response"].encode()
    # Fallback: cannot verify output_hash without raw bytes
    # Return empty bytes — output_hash check will fail
    return b""


def _print_result(result: dict):
    status = "✓ PASS" if result["valid"] else f"✗ FAIL ({result['failure_reason']})"
    print(f"  {result['commit']} {status}")
    if not result["valid"] and result.get("checks"):
        for check, passed in result["checks"].items():
            if isinstance(passed, bool) and not passed:
                print(f"    ✗ {check}")


def _err(msg: str):
    print(f"agentmark: error: {msg}", file=sys.stderr)


if __name__ == "__main__":
    main()
