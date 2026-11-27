<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Profile;

/**
 * The package-verdicts register, with a project's profile verdicts applied.
 *
 * The register is the table in
 * `resources/boost/skills/laravel-package-verdicts/references/register.md`: one row
 * per package with its use (`use`, `avoid` or `depends`), reason, conditions and the
 * date it was last checked. A profile's `verdicts` take precedence: an entry
 * replaces the register row for its package as a whole (a field it leaves out is
 * empty, never inherited), and a package only the profile names is added. The
 * setup writes nothing for verdicts; agents read this merged view.
 *
 * @author michtio
 */
final class Verdicts
{
    // Constants
    // =========================================================================

    /**
     * The register file, relative to the package root.
     */
    public const REGISTER = 'resources/boost/skills/laravel-package-verdicts/references/register.md';

    // Public Methods
    // =========================================================================

    /**
     * The package's own register: package name => [use, reason, conditions, checked].
     *
     * @return array<string, array{use: string, reason: string, conditions: string, checked: string}>
     * @author michtio
     */
    public static function register(): array
    {
        $file = dirname(__DIR__, 2).'/'.self::REGISTER;
        $lines = is_file($file) ? (file($file, FILE_IGNORE_NEW_LINES) ?: []) : [];
        $register = [];

        foreach ($lines as $line) {
            if (! str_starts_with($line, '| `')) {
                continue;
            }

            $cells = self::cells($line);

            if (count($cells) < 5) {
                continue;
            }

            $register[trim($cells[0], '` ')] = [
                'use' => $cells[1],
                'reason' => $cells[2],
                'conditions' => $cells[3],
                'checked' => $cells[4],
            ];
        }

        return $register;
    }

    /**
     * The register with the verdicts of `<root>/.ai/skills-profile.json` merged over
     * it by package name: the profile's entry replaces the row, new packages are added.
     * Contract API (tests/Profile/CONTRACT.md), proven by tests/Profile/ProfileVerdictsTest.php.
     *
     * @api
     * @return array<string, array{use: string, reason: string, conditions: string, checked: string}>
     * @throws ProfileException When the profile is invalid.
     * @author michtio
     */
    public static function merged(string $root): array
    {
        $merged = self::register();

        foreach (Profile::load($root)->verdicts() as $package => $verdict) {
            $merged[(string) $package] = [
                'use' => (string) $verdict['use'],
                'reason' => (string) $verdict['reason'],
                'conditions' => is_string($verdict['conditions'] ?? null) ? $verdict['conditions'] : '',
                'checked' => is_string($verdict['checked'] ?? null) ? $verdict['checked'] : '',
            ];
        }

        return $merged;
    }

    // Private Methods
    // =========================================================================

    /**
     * The trimmed cells of one Markdown table row (an escaped `\|` stays in its cell).
     *
     * @return list<string>
     * @author michtio
     */
    private static function cells(string $line): array
    {
        $line = trim($line);
        $line = substr($line, 1, str_ends_with($line, '|') ? -1 : null);
        $cells = preg_split('/(?<!\\\\)\|/', $line) ?: [];

        return array_map(static fn (string $cell): string => str_replace('\\|', '|', trim($cell)), $cells);
    }
}
