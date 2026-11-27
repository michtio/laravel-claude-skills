<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Symfony\Component\Yaml\Yaml;

/**
 * Writes `.github/workflows/claude-skills-gate.yml` when the profile sets
 * `laravel.ci` to true: a GitHub Actions workflow that runs the project's one gate
 * command, `composer test`, exactly as it runs locally. With `ci` false (the
 * default) the file is not written, and a copy the setup wrote is deleted.
 *
 * The workflow does not depend on the runner (CI never runs DDEV), so changing the
 * runner never changes it. It follows the project:
 * - PHP: the X.Y of composer.json `config.platform.php`, else the lowest X.Y of
 *   `require.php`, else 8.4;
 * - database: for an app whose suite runs on MySQL, MariaDB or PostgreSQL, a
 *   service container with the test database the PHPUnit pins name (the image of
 *   the DDEV database when `.ddev/config.yaml` exists, else the connection's);
 * - gitleaks: installed from its release, checksum verified, because the secret
 *   scan step of `composer test` fails in CI without it.
 *
 * Actions, each on its latest major and Node 24, pinned to the major tag (checked
 * 2026-11-27 against each repository's latest release and its action.yml):
 * actions/checkout v7 (v7.0.1), shivammathur/setup-php v2 (2.40.0),
 * actions/cache v6 (v6.1.0). gitleaks 8.30.1 is its latest release on the same date.
 *
 * @author michtio
 */
