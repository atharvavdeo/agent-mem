# easy-agent-mem — Persistent Coding Memory

Companion skill for the open-source [easy-agent-mem](https://pypi.org/project/easy-agent-mem/) CLI and local MCP server. Retrieve project context, save sourced decisions, review changed evidence and carry a durable handoff into a fresh coding chat. Optional Obsidian export; local fallback is supported.

## Install the skill

```sh
npx skills add atharvavdeo/agent-mem --skill easy-agent-mem
```

Alternatively, copy this skill folder into your agent's supported skills location. Installing the skill does not install the local application or its MCP connection.

## Connect the runtime

Requires Python 3.10+ and a compatible coding agent. Install the MCP extra in your chosen Python environment:

```sh
python3 -m pip install 'easy-agent-mem[mcp]==0.8.0'
```

Configure your agent to launch the installed `agent-mem` executable with arguments `serve --force-stdio` and the intended repository as working directory. Use your client's documented MCP configuration format. Obsidian and separate provider API keys are optional for the core local-memory workflow.

## Example requests

- Recall the storage decision before continuing this task.
- Remember this accepted constraint and cite docs/architecture.md as evidence.
- Review saved decisions affected by the files I changed.
- Save a concise handoff and give me the handle for the next chat.

Private continuity requires the same repository, worktree, branch and session handle. The skill operates when invoked; it does not install automatic lifecycle hooks. Check current code before relying on consequential historical claims.

## Documentation

- [Skill workflow](SKILL.md)
- [Setup and troubleshooting](references/setup.md)
- [Tool-call examples](references/workflows.md)
- [Full application command reference](references/commands.md)

Local synthetic MCP save/restart/recall and evidence-change operations were exercised against PyPI 0.8.0 on macOS. This is not an autonomous-agent or universal IDE compatibility guarantee.

MIT licensed. The application and this companion skill are free.
