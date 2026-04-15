![easy-agent-mem header](https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/repo-header.png)

# agent-mem

**Automatic context compression and persistent memory for AI coding agents**

`agent-mem` watches your work, detects meaningful progress, and gives you a **one-paste handoff prompt** that tells your IDE agent to summarize, save memory, and start fresh with minimal context.

---

### Features

- Smart `watch` mode with file + git + idle detection
- One-paste handoff prompts (Groq powered, optional)
- Rich Obsidian-first storage with wiki-links and frontmatter
- Local fallback mode (`.agent-memory/`)
- New: **`graph` command** - builds an Obsidian-native knowledge graph from code, chat history, and memory

---

### Badges

![PyPI version](https://img.shields.io/pypi/v/easy-agent-mem)
![Python version](https://img.shields.io/pypi/pyversions/easy-agent-mem)
![License](https://img.shields.io/pypi/l/easy-agent-mem)
![GitHub stars](https://img.shields.io/github/stars/atharvavdeo/agent-mem?style=social)

---

### Quick Start

```bash
pip install easy-agent-mem

agent-mem init
agent-mem configure-groq          # optional but recommended
agent-mem watch                   # start automatic handoff mode
```

New in v0.5+:  
`agent-mem graph build` -> creates a full knowledge graph in `agent-mem-output/`

---

### New: Knowledge Graph (`agent-mem graph`)

```bash
agent-mem graph build              # Basic deterministic graph
agent-mem graph build --enrich     # Enrich with Groq (inferred relationships)
agent-mem graph build --compact    # Compact mode for large projects
```

**Output**: Clean Obsidian-ready Markdown files in `agent-mem-output/`  
- `Index.md` - beautiful dashboard
- Code structure, decisions, blockers, concepts, sessions
- Clear `EXTRACTED` vs `INFERRED` labeling with confidence scores

Open `agent-mem-output/Index.md` in Obsidian for full graph navigation and backlinks.

---

### Commands Overview

| Command                        | Description                                      |
|-------------------------------|--------------------------------------------------|
| `agent-mem init`              | Setup Obsidian / fallback + IDE rules            |
| `agent-mem configure-groq`    | Set Groq API key                                 |
| `agent-mem watch`             | Automatic one-paste handoff watcher              |
| `agent-mem graph build`       | Build knowledge graph (new)                      |
| `agent-mem summarize`         | Manual summary                                   |
| `agent-mem recall <query>`    | Search memory                                    |

---

### Project Links

- PyPI: https://pypi.org/project/easy-agent-mem/
- GitHub: https://github.com/atharvavdeo/agent-mem

---

**Made for developers who want their AI agent to actually remember things.**

---

**License**: MIT

---

### How to Update README

1. Open your `README.md`
2. Replace the entire content with the text above
3. Save and commit:

```bash
git add README.md
git commit -m "docs: update README with badges and graph feature"
git push
```

---

### What Part Requires Improvement (Specific Feedback)

**Current State (Good):**
- Core graph building works
- Compact mode and enrichment are implemented
- Output is Obsidian-friendly

**Areas that still need improvement (Priority order):**

1. **Index.md is still a bit basic**  
	-> Can be made more dashboard-like with better stats layout and visual separation.

2. **Error handling when Groq key is missing/invalid**  
	-> Currently it fails silently or shows confusing messages. Should give clear user-friendly message.

3. **Documentation in README**  
	-> The new `graph` command section is missing detailed examples and flags explanation.

4. **Performance on very large projects**  
	-> Scanning thousands of files can be slow. Compact mode helps but can be optimized further.
