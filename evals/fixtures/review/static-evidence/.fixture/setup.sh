#!/bin/sh
# Builds the repository the deep-static-evidence case runs in: a base commit, then the
# builder's work left uncommitted, so `git diff HEAD` is the change under review. See
# ../weakened-tests/.fixture/setup.sh for the mechanism.
set -eu
stages=$(mktemp -d)
cp -R .fixture "$stages/fixture"
rm -rf .fixture
git init -q
git config user.email "fixture@example.invalid"
git config user.name "Fixture"
cp -R "$stages/fixture/base/." .
git add -A
git commit -q -m "base"
cp -R "$stages/fixture/build/." .
rm -rf "$stages"
