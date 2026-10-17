#!/bin/bash
# Commit and push pdps/ PDF files in batches under 500MB per push.

set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

MAX_BYTES=$((450 * 1024 * 1024))  # 450MB to leave margin
BATCH=1
BATCH_SIZE=0
BATCH_FILES=()

flush_batch() {
    if [ ${#BATCH_FILES[@]} -eq 0 ]; then
        return
    fi
    echo "=== Batch $BATCH: ${#BATCH_FILES[@]} files, ~$((BATCH_SIZE / 1024 / 1024))MB ==="
    printf '%s\0' "${BATCH_FILES[@]}" | xargs -0 git add
    git commit -m "pdps data batch $BATCH"
    git push
    echo "=== Batch $BATCH pushed ==="
    BATCH=$((BATCH + 1))
    BATCH_SIZE=0
    BATCH_FILES=()
}

# Collect untracked and modified files under pdps/
while IFS= read -r -d '' file; do
    fsize=$(stat -c%s "$file" 2>/dev/null || echo 0)

    if (( BATCH_SIZE + fsize > MAX_BYTES )) && [ ${#BATCH_FILES[@]} -gt 0 ]; then
        flush_batch
    fi

    BATCH_FILES+=("$file")
    BATCH_SIZE=$((BATCH_SIZE + fsize))
done < <(git ls-files --others --modified -z -- pdps/)

flush_batch

echo "Done! All pdps files committed and pushed."
