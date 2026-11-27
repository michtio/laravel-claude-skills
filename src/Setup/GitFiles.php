<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * Content of the fixed files the setup writes: the commit-msg hook, the secret
 * scan step and its gitleaks config, and the .gitignore files of a package's
 * local Laravel skeleton.
 *
 * @author michtio
 */
final class GitFiles
{
    // Constants
    // =========================================================================

    /**
     * The commit-msg hook.
     */
    public const COMMIT_MSG = '.githooks/commit-msg';

    /**
     * The secret scan step of the gate command.
     */
    public const GITLEAKS_CHECK = '.githooks/gitleaks-check';

    /**
     * The gitleaks configuration.
     */
    public const GITLEAKS_CONFIG = '.gitleaks.toml';

    /**
     * The .gitignore files of the directories Laravel needs under a package's own skeleton.
     */
    public const SKELETON_IGNORES = [
        'bootstrap/cache/.gitignore',
        'storage/logs/.gitignore',
        'storage/framework/cache/.gitignore',
        'storage/framework/sessions/.gitignore',
        'storage/framework/views/.gitignore',
    ];

    /**
     * A .gitignore that keeps the directory and ignores what is written into it.
     */
    public const IGNORE_ALL = "*\n!.gitignore\n";

    // Public Methods
    // =========================================================================

    /**
     * The commit-msg hook: rejects a message with an attribution trailer or a
     * "generated with" line (comment lines excluded), naming the line.
     *
     * @author michtio
     */
    public static function commitMsg(): string
    {
        return <<<'SH'
#!/bin/sh
# Written by claude-skills:setup. Rejects a commit message that carries an
# attribution trailer (Co-Authored-By, Claude-Session, Assisted-by,
# Generated-by) or a "Generated with" line. Lines starting with # are ignored.
# Active once `git config core.hooksPath .githooks` is set.

message_file=$1

found=$(grep -v '^#' "$message_file" | grep -i -E '^(co-authored-by|claude-session|assisted-by|generated-by):|generated with' | head -n 1)

if [ -n "$found" ]; then
    echo "commit-msg: remove this attribution line from the commit message: $found" >&2
    exit 1
fi

exit 0

SH;
    }

    /**
     * The secret scan step: gitleaks with the project config; skipped with a message
     * locally when gitleaks is missing, required when CI is set.
     *
     * @author michtio
     */
    public static function gitleaksCheck(): string
    {
        return <<<'SH'
#!/bin/sh
# Written by claude-skills:setup. The secret scan step of `composer test`.
# Runs gitleaks with .gitleaks.toml. Without gitleaks it skips locally and
# fails in CI (the CI variable set), so CI never passes without the scan.

if command -v gitleaks >/dev/null 2>&1; then
    exec gitleaks detect --source . --config .gitleaks.toml --no-banner
fi

if [ -n "${CI:-}" ]; then
    echo "gitleaks is required in CI: install it before running composer test" >&2
    exit 1
fi

echo "gitleaks not found, skipping the secret scan (install gitleaks to run it locally)"
exit 0

SH;
    }

    /**
     * The gitleaks configuration: the default rules plus allowlisted fixture paths.
     *
     * @author michtio
     */
    public static function gitleaksConfig(): string
    {
        return <<<'TOML'
# Written by claude-skills:setup. Gitleaks' default rules, with test fixtures and
# the example environment file allowlisted (their values are placeholders).
title = "claude-skills"

[extend]
useDefault = true

[allowlist]
description = "Test fixtures and example environment values"
paths = [
    '''(^|/)tests/Fixtures/''',
    '''(^|/).env.example$''',
]

TOML;
    }
}
