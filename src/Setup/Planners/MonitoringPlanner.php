<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedAction;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Symfony\Component\Process\Process;

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

        $command = $project->usesDdev() ? ['ddev', 'composer', 'require', $package] : ['composer', 'require', $package];

        return [
            new PlannedAction(
                implode(' ', $command),
                // composer.json is read again: it may have changed since the plan was shown.
                static fn (): bool => ! Project::detect($project->root)->requires($package),
                static function (\Closure $output) use ($command, $project): bool {
                    try {
                        $process = new Process($command, $project->root);
                        $process->setTimeout(null);
                        $process->run(static function (string $type, string $buffer) use ($output): void {
                            $output($buffer);
                        });
                    } catch (\Throwable $exception) {
                        $output($exception->getMessage()."\n");

                        return false;
                    }

                    return $process->isSuccessful();
                },
            ),
            [],
        ];
    }
}
