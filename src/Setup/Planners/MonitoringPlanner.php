<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\ComposerRequire;
use Michtio\LaravelClaudeSkills\Setup\PlannedAction;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * Plans the Composer install of the monitoring package the profile names
 * (`laravel.monitoring`), through the project's runner:
 *
 * - `sentry`: `composer require sentry/sentry-laravel` (`ddev composer ...` on DDEV);
 * - `nightwatch`: `composer require laravel/nightwatch`;
 * - `none` (the default): nothing. A monitoring package already in composer.json
 *   is never removed.
 *
 * Nothing is planned when the package is already in `require` or `require-dev`,
 * or for a Testbench package (a library does not ship its own monitoring).
 *
 * @author michtio
 */
final class MonitoringPlanner implements ActionPlanner
{
    // Constants
    // =========================================================================

    /**
     * The Composer package for each monitoring choice.
     */
    public const PACKAGES = [
        'sentry' => 'sentry/sentry-laravel',
        'nightwatch' => 'laravel/nightwatch',
    ];

    // Public Methods
    // =========================================================================

    /**
     * Take the monitoring choice from the profile.
     *
     * @author michtio
     */
    public function __construct(private readonly string $monitoring)
    {
    }

    /**
     * Plan the install, or nothing.
     *
     * @return array{0: PlannedAction|null, 1: list<string>}
     * @author michtio
     */
    public function plan(Project $project): array
    {
        $package = self::PACKAGES[$this->monitoring] ?? null;

        if ($package === null || $project->isPackage() || $project->requires($package)) {
            return [null, []];
        }

        return [ComposerRequire::action($project, $package), []];
    }
}
