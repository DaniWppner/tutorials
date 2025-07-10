#!/bin/bash
# This script looks for the syzkaller commit(s) where the contents of the file /prog/prog.go in
# the syzkaller tree had the exact same contents as the one in vendor/github.com/google/syzkaller.
# We need this syzkaller version to solve the moonshine dependencies by including it in a go.mod.

# This is the result of running `git hash-object` on 
# vendor/github.com/google/syzkaller/prog/prog.go in moonshine.
TARGET_HASH="af830f33e16760412a5130ba8629b07d8da04908"
TARGET_PATH="prog/prog.go"

echo "Looking for commits where $TARGET_PATH has blob hash $TARGET_HASH"
echo

for commit in $(git rev-list HEAD); do
    FILE_HASHES=$(git ls-tree -r "$commit")

    # Extract the line for the target file (if it exists)
    LINE=$(echo "$FILE_HASHES" | awk -v path="$TARGET_PATH" '$0 ~ path {print $0}')

    if [[ -n "$LINE" ]]; then
        # Extract the blob hash from the line (3rd field)
        ACTUAL_HASH=$(echo "$LINE" | awk '{print $3}')
        
        if [[ "$ACTUAL_HASH" == "$TARGET_HASH" ]]; then
            echo "MATCH at commit $commit"
            git log -1 --oneline "$commit"
        else
            echo "No match at commit $commit (hash was $ACTUAL_HASH)"
        fi
    else
        echo "File $TARGET_PATH not present in commit $commit"
    fi
done
