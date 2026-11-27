<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Closure;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * A file the setup owns entirely, with fixed content (hook scripts, the gitleaks
 * config, the .gitignore files of a package skeleton), written only for the
 * projects the condition accepts.
 *
 * @author michtio
 */
final class StaticFilePlanner implements Planner
{
    // Public Methods
    // =========================================================================

    /**
     * Describe one owned file.
     *
     * @param string $path Path relative to the project root.
     * @param string $content The file's content.
     * @param bool $executable Whether the file must carry the executable bits.
     * @param (Closure(Project): bool)|null $condition Which projects get the file; all when null.
     * @author michtio
     */
    public function __construct(
        private readonly string $path,
        private readonly string $content,
        private readonly bool $executable = false,
        private readonly ?Closure $condition = null,
    ) {
    }

    /**
     * Plan the file, or its absence for a project the condition rejects.
     *
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        $wanted = $this->condition === null || ($this->condition)($project);

        return PlannedFile::whole($project->root, $this->path, $wanted ? $this->content : null, $this->executable);
    }
}
