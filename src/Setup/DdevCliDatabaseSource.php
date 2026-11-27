<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Symfony\Component\Process\ExecutableFinder;
use Symfony\Component\Process\Process;

/**
 * The DdevDatabaseSource that asks the installed DDEV, first match wins:
 * - `ddev describe -j` in the project root (`raw.database_type`, `raw.database_version`);
 * - inside a DDEV web container, where no `ddev` binary exists, `DDEV_DATABASE`
 *   (for example `mariadb:11.8`), which DDEV sets to the project's database;
 * - the default `ddev config --help` prints for `--database` (`default "mariadb:11.8"`).
 *
 * Every command runs as an argument list, never through a shell. A missing `ddev`
 * binary, a failing command or output that does not parse means that source has
 * nothing; null when none has.
 *
 * @author michtio
 */
final class DdevCliDatabaseSource implements DdevDatabaseSource
{
    // Constants
    // =========================================================================

    /**
     * The database types DDEV runs.
     */
    public const TYPES = ['mariadb', 'mysql', 'postgres'];

    // Public Methods
    // =========================================================================

    /**
     * Read the project's database from the installed DDEV.
     *
     * @return array{type: string, version: string}|null
     * @author michtio
     */
    public function read(string $root): ?array
    {
        $ddev = (new ExecutableFinder())->find('ddev');

        if ($ddev !== null) {
            $described = $this->described($this->run([$ddev, 'describe', '-j'], $root));

            if ($described !== null) {
                return $described;
            }
        }

        $environment = getenv('DDEV_DATABASE');

        if (is_string($environment) && ($parsed = self::parse($environment)) !== null) {
            return $parsed;
        }

        if ($ddev !== null && preg_match('/--database\b[^\n]*\(default "([^"]+)"\)/', (string) $this->run([$ddev, 'config', '--help'], $root), $match) === 1) {
            return self::parse($match[1]);
        }

        return null;
    }

    /**
     * Parse `<type>:<version>` (as DDEV writes it) into type and version, or null.
     *
     * @return array{type: string, version: string}|null
     * @author michtio
     */
    public static function parse(string $value): ?array
    {
        if (preg_match('/^([a-z]+):(\d+(?:\.\d+)?)$/D', trim($value), $match) !== 1) {
            return null;
        }

        return self::valid($match[1], $match[2]);
    }

    // Private Methods
    // =========================================================================

    /**
     * Type and version when both are ones DDEV runs, else null.
     *
     * @return array{type: string, version: string}|null
     * @author michtio
     */
    private static function valid(mixed $type, mixed $version): ?array
    {
        if (! is_string($type) || ! in_array($type, self::TYPES, true)) {
            return null;
        }

        if (! is_string($version) || preg_match('/^\d+(?:\.\d+)?$/D', $version) !== 1) {
            return null;
        }

        return ['type' => $type, 'version' => $version];
    }

    /**
     * The database from `ddev describe -j` output (one JSON object per line), or null.
     *
     * @return array{type: string, version: string}|null
     * @author michtio
     */
    private function described(?string $output): ?array
    {
        foreach (preg_split('/\R/', (string) $output) ?: [] as $line) {
            $decoded = json_decode($line, true);
            $raw = is_array($decoded) && is_array($decoded['raw'] ?? null) ? $decoded['raw'] : null;

            if ($raw !== null && isset($raw['database_type'])) {
                return self::valid($raw['database_type'], $raw['database_version'] ?? null);
            }
        }

        return null;
    }

    /**
     * Run a command (an argument list, no shell) in the root: its output, or null when it fails or cannot start.
     *
     * @param list<string> $command
     * @author michtio
     */
    private function run(array $command, string $root): ?string
    {
        try {
            $process = new Process($command, is_dir($root) ? $root : null);
            $process->setTimeout(60);
            $process->run();
        } catch (\Throwable) {
            return null;
        }

        return $process->isSuccessful() ? $process->getOutput() : null;
    }
}
