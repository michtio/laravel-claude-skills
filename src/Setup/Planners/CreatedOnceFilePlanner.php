<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Closure;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * A file the setup creates when it is missing and never touches once it exists,
 * whoever wrote it: `CLAUDE.md` (so Boost writes its guidelines there, not into
 * AGENTS.md), `boost.json` (so `boost:install -n` installs this pack's skills for
 * Claude Code) and a package's `tests/Pest.php` (so a fresh package has a suite).
 *
 * The created file is shown in the plan like any other, but it is not recorded in
 * the state file: what Boost or the person writes into it later is never an edit
 * the setup reports or replaces, and a rerun says "No changes".
 *
 * @author michtio
 */
final class CreatedOnceFilePlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * The Pest file of a Testbench package.
     */
    public const PEST = 'tests/Pest.php';

    /**
     * The file Claude Code reads and Boost writes its guidelines into.
     */
    public const CLAUDE_MD = 'CLAUDE.md';

    /**
     * Boost's own config, seeded for a non-interactive boost:install.
     */
    public const BOOST_JSON = 'boost.json';

    // Public Methods
    // =========================================================================

    /**
     * Describe one created-once file.
     *
     * @param string $path Path relative to the project root.
     * @param string $content The content it is created with.
     * @param Closure(Project): bool $condition Which projects get the file.
     * @author michtio
     */
    public function __construct(
        private readonly string $path,
        private readonly string $content,
        private readonly Closure $condition,
    ) {
    }

    /**
     * The planner for a package's tests/Pest.php: Testbench's test case for every test.
     * Only for a package on Pest (`pestphp/pest` required) whose tests pick no base
     * case yet: no `tests/TestCase.php` and no test file that calls `uses(`.
     *
     * @author michtio
     */
    public static function pest(): self
    {
        return new self(
            self::PEST,
            implode("\n", [
                '<?php',
                '',
                'declare(strict_types=1);',
                '',
                'use Orchestra\Testbench\TestCase;',
                '',
                'pest()->extend(TestCase::class)->in(__DIR__);',
            ])."\n",
            static fn (Project $project): bool => $project->isPackage()
                && $project->requires('pestphp/pest')
                && ! file_exists($project->root.'/tests/TestCase.php')
                && ! self::callsUses($project->root.'/tests'),
        );
    }

    /**
     * Whether a PHP file under the folder (subfolders included, symlinks not
     * followed) calls Pest's `uses(`, which picks the base case itself.
     *
     * @author michtio
     */
    public static function callsUses(string $directory): bool
    {
        if (! is_dir($directory) || is_link($directory)) {
            return false;
        }

        $files = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($directory, \FilesystemIterator::SKIP_DOTS));

        foreach ($files as $file) {
            if ($file instanceof \SplFileInfo && $file->isFile() && ! $file->isLink() && str_ends_with($file->getFilename(), '.php')
                && preg_match('/(?<![\w>:$])uses\s*\(/', (string) file_get_contents($file->getPathname())) === 1) {
                return true;
            }
        }

        return false;
    }

    /**
     * The planner for the boost.json seed Boost reads on a non-interactive
     * `boost:install -n`: Claude Code as the agent, this pack among the
     * third-party packages, the Laravel Cloud skill off. Created only when the
     * project has no boost.json; an existing one is never touched.
     *
     * @author michtio
     */
    public static function boostJson(): self
    {
        return new self(
            self::BOOST_JSON,
            json_encode(
                ['agents' => ['claude_code'], 'packages' => ['michtio/laravel-claude-skills'], 'cloud' => false],
                JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES,
            )."\n",
            static fn (Project $project): bool => true,
        );
    }

    /**
     * The planner for an empty CLAUDE.md, for a project whose agents include Claude
     * Code: boost.json is missing, or its `agents` lists `claude_code` (or is not a list).
     *
     * @author michtio
     */
    public static function claudeMd(): self
    {
        return new self(self::CLAUDE_MD, '', static function (Project $project): bool {
            $file = $project->root.'/boost.json';
            $boost = is_file($file) ? json_decode((string) file_get_contents($file), true) : null;
            $agents = is_array($boost) ? ($boost['agents'] ?? null) : null;

            return ! is_array($agents) || in_array('claude_code', $agents, true);
        });
    }

    /**
     * Plan the file when it is missing and wanted; otherwise nothing.
     *
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        return new PlannedFile($this->path, null, $this->creates($project) ? $this->content : null, null, null);
    }

    /**
     * Whether this run creates the file: it is wanted and does not exist.
     *
     * @author michtio
     */
    public function creates(Project $project): bool
    {
        return ! file_exists($project->root.'/'.$this->path) && ! is_link($project->root.'/'.$this->path) && ($this->condition)($project);
    }
}
