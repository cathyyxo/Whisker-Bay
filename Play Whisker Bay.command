#!/bin/bash
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 play.py
else
  echo "Python 3 isn't installed. Get it free from https://www.python.org/downloads/"
  read -r -p "Press Enter to close..."
fi
