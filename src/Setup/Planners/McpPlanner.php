<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Michtio\LaravelClaudeSkills\Setup\SetupState;
use stdClass;

/**
 * Points the laravel-boost entry in .mcp.json at the project's runner.
 *
 * Only that entry is owned: other servers and keys stay as they are. Boost's own
 * `boost:install --mcp` writes `php artisan boost:mcp` there, which does not start
 * inside DDEV and does not exist in a Testbench package; the entry written here
 * runs `boost:mcp` through `ddev exec php` and through `vendor/bin/testbench` for
 * packages. Only `command` and `args` of that entry are owned (and fingerprinted);
 * other keys such as `env` are kept. JSON is written pretty printed with slashes
 * and Unicode unescaped, in the file's existing indentation, and the file is left
 * byte for byte as it is when command and args already match.
 *
 * An exact Boost default entry (only command and args) gets a "reset by
 * boost:install" note; any other entry that differs from what the setup recorded,
 * or a custom entry the setup has no record of, is reported as edited by hand.
 *
 * @author michtio
 */
final class McpPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the MCP configuration Claude Code reads.
     */
    public const PATH = '.mcp.json';

    /**
     * Name of Boost's MCP server entry.
     */
    public const SERVER = 'laravel-boost';

    // Public Methods
    // =========================================================================

    /**
     * Plan .mcp.json with the laravel-boost entry for the project's runner and kind.
     *
     * @throws SetupException When .mcp.json exists but is not a JSON object with an mcpServers object.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        $current = PlannedFile::read($project->root, self::PATH);
        $config = $this->decode($current);
        $wanted = $project->boostMcpServer();
        $entry = $config->mcpServers->{self::SERVER} ?? null;
        $existing = $entry === null ? null : json_decode((string) json_encode($entry), true);

        if ($existing !== null && ! is_array($existing)) {
            $existing = ['value' => $existing];
        }

        $owned = $existing === null ? null : ['command' => $existing['command'] ?? null, 'args' => $existing['args'] ?? null];

        if ($owned == $wanted && $current !== null) {
            $desired = $current;
        } else {
            // Only command and args are owned: every other key of the entry stays.
            if (! $entry instanceof stdClass) {
                $entry = new stdClass();
            }

            $entry->command = $wanted['command'];
            $entry->args = $wanted['args'];
            $config->mcpServers->{self::SERVER} = $entry;
            $desired = $this->encode($config, $this->indentation($current));
        }

        return new PlannedFile(
            self::PATH,
            $current,
            $desired,
            $owned === null ? null : $this->fingerprint($owned),
            $this->fingerprint($wanted),
            true,
            $existing !== null && $owned != $wanted && $this->isBoostDefault($existing)
                ? 'boost:install reset the laravel-boost entry to its own default; setting it back to the runner'
                : null,
        );
    }

    // Private Methods
    // =========================================================================

    /**
     * Decode .mcp.json into objects (so empty objects survive a rewrite), or start an empty one.
     *
     * @throws SetupException When the file is not a JSON object with an mcpServers object.
     * @author michtio
     */
    private function decode(?string $content): stdClass
    {
        if ($content === null || trim($content) === '') {
            $config = new stdClass();
            $config->mcpServers = new stdClass();

            return $config;
        }

        $config = json_decode($content);

        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new SetupException(self::PATH.' is not valid JSON ('.json_last_error_msg().'). Fix it by hand and run the setup again; nothing was written.');
        }

        if (! $config instanceof stdClass) {
            throw new SetupException(self::PATH.' is not a JSON object. Fix it by hand and run the setup again; nothing was written.');
        }

        if (! isset($config->mcpServers)) {
            $config->mcpServers = new stdClass();
        }

        if (! $config->mcpServers instanceof stdClass) {
            throw new SetupException(self::PATH.' has an mcpServers value that is not an object. Fix it by hand and run the setup again; nothing was written.');
        }

        return $config;
    }

    /**
     * Fingerprint of a server entry.
     *
     * @param array<mixed> $entry
     * @author michtio
     */
    private function fingerprint(array $entry): string
    {
        return SetupState::fingerprint((string) json_encode($entry, JSON_UNESCAPED_SLASHES));
    }

    /**
     * Whether an entry is exactly one Boost's own installer writes: only command and
     * args, php (or an absolute php binary), WSL or Sail, starting `artisan boost:mcp`.
     *
     * @param array<mixed> $entry
     * @author michtio
     */
    private function isBoostDefault(array $entry): bool
    {
        $keys = array_keys($entry);
        sort($keys);

        if ($keys !== ['args', 'command']) {
            return false;
        }

        $command = is_string($entry['command'] ?? null) ? basename(str_replace('\\', '/', $entry['command'])) : '';
        $args = is_array($entry['args'] ?? null) ? array_values($entry['args']) : [];
        $count = count($args);

        if ($count < 2 || $args[$count - 1] !== 'boost:mcp' || ! is_string($args[$count - 2])) {
            return false;
        }

        $runsArtisan = basename(str_replace('\\', '/', $args[$count - 2])) === 'artisan';

        return $runsArtisan && (str_starts_with($command, 'php') || $command === 'wsl.exe' || $command === 'sail');
    }

    /**
     * The indentation unit of an existing JSON file (the first indented line), four spaces by default.
     *
     * @author michtio
     */
    private function indentation(?string $content): string
    {
        if ($content !== null && preg_match('/^([ \t]+)"/m', str_replace("\r\n", "\n", $content), $match) === 1) {
            return $match[1];
        }

        return '    ';
    }

    /**
     * Encode the configuration as Boost does (pretty, slashes and Unicode unescaped) with the given indentation.
     *
     * @author michtio
     */
    private function encode(stdClass $config, string $indent): string
    {
        $json = (string) json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

        if ($indent !== '    ') {
            $json = (string) preg_replace_callback(
                '/^(?: {4})+/m',
                static fn (array $match): string => str_repeat($indent, intdiv(strlen($match[0]), 4)),
                $json,
            );
        }

        return $json."\n";
    }
}
