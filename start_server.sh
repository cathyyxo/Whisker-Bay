#!/bin/bash
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 server.py
else
  echo "Python 3 isn't installed. Get it free from https://www.python.org/downloads/"
fi
read -r -p "Server stopped. Press Enter to close..."
