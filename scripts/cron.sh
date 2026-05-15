#!/bin/bash
cd "$(dirname "$0")/.."

git pull

php scripts/sunshine.php

if [ -n "$(git status --porcelain docs/)" ]; then
    git add docs/
    git commit -m "sunshine data updated"
    git push
fi
