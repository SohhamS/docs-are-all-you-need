"""Code access. See `protocol.py` for the contract, which is load-bearing."""

from __future__ import annotations

import os

from docverify.codetools.fake import FakeCodeTools
from docverify.codetools.mcp import McpCodeTools
from docverify.codetools.protocol import CodeTools
from docverify.config import CodeToolsConfig

__all__ = ["CodeTools", "FakeCodeTools", "McpCodeTools", "build_codetools"]


def build_codetools(cfg: CodeToolsConfig, *, fake_files: dict[str, str] | None = None) -> CodeTools:
    """Factory. Add new backends here and nowhere else."""
    if cfg.kind == "fake":
        return FakeCodeTools(fake_files or {}, repo=cfg.repo or "fake/repo")
    if cfg.kind == "mcp":
        url = os.environ.get(cfg.mcp_url_env, "")
        if not url:
            raise RuntimeError(f"{cfg.mcp_url_env} is not set")
        return McpCodeTools(
            url=url,
            token=os.environ.get(cfg.mcp_token_env),
            repo=cfg.repo,
            timeout_s=cfg.timeout_s,
        )
    raise ValueError(f"unknown codetools kind: {cfg.kind!r}")
