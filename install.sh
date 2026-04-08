#!/bin/bash
set -euo pipefail

echo "Installing agent-mem..."
pip install -e . --quiet
echo "Installed. Run: agent-mem init"
echo "Then save context with: agent-mem summarize --summary \"...\""
echo "Recall later with: agent-mem recall \"current goal\""
