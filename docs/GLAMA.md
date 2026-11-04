# Glama and Docker

The MCP transport is stdio. Core memory save/recall needs no API key.

## Glama build specification

Glama generates its own Dockerfile; configure its Dockerfile admin form rather than assuming it uses the repository Dockerfile.

Build steps (JSON array):

```json
["python -m venv /opt/agent-mem-venv", "/opt/agent-mem-venv/bin/python -m pip install '.[mcp]' 'mcp>=1,<2'", "mkdir -p /tmp/agent-mem-workspace"]
```

CMD arguments:

```json
["sh", "-c", "cd /tmp/agent-mem-workspace && exec /opt/agent-mem-venv/bin/agent-mem serve --force-stdio"]
```

Use Python **3.12** and Node.js **22** in the Glama form. The MCP SDK is constrained to 1.x because this release uses FastMCP 1.x APIs.

Environment schema: `{"type":"object","properties":{},"additionalProperties":false}`.
Placeholder parameters: `{}`. No secret or host vault is required for introspection.

Build, inspect the MCP tool discovery/test logs, then publish a Glama release only after its checks succeed. A GitHub release does not create a Glama release.

## Local Docker

```sh
docker build -t easy-agent-mem:0.8.0 .
docker run --rm -i easy-agent-mem:0.8.0
```

The image runs as non-root, with an empty `/workspace`. Without a mounted directory, container memory is disposable. For actual coding use, mount the intended project (including its Git metadata) as `/workspace`; grant that directory write access to container UID 10001. For example on a compatible host:

```sh
docker run --rm -i --mount type=bind,src=/absolute/path/to/project,dst=/workspace easy-agent-mem:0.8.0
```

Only mount a project the agent is authorized to access. Local memory is written below `/workspace/.agent-memory/`. Linked worktrees may require their common Git directory to be mounted at its expected path. Evidence checks need the project files inside the container. A hosted Glama instance cannot see your computer's repositories or Obsidian vault; its storage lifecycle is controlled by the hosting platform. Use the local stdio installation for access to local projects, or configure appropriate persistent hosting storage explicitly.

The build context allowlist excludes local memory, configuration, credentials, output artifacts, and Git history. The image contains application source, package metadata, license and README only.
