# MCP and skill marketplace links

Status checked 4 November 2026. A submitted entry is not an approved public listing.

| Destination | Type | Status | Direct link |
| --- | --- | --- | --- |
| Glama | MCP server | Public; Glama release 0.8.0 published | [Server listing](https://glama.ai/mcp/servers/atharvavdeo/agent-mem) |
| Plug and Ship | MCP server | Public page; free launch scheduled for 23 November 2026 | [Product page](https://plugandship.dev/p/easy-agent-mem) |
| GitHub | Agent skill | Public source; discoverable by the skills CLI | [Installable skill folder](https://github.com/atharvavdeo/agent-mem/tree/main/skills/easy-agent-mem) |
| Agensi | Agent skill | Pending review; existing submission preserved | [Creator dashboard — requires creator sign-in](https://www.agensi.io/dashboard#my-skills) |
| MCP Market | MCP server | Submitted to free review queue; no confirmed listing URL yet | [Server submission form](https://mcpmarket.com/submit) |
| MCP Market | Agent skill | Separately submitted to free review queue; no confirmed listing URL yet | [Skill submission form](https://mcpmarket.com/submit?type=skill) |
| mcp.tc | MCP server | Waiting for human review | [Submission receipt](https://mcp.tc/s/EtQEL5tmbkOM785j) |

mcp.tc reserves [the future listing URL](https://mcp.tc/i/agent-mem), which starts working only after approval. Agensi has no confirmed public skill URL yet. MCP Market has not supplied confirmed public listing URLs. The companion-skill submission on Plug and Ship resolved to the same product page, so it is one listing, not two.

## Other platforms researched

These are platform links, not claims that easy-agent-mem is listed there.

| Platform | Current outcome of this publishing work | Link |
| --- | --- | --- |
| skills.sh | Public GitHub skill ready; CLI discovery tested. Leaderboard inclusion not verified. | [Directory](https://skills.sh/) |
| SkillsMP | GitHub indexing route researched; indexing not verified. | [About/indexing](https://skillsmp.com/about) |
| Official MCP Registry | Not submitted; current PyPI metadata needs the required namespace marker and a future package release. | [Publishing quickstart](https://modelcontextprotocol.io/registry/quickstart) |
| Cline MCP Marketplace | Not submitted; actual Cline installation validation remains required. | [Marketplace repository](https://github.com/cline/mcp-marketplace) |
| PulseMCP | Submission page was paused at inspection. | [Submission page](https://www.pulsemcp.com/submit) |
| MCP.so | Paid submission route observed; no purchase made. | [Directory](https://mcp.so/) |
| ClawHub | Not published; its MIT-0 publishing terms need a licensing decision. | [Directory](https://clawhub.ai/) |
| Smithery | Publishing route researched; no listing submitted. | [Platform](https://smithery.ai/) |
| Skill Exchange | Seller route researched; not submitted. | [Seller page](https://skillexchange.tapdot.org/become-a-seller) |

## Install the published companion skill

```sh
npx skills add atharvavdeo/agent-mem --skill easy-agent-mem
```

The skill and the MCP runtime are separate artifacts. Installing the skill does not install or connect the local MCP server.
