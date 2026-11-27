<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Closure;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * A file the setup creates when it is missing and never touches once it exists,
 * whoever wrote it: `CLAUDE.md` (so Boost writes its guidelines there, not into
 * AGENTS.md) and a package's `tests/Pest.php` (so a fresh package has a suite).
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
            static fn (Project $project): bool => $project->isPackage(),
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

    /**
     * The path this planner creates.
     *
     * @author michtio
     */
    public function path(): string
    {
        return $this->path;
    }
}
