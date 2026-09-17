#!/usr/bin/env bash
# Install SAT-SA from the offline bundle with zero network (inside the bundle).
#   bash install_offline.sh
set -euo pipefail
pip install --no-index --find-links packaging/wheels -e .[lite]
echo "SAT-SA installed. Run: satsa --help"
