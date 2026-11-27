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
}
