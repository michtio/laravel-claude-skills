<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * The project the setup runs against: its root, its kind and its runner, and the
 * command forms that follow from them.
 *
 * Detection rules:
 * - Runner: DDEV when `<root>/.ddev` is a directory, otherwise host.
 * - Kind: package when composer.json lists orchestra/testbench (require or
 *   require-dev) and `<root>/workbench` is a directory, otherwise app.
 *
 * A package has no artisan file; Testbench boots the application, so its
 * artisan commands run as `vendor/bin/testbench <command>`. DDEV only offers
 * `ddev artisan` for projects of type laravel, so other DDEV project types get
 * `ddev exec php artisan`.
 *
 * @author michtio
 */
final class Project
{
    // Constants
    // =========================================================================

    /**
     * The longest identifier PostgreSQL keeps (MySQL allows 64): the limit for the test database name.
     */
    public const MAX_IDENTIFIER = 63;

    /**
     * The suffix of the test database name.
     */
    public const TEST_SUFFIX = '_test';

    // Public Methods
    // =========================================================================

    /**
     * Create a project from already detected facts.
     *
     * @author michtio
     */
    public function __construct(
        public readonly string $root,
        public readonly Kind $kind,
        public readonly Runner $runner,
        public readonly bool $ddevLaravelType = false,
    ) {
    }

    /**
     * Detect kind and runner for the project at the given root.
     *
     * @author michtio
     */
    public static function detect(string $root): self
    {
        $root = rtrim($root, '/\\');
        $ddev = is_dir($root.'/.ddev');

        return new self(
            $root,
            self::hasTestbench($root) && is_dir($root.'/workbench') ? Kind::Package : Kind::App,
            $ddev ? Runner::Ddev : Runner::Host,
            $ddev && self::ddevType($root) === 'laravel',
        );
    }

    /**
     * Whether the runner is DDEV.
     *
     * @author michtio
     */
    public function usesDdev(): bool
    {
        return $this->runner === Runner::Ddev;
    }

    /**
     * Whether the project is a Testbench package.
     *
     * @author michtio
     */
    public function isPackage(): bool
    {
        return $this->kind === Kind::Package;
    }

    /**
     * The command that runs an artisan command in this project, without the command itself.
     *
     * @author michtio
     */
    public function artisan(): string
    {
        $php = $this->isPackage() ? 'php vendor/bin/testbench' : 'php artisan';

        if (! $this->usesDdev()) {
            return $php;
        }

        return $this->ddevLaravelType && ! $this->isPackage() ? 'ddev artisan' : 'ddev exec '.$php;
    }

    /**
     * The Composer command for this runner.
     *
     * @author michtio
     */
    public function composer(): string
    {
        return $this->usesDdev() ? 'ddev composer' : 'composer';
    }

    /**
     * The npm command for this runner.
     *
     * @author michtio
     */
    public function npm(): string
    {
        return $this->usesDdev() ? 'ddev npm' : 'npm';
    }

    /**
     * The prefix for a Composer vendor binary (vendor/bin/<tool>) for this runner.
     *
     * @author michtio
     */
    public function vendorBin(): string
    {
        return $this->usesDdev() ? 'ddev exec vendor/bin/' : 'vendor/bin/';
    }

    /**
     * The .mcp.json entry that starts Boost's MCP server through this project's runner.
     *
     * @return array{command: string, args: list<string>}
     * @author michtio
     */
    public function boostMcpServer(): array
    {
        $args = $this->isPackage() ? ['vendor/bin/testbench', 'boost:mcp'] : ['artisan', 'boost:mcp'];

        return $this->usesDdev()
            ? ['command' => 'ddev', 'args' => ['exec', 'php', ...$args]]
            : ['command' => 'php', 'args' => $args];
    }

    /**
     * The database connection the suite should use: DB_CONNECTION from .env, else
     * .env.example, else mysql for a DDEV app and sqlite otherwise.
     *
     * @author michtio
     */
    public function dbConnection(): string
    {
        $env = $this->envValues();

        if (isset($env['DB_CONNECTION']) && $env['DB_CONNECTION'] !== '') {
            return $env['DB_CONNECTION'];
        }

        return $this->usesDdev() && ! $this->isPackage() ? 'mysql' : 'sqlite';
    }

    /**
     * Whether the suite runs on in-memory sqlite (a package, or an sqlite connection).
     *
     * @author michtio
     */
    public function usesMemoryDatabase(): bool
    {
        return $this->isPackage() || $this->dbConnection() === 'sqlite';
    }

    /**
     * The test database name: <slug>_test, always a valid unquoted identifier for
     * MySQL and PostgreSQL (/^[a-z][a-z0-9_]*_test$/, at most 63 characters).
     *
     * A slug that starts with a digit, or is empty, gets the prefix "t_". A slug
     * too long for the limit is cut so the whole name, "_test" included, is 63
     * characters, with no trailing underscore left before "_test".
     *
     * @author michtio
     */
    public function testDatabase(): string
    {
        $base = $this->slug();

        if ($base === '' || ctype_digit($base[0])) {
            $base = 't_'.$base;
        }

        $base = rtrim(substr($base, 0, self::MAX_IDENTIFIER - strlen(self::TEST_SUFFIX)), '_');

        return $base.self::TEST_SUFFIX;
    }

