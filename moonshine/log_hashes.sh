#!/bin/bash

OUTFILE="commit_trees.txt"

exec 3>"$OUTFILE"

for commit in $(git rev-list HEAD); do
    echo "===== COMMIT: $commit =====" >&3
    git ls-tree -r "$commit" >&3
    echo >&3
done

exec 3>&-
