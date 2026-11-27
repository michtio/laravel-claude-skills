#!/bin/sh
# Builds the repository the review-weakened-tests case runs in. The runner copies this
# folder into a temp dir and runs this script there (no git repository exists yet); the
# script makes every commit. It leaves the builder's work uncommitted, so `git diff HEAD`
# is the change under review and HEAD is the gate commit.
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
cp -R "$stages/fixture/gate/." .
git add tests
git commit -q -m "test(gate): S1"
cp -R "$stages/fixture/build/." .
rm -rf "$stages"