    /**
     * The project slug: composer.json name after the slash (or the whole name), else
     * the directory name; lowercased, runs outside [a-z0-9] become one underscore,
     * underscores trimmed at both ends. Empty when nothing is left.
     *
     * @author michtio
     */
    public function slug(): string
    {
        $composer = $this->composerJson();
        $name = is_string($composer['name'] ?? null) && $composer['name'] !== '' ? $composer['name'] : basename($this->root);

        if (str_contains($name, '/')) {
            $name = substr($name, strrpos($name, '/') + 1);
        }

        return trim((string) preg_replace('/[^a-z0-9]+/', '_', strtolower($name)), '_');
    }

    /**
     * Live-provider flags: keys in .env.example or .env matching /^[A-Z][A-Z0-9_]*_LIVE(_MODE)?$/, sorted.
     *
     * @return list<string>
     * @author michtio
     */
    public function liveFlags(): array
    {
        $flags = [];

        foreach (['.env.example', '.env'] as $file) {
            foreach (array_keys($this->parseEnv($file)) as $key) {
                if (preg_match('/^[A-Z][A-Z0-9_]*_LIVE(_MODE)?$/', $key) === 1) {
                    $flags[$key] = true;
                }
            }
        }

        $flags = array_keys($flags);
        sort($flags);

        return $flags;
    }

    /**
     * composer.json decoded to arrays, or an empty array when absent or invalid.
     *
     * @return array<mixed>
     * @author michtio
     */
    public function composerJson(): array
    {
        $file = $this->root.'/composer.json';
        $data = is_file($file) ? json_decode((string) file_get_contents($file), true) : null;

        return is_array($data) ? $data : [];
    }

    /**
     * Whether composer.json lists a package in require or require-dev.
     *
     * @author michtio
     */
    public function requires(string $package): bool
    {
        $composer = $this->composerJson();

        foreach (['require', 'require-dev'] as $section) {
            if (is_array($composer[$section] ?? null) && array_key_exists($package, $composer[$section])) {
                return true;
            }
        }

        return false;
    }

    /**
     * Values from .env.example overlaid with .env (.env wins).
     *
     * @return array<string, string>
     * @author michtio
     */
    public function envValues(): array
    {
        return array_merge($this->parseEnv('.env.example'), $this->parseEnv('.env'));
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether composer.json requires orchestra/testbench in require or require-dev.
     *
     * @author michtio
     */
    private static function hasTestbench(string $root): bool
    {
        $file = $root.'/composer.json';

        if (! is_file($file)) {
            return false;
        }

        $composer = json_decode((string) file_get_contents($file), true);

        if (! is_array($composer)) {
            return false;
        }

        foreach (['require', 'require-dev'] as $section) {
            if (is_array($composer[$section] ?? null) && array_key_exists('orchestra/testbench', $composer[$section])) {
                return true;
            }
        }

        return false;
    }

    /**
     * The DDEV project type, read from .ddev/config.yaml and any config.*.yaml
     * override (later files win, as DDEV merges them), or null when unset.
     *
     * @author michtio
     */
    private static function ddevType(string $root): ?string
    {
        $files = glob($root.'/.ddev/config.*.yaml') ?: [];
        sort($files);
        array_unshift($files, $root.'/.ddev/config.yaml');

        $type = null;

        foreach ($files as $file) {
            if (is_file($file) && preg_match('/^type:\s*["\']?([A-Za-z0-9_-]+)/m', (string) file_get_contents($file), $match) === 1) {
                $type = $match[1];
            }
        }

        return $type;
    }

    /**
     * Parse one dotenv file into key => value (comments and blank lines skipped, quotes removed).
     *
     * @return array<string, string>
     * @author michtio
     */
    private function parseEnv(string $file): array
    {
        $path = $this->root.'/'.$file;

        if (! is_file($path)) {
            return [];
        }

        $values = [];

        foreach (preg_split('/\r\n|\n/', (string) file_get_contents($path)) ?: [] as $line) {
            $line = trim($line);

            if ($line === '' || str_starts_with($line, '#')) {
                continue;
            }

            if (preg_match('/^(?:export\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(.*)$/', $line, $match) !== 1) {
                continue;
            }

            $value = $match[2];

            if (strlen($value) >= 2 && ($value[0] === '"' || $value[0] === "'") && str_ends_with($value, $value[0])) {
                $value = substr($value, 1, -1);
            } else {
                $value = trim((string) preg_replace('/\s+#.*$/', '', $value));
            }

            $values[$match[1]] = $value;
        }

        return $values;
    }
}
