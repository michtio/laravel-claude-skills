#!/bin/sh
# Rebuilds the laravel/framework source index scripts/laravel_source.py checks against.
# The only step that needs the network; scripts/check.sh reads the committed files.
#
#   sh scripts/refresh-laravel-data.sh            # pin the newest stable v13.x tag, rebuild
#   sh scripts/refresh-laravel-data.sh --tag vX.Y.Z   # pin this tag, rebuild
#   sh scripts/refresh-laravel-data.sh --check    # rebuild the committed tag's index to a
#                                                 # temp file and compare byte for byte
#
# Writes scripts/data/laravel-source-tag.txt, scripts/data/laravel-source-commit.txt (the
# commit SHA the tag resolved to) and scripts/data/laravel-source-index.tsv. Both modes
# fail when the committed tag now resolves to a different commit (a moved tag).
# A moved pin can make scripts/check.sh fail: that is the point, fix the package.
#
# Exit: 0 done (or --check: identical), 1 --check: the committed index differs,
#       2 usage, network or source error, or the pinned tag moved to another commit.
# Requires: git, python3 (3.9+).

set -u

repo=$(cd "$(dirname "$0")/.." && pwd)
url=https://github.com/laravel/framework
major=13
tag_file="$repo/scripts/data/laravel-source-tag.txt"
index="$repo/scripts/data/laravel-source-index.tsv"
commit_file="$repo/scripts/data/laravel-source-commit.txt"

mode=refresh
tag=
while [ $# -gt 0 ]; do
    case $1 in
        --check) mode=check ;;
        --tag) shift; tag=${1:-} ;;
        -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
        *) echo "refresh-laravel-data.sh: unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done

if [ "$mode" = check ]; then
    [ -n "$tag" ] || tag=$(cat "$tag_file" 2>/dev/null)
    [ -n "$tag" ] || { echo "refresh-laravel-data.sh: no tag in $tag_file" >&2; exit 2; }
    [ -f "$index" ] || { echo "refresh-laravel-data.sh: no committed index at $index" >&2; exit 2; }
    [ -s "$commit_file" ] || { echo "refresh-laravel-data.sh: no pinned commit in $commit_file" >&2; exit 2; }
elif [ -z "$tag" ]; then
    # Newest stable vMAJOR.x.y tag; pre-releases (v13.0.0-beta1) are skipped.
    tag=$(git ls-remote --tags --refs "$url" "v$major.*" | sed 's|.*refs/tags/||' \
        | grep -E "^v$major\.[0-9]+\.[0-9]+$" | sort -t. -k2,2n -k3,3n | tail -n 1)
    [ -n "$tag" ] || { echo "refresh-laravel-data.sh: no stable v$major tag found at $url" >&2; exit 2; }
fi
case $tag in
    v[0-9]*.[0-9]*.[0-9]*) ;;
    *) echo "refresh-laravel-data.sh: not a release tag: $tag" >&2; exit 2 ;;
esac

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if ! git -c advice.detachedHead=false clone --quiet --depth 1 --branch "$tag" "$url" "$tmp/framework"; then
    echo "refresh-laravel-data.sh: could not fetch $url at $tag" >&2
    exit 2
fi
sha=$(git -C "$tmp/framework" rev-parse HEAD) || exit 2

# The committed tag must still resolve to the committed commit.
pinned_tag=$(cat "$tag_file" 2>/dev/null)
pinned_sha=$(cat "$commit_file" 2>/dev/null)
if [ "$tag" = "$pinned_tag" ] && [ -n "$pinned_sha" ] && [ "$sha" != "$pinned_sha" ]; then
    echo "refresh-laravel-data.sh: laravel/framework $tag moved: pinned commit $pinned_sha, tag now resolves to $sha" >&2
    exit 2
fi

if [ "$mode" = check ]; then
    python3 "$repo/scripts/laravel_source.py" index "$tmp/framework" --tag "$tag" --out "$tmp/index.tsv" || exit 2
    if cmp -s "$tmp/index.tsv" "$index"; then
        echo "index reproduces from laravel/framework $tag"
        exit 0
    fi
    echo "index differs from a fresh build of laravel/framework $tag:" >&2
    diff "$index" "$tmp/index.tsv" | head -n 20 >&2
    exit 1
fi

python3 "$repo/scripts/laravel_source.py" index "$tmp/framework" --tag "$tag" || exit 2
echo "$sha" > "$commit_file"
sh "$repo/scripts/check.sh" >/dev/null || echo "check.sh fails against laravel/framework $tag: fix the package"
echo "done; review: git diff -- scripts/data/"
