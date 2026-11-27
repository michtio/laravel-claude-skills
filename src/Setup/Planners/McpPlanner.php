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
 * packages. JSON is written the way Boost writes it (pretty printed, slashes
 * unescaped), and the file is left byte for byte as it is when the entry already
 * matches.
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
        $existing = isset($config->mcpServers->{self::SERVER})
            ? json_decode((string) json_encode($config->mcpServers->{self::SERVER}), true)
            : null;

        if ($existing !== null && ! is_array($existing)) {
            $existing = ['value' => $existing];
        }

        if ($existing == $wanted && $current !== null) {
            $desired = $current;
        } else {
            $config->mcpServers->{self::SERVER} = (object) $wanted;
            $desired = json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n";
        }

        return new PlannedFile(
            self::PATH,
            $current,
            $desired,
            $existing === null ? null : $this->fingerprint($existing),
            $this->fingerprint($wanted),
            false,
            $existing !== null && $existing != $wanted && $this->isBoostDefault($existing)
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
     * Whether an entry is one Boost's own installer writes: php (or an absolute
     * php binary), WSL or Sail, starting `artisan boost:mcp`.
     *
     * @param array<mixed> $entry
     * @author michtio
     */
    private function isBoostDefault(array $entry): bool
    {
        $command = is_string($entry['command'] ?? null) ? basename(str_replace('\\', '/', $entry['command'])) : '';
        $args = is_array($entry['args'] ?? null) ? array_values($entry['args']) : [];
        $count = count($args);

        if ($count < 2 || $args[$count - 1] !== 'boost:mcp' || ! is_string($args[$count - 2])) {
            return false;
        }

        $runsArtisan = basename(str_replace('\\', '/', $args[$count - 2])) === 'artisan';

        return $runsArtisan && (str_starts_with($command, 'php') || $command === 'wsl.exe' || $command === 'sail');
    }
}
