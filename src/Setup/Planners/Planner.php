<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;

/**
 * One concern of the setup: says what one project file should contain.
 *
 * Planners only read; the setup command compares their plans with the recorded
 * state, shows the diff, asks, and writes.
 *
 * @author michtio
 */
interface Planner
{
    // Public Methods
    // =========================================================================

    /**
     * Plan the file this planner owns for the given project.
     *
     * @throws SetupException When the project is in a state the setup must not touch.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile;
}
