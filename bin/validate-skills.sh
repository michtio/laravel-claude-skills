#!/usr/bin/env bash
#
# Validate every resources/boost/skills/*/SKILL.md frontmatter against the Agent
# Skills spec (https://agentskills.io/specification) and Claude Code's listing cap
# (https://code.claude.com/docs/en/skills).
#
# Ported from craftcms-claude-skills (bin/validate-skills.sh, 1.31.0). The
# Craft-only version-script checks are dropped; skills live where Boost reads
# them, resources/boost/skills/<name>/SKILL.md.
#
#   bash bin/validate-skills.sh               # this package
#   bash bin/validate-skills.sh --root DIR    # another tree (self-tests)
#
# Checks, per skill:
#   - frontmatter parses as strict YAML
#   - only known keys: the spec's fields plus Claude Code's `when_to_use`
#   - name: 1-64 chars, lowercase letters/digits/hyphens, matches the directory
#   - description: 1-1024 chars (spec limit)
#   - description + " - " + when_to_use: <= 1300 chars, the package budget
#     (Claude Code truncates the combined text beyond 1536)
#   - SKILL.md body (after the frontmatter) <= 12 KB: it loads in full with the
#     skill, so detail lives in references/
#
# A missing resources/boost/skills/ directory means nothing to check (exit 0).
# Exits non-zero on any failure.
#
# Requires: ruby (macOS system ruby and every GitHub ubuntu runner have it).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [ $# -gt 0 ]; do
  case "$1" in
    --root)
      [ $# -ge 2 ] || { echo "usage: $0 [--root DIR]" >&2; exit 2; }
      ROOT="$2"
      shift 2
      ;;
    *)
      echo "usage: $0 [--root DIR]" >&2
      exit 2
      ;;
  esac
done

SKILLS_DIR="$ROOT/resources/boost/skills"
if [ ! -d "$SKILLS_DIR" ]; then
  echo "no resources/boost/skills/ under $ROOT: nothing to check"
  exit 0
fi

shopt -s nullglob
files=("$SKILLS_DIR"/*/SKILL.md)
if [ ${#files[@]} -eq 0 ]; then
  echo "no skills under $SKILLS_DIR: nothing to check"
  exit 0
fi

ruby -ryaml - "${files[@]}" <<'RUBY'
ALLOWED = %w[name description license compatibility metadata allowed-tools when_to_use]
DESC_MAX = 1024
BODY_MAX = 12 * 1024 # bytes after the frontmatter (~3K tokens); detail belongs in references/
LISTING_MAX = 1300 # package budget: ~15% under Claude Code's 1,536-char listing cap
SEPARATOR = " - "

failures = 0
ARGV.each do |path|
  skill = File.basename(File.dirname(path))
  errors = []
  parts = File.read(path).split(/^---\s*$/, 3)

  if parts.length < 3 || !parts[0].strip.empty?
    errors << "missing --- frontmatter block"
  else
    begin
      fm = YAML.safe_load(parts[1])
    rescue Psych::Exception => e
      fm = nil
      errors << "invalid YAML: #{e.message.lines.first.strip}"
    end

    if fm.is_a?(Hash)
      extra = fm.keys - ALLOWED
      errors << "unknown keys: #{extra.join(', ')}" unless extra.empty?

      name = fm["name"].to_s
      errors << "name '#{name}' does not match directory '#{skill}'" unless name == skill
      errors << "name must be 1-64 lowercase letters, digits, hyphens" unless name.match?(/\A[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?\z/)

      desc = fm["description"].to_s
      wtu = fm["when_to_use"].to_s
      errors << "description is empty" if desc.strip.empty?
      errors << "description is #{desc.length} chars (max #{DESC_MAX})" if desc.length > DESC_MAX

      listing = wtu.empty? ? desc.length : desc.length + SEPARATOR.length + wtu.length
      errors << "description + when_to_use is #{listing} chars (max #{LISTING_MAX})" if listing > LISTING_MAX
    elsif fm
      errors << "frontmatter is not a mapping"
    else
      errors << "frontmatter is empty" if errors.empty?
    end
  end

  if parts.length >= 3
    body = parts[2].bytesize
    errors << "SKILL.md body is #{body} bytes (max #{BODY_MAX}); move detail into references/" if body > BODY_MAX
  end

  if errors.empty?
    puts "ok    #{skill}"
  else
    failures += 1
    errors.each { |e| puts "FAIL  #{skill}: #{e}" }
  end
end

exit(failures.zero? ? 0 : 1)
RUBY
