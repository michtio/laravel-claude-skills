<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedAction;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * One concern of the setup that is not a file write (a git setting, a Composer
 * install): plans at most one action, shown as its command line and confirmed
 * with the file changes, plus lines to show when it plans none.
 *
 * @author michtio
 */
interface ActionPlanner
{
    // Public Methods
    // =========================================================================

    /**
     * Plan the action for the project: the action (or null) and the lines to show.
     *
     * @return array{0: PlannedAction|null, 1: list<string>}
     * @author michtio
     */
    public function plan(Project $project): array;
}
