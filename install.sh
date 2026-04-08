#!/bin/bash
set -euo pipefail

echo "Installing agent-mem..."
pip install -e . --quiet
echo "Installed. Run: agent-mem init"
echo "Then keep: agent-mem serve"