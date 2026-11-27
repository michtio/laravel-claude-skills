<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\ComposerRequire;
use Michtio\LaravelClaudeSkills\Setup\PlannedAction;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;

/**
 * Plans `composer require --dev larastan/larastan` through the runner when the
 * setup writes phpstan.neon (which includes Larastan's extension) and the project
 * does not require Larastan yet, for an app and for a Testbench package alike.
 * Never planned when it is required; never removed.
 *
 * @author michtio
 */
final class LarastanPlanner implements ActionPlanner
{
    // Public Methods
    // =========================================================================

    /**
     * Take the planner that decides whether phpstan.neon is written.
     *
     * @author michtio
     */
    public function __construct(private readonly PhpstanPlanner $phpstan)
    {
    }

    /**
     * Plan the install, or nothing.
     *
     * @return array{0: PlannedAction|null, 1: list<string>}
     * @throws SetupException When the state file holds a tampered step.
     * @author michtio
     */
    public function plan(Project $project): array
    {
        if ($project->requires(PhpstanPlanner::LARASTAN) || ! $this->phpstan->writes($project)) {
            return [null, []];
        }

        return [ComposerRequire::action($project, PhpstanPlanner::LARASTAN, true), []];
    }
}
