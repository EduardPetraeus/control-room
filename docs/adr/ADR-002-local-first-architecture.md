# ADR-002: Local-First Architecture

## Status
Accepted

## Date
2026-03-02

## Context
Control Room needs to decide between running as a local-only application (`python -m control_room`) or as a hosted web dashboard deployed to a server or cloud provider.

This decision affects multiple architectural concerns:
- **Heartbeat architecture:** How agents report status and how Control Room reads it.
- **Security model:** How the app accesses git repos, the filesystem, and the `gh` CLI.
- **Deployment complexity:** What infrastructure is required to run the dashboard.

The primary user is a solo developer managing 8+ repos from a single machine (Mac Mini M4).

## Decision
**Local-first.** Control Room runs as a local Python process on the developer's machine. No server deployment, no hosting, no authentication layer.

## Consequences

### Pros
- **Direct filesystem access** to git repos, YAML task files, and heartbeat files — no API layer needed.
- **No deployment infrastructure.** Start with `python -m control_room` and open a browser tab.
- **No authentication required.** Solo dev on localhost — the OS provides the security boundary.
- **`gh` CLI uses system auth.** No token management or OAuth flow needed.
- **Simpler architecture.** Fewer moving parts means fewer failure modes.
- **Non-reversible cost is low.** An HTTP/remote layer can be added later without rewriting the core.

### Cons
- **Single-device only.** Dashboard is not accessible from a phone or another machine.
- **No multi-user.** Cannot share the dashboard with collaborators.
- **No always-on monitoring.** Dashboard only runs when the developer starts it.

### Mitigations
- A future ADR can address remote access via SSH tunnel, Tailscale, or lightweight hosting if the need arises.
- The collector/model layer is decoupled from the web layer, so adding a remote interface does not require core changes.

## Implications for Heartbeat Design
Agents write JSON heartbeat files into their respective repos (e.g., `.claude/heartbeat.json`). Control Room scans the filesystem for these files. No HTTP endpoints, no pub/sub, no message queue — just file reads.

This aligns with the local-first principle: everything is a file, and the OS is the integration layer.

## Governance Mapping
Maps to **Layer 5 (Observability)** in the 7-layer governance architecture defined in `ai-governance-framework`. Control Room is the observability surface; heartbeat files are the telemetry source.
