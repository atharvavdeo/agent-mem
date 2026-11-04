# easy-agent-mem — Persistent Coding Memory

Companion skill for the open-source [easy-agent-mem](https://pypi.org/project/easy-agent-mem/) CLI and local MCP server. Retrieve project context, save sourced decisions, review changed evidence and carry a durable handoff into a fresh coding chat. Optional Obsidian export; local fallback is supported.

## MCP and skill listings

<p>
  <a href="https://glama.ai/mcp/servers/atharvavdeo/agent-mem"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/glama.png" alt="Glama: MCP live" width="244" height="36"></a>
  <a href="https://plugandship.dev/p/easy-agent-mem"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/plug-and-ship.png" alt="Plug and Ship: Public page" width="244" height="36"></a>
  <a href="https://github.com/atharvavdeo/agent-mem/tree/main/skills/easy-agent-mem"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/github-skill.png" alt="Agent skill: GitHub" width="244" height="36"></a>
</p>

<details>
<summary>Submissions awaiting review</summary>

<p>
  <a href="https://www.agensi.io/dashboard#my-skills"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/agensi.png" alt="Agensi: In review" width="244" height="36"></a>
  <a href="https://mcpmarket.com/submit"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/mcp-market-server.png" alt="MCP Market: MCP queued" width="244" height="36"></a>
  <a href="https://mcpmarket.com/submit?type=skill"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/mcp-market-skill.png" alt="MCP Market: Skill queued" width="244" height="36"></a>
  <a href="https://mcp.tc/s/EtQEL5tmbkOM785j"><img src="https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/listing-badges/mcp-tc.png" alt="mcp.tc: In review" width="244" height="36"></a>
</p>

Agensi is in review. MCP Market has separate server and skill submissions in its free queue. mcp.tc is waiting for human review. Pending links open the creator dashboard, submission forms, or status receipt; they are not approved listing pages.

</details>

[All listings, approval checks and platform links](../../docs/MARKETPLACE-LINKS.md). Status labels were checked on **4 November 2026** and are updated manually.

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