final class WorkflowPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the workflow.
     */
    public const PATH = '.github/workflows/claude-skills-gate.yml';

    /**
     * The gitleaks release the workflow installs, and the sha256 of its linux_x64 archive.
     */
    public const GITLEAKS_VERSION = '8.30.1';

    public const GITLEAKS_SHA256 = '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb';

    /**
     * The PHP version when composer.json names none.
     */
    public const DEFAULT_PHP = '8.4';

    /**
     * Database images: DDEV database type => [image, default version, port, user, password].
     */
    private const DATABASES = [
        'mysql' => ['mysql', '8.4', 3306, 'root', 'root'],
        'mariadb' => ['mariadb', '11.4', 3306, 'root', 'root'],
        'postgres' => ['postgres', '17', 5432, 'postgres', 'postgres'],
    ];

    // Public Methods
    // =========================================================================

    /**
     * Take the profile's `laravel.ci` option.
     *
     * @author michtio
     */
    public function __construct(private readonly bool $ci)
    {
    }

    /**
     * Plan the workflow, or its absence.
     *
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        return PlannedFile::whole($project->root, self::PATH, $this->ci ? $this->content($project) : null);
    }

    /**
     * The workflow for the project.
     *
     * @author michtio
     */
    public function content(Project $project): string
    {
        $database = $this->database($project);
        $lines = [
            '# Written by claude-skills:setup because .ai/skills-profile.json sets laravel.ci to true.',
            '# Runs the one gate command, composer test, as it runs locally. The setup refreshes',
            '# this file and deletes it when ci goes back to false: edit it by hand only if you accept that.',
            'name: claude-skills gate',
            '',
            'on:',
            '  push:',
            '  pull_request:',
            '',
            'permissions:',
            '  contents: read',
            '',
            'concurrency:',
            '  group: claude-skills-gate-${{ github.ref }}',
            '  cancel-in-progress: true',
            '',
            'jobs:',
            '  gate:',
            '    runs-on: ubuntu-latest',
        ];

        if ($database !== null) {
            [$image, $port, $user, $password, $name] = $database;
            $kind = explode(':', $image)[0];
            $lines[] = '    services:';
            $lines[] = '      database:';
            $lines[] = '        image: '.$image;
            $lines[] = '        env:';

            if ($kind === 'postgres') {
                $lines[] = '          POSTGRES_USER: '.$user;
                $lines[] = '          POSTGRES_PASSWORD: '.$password;
                $lines[] = '          POSTGRES_DB: '.$name;
                $health = 'pg_isready -U '.$user;
            } elseif ($kind === 'mariadb') {
                $lines[] = '          MARIADB_ROOT_PASSWORD: '.$password;
                $lines[] = '          MARIADB_DATABASE: '.$name;
                $health = 'healthcheck.sh --connect --innodb_initialized';
            } else {
                $lines[] = '          MYSQL_ROOT_PASSWORD: '.$password;
                $lines[] = '          MYSQL_DATABASE: '.$name;
                $health = 'mysqladmin ping -h 127.0.0.1 -p'.$password;
            }

            $lines[] = '        ports:';
            $lines[] = '          - '.$port.':'.$port;
            $lines[] = '        options: >-';
            $lines[] = '          --health-cmd="'.$health.'"';
            $lines[] = '          --health-interval=5s';
            $lines[] = '          --health-timeout=5s';
            $lines[] = '          --health-retries=20';
            $lines[] = '    env:';
            $lines[] = '      DB_HOST: 127.0.0.1';
            $lines[] = '      DB_PORT: '.$port;
            $lines[] = '      DB_USERNAME: '.$user;
            $lines[] = '      DB_PASSWORD: '.$password;
        }

        array_push(
            $lines,
            '    steps:',
            '      - uses: actions/checkout@v7',
            '',
            '      - uses: shivammathur/setup-php@v2',
            '        with:',
            "          php-version: '".$this->phpVersion($project)."'",
            '          coverage: none',
            '',
            '      - name: Find the Composer cache directory',
            '        id: composer-cache',
            '        run: echo "dir=$(composer config cache-files-dir)" >> "$GITHUB_OUTPUT"',
            '',
            '      - uses: actions/cache@v6',
            '        with:',
            '          path: ${{ steps.composer-cache.outputs.dir }}',
            "          key: composer-\${{ runner.os }}-\${{ hashFiles('composer.json', 'composer.lock') }}",
            '          restore-keys: composer-${{ runner.os }}-',
            '',
            '      - name: Install dependencies',
            '        run: composer install --no-interaction --no-progress --prefer-dist',
            '',
            '      - name: Install gitleaks (the secret scan of composer test)',
            '        env:',
            '          GITLEAKS_VERSION: '.self::GITLEAKS_VERSION,
            '          GITLEAKS_SHA256: '.self::GITLEAKS_SHA256,
            '        run: |',
            '          archive="$RUNNER_TEMP/gitleaks.tar.gz"',
            '          curl -sSfL -o "$archive" "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"',
            '          echo "${GITLEAKS_SHA256}  $archive" | sha256sum -c -',
            '          mkdir -p "$HOME/.local/bin"',
            '          tar -xzf "$archive" -C "$HOME/.local/bin" gitleaks',
            '          echo "$HOME/.local/bin" >> "$GITHUB_PATH"',
            '',
            '      - name: Set a throwaway application key',
            '        run: echo "APP_KEY=base64:$(openssl rand -base64 32)" >> "$GITHUB_ENV"',
            '',
            '      - name: Gate',
            '        run: composer test',
        );

        return implode("\n", $lines)."\n";
    }

    // Private Methods
    // =========================================================================

    /**
     * The PHP version for CI: config.platform.php, else the lowest X.Y of require.php, else the default.
     *
     * @author michtio
     */
    private function phpVersion(Project $project): string
    {
        $composer = $project->composerJson();
        $platform = is_array($composer['config'] ?? null) && is_array($composer['config']['platform'] ?? null)
            ? ($composer['config']['platform']['php'] ?? null)
            : null;

        if (is_string($platform) && preg_match('/^(\d+)\.(\d+)/', $platform, $m) === 1) {
            return $m[1].'.'.$m[2];
        }

        $constraint = is_array($composer['require'] ?? null) ? ($composer['require']['php'] ?? null) : null;

        if (! is_string($constraint) || preg_match_all('/(\d+)\.(\d+)/', $constraint, $matches, PREG_SET_ORDER) === 0) {
            return self::DEFAULT_PHP;
        }

        $versions = array_map(static fn (array $m): string => $m[1].'.'.$m[2], $matches);
        usort($versions, static fn (string $a, string $b): int => version_compare($a, $b));

        return $versions[0];
    }

    /**
     * The database service for an app on a server database: [image, port, user,
     * password, test database name], or null when the suite needs none.
     *
     * @return array{0: string, 1: int, 2: string, 3: string, 4: string}|null
     * @author michtio
     */
    private function database(Project $project): ?array
    {
        if ($project->usesMemoryDatabase()) {
            return null;
        }

        $type = match ($project->dbConnection()) {
            'mysql' => 'mysql',
            'mariadb' => 'mariadb',
            'pgsql' => 'postgres',
            default => null,
        };

        if ($type === null) {
            return null;
        }

        $version = null;
        $ddev = $this->ddevDatabase($project->root);

        if ($ddev !== null) {
            [$type, $version] = $ddev;
        }

        [$image, $defaultVersion, $port, $user, $password] = self::DATABASES[$type];

        return [$image.':'.($version ?? $defaultVersion), $port, $user, $password, $project->testDatabase()];
    }

    /**
     * The database type and version of `.ddev/config.yaml` (DDEV's default, MariaDB
     * 10.11, when the file sets none), or null without a DDEV config or for a type
     * the workflow has no image for.
     *
     * @return array{0: string, 1: string}|null
     * @author michtio
     */
    private function ddevDatabase(string $root): ?array
    {
        $file = $root.'/.ddev/config.yaml';

        if (! is_file($file)) {
            return null;
        }

        try {
            $config = Yaml::parse((string) file_get_contents($file));
        } catch (\Throwable) {
            return null;
        }

        $database = is_array($config) && is_array($config['database'] ?? null) ? $config['database'] : [];
        $type = is_string($database['type'] ?? null) ? $database['type'] : 'mariadb';
        $version = $database['version'] ?? null;
        $version = is_string($version) || is_int($version) || is_float($version) ? (string) $version : null;

        if (! isset(self::DATABASES[$type])) {
            return null;
        }

        if ($version === null || preg_match('/^[0-9][0-9.]*$/', $version) !== 1) {
            $version = isset($database['type']) ? self::DATABASES[$type][1] : '10.11';
        }

        return [$type, $version];
    }
}
