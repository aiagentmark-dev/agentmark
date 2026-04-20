"""agentmark.registry — pipeline key registry"""

import os


class PipelineRegistry:
    """
    Pipeline signing key registry.
    In production backed by agentmark.dev registry API.
    For local use, keys can be added directly.
    """

    def __init__(self, registry_url: str | None = None):
        self._url = registry_url or os.environ.get(
            "AGENTMARK_REGISTRY_URL", "https://registry.agentmark.dev"
        )
        self._local: dict[str, bytes] = {}

    def register_local(self, pipeline_id: str, public_key_bytes: bytes):
        """Register a key locally (for testing)."""
        self._local[pipeline_id] = public_key_bytes

    def get_public_key(self, pipeline_id: str) -> bytes | None:
        """Fetch public key bytes for a pipeline ID."""
        if pipeline_id in self._local:
            return self._local[pipeline_id]
        # TODO: fetch from registry API
        return None

    def is_registered(self, pipeline_id: str) -> bool:
        return pipeline_id in self._local
