<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Closure;
use Symfony\Component\Process\Process;

/**
 * A planned `composer require` through the project's runner (`ddev composer ...`
 * on DDEV), checked again before it runs (the package must still be missing from
 * composer.json) and run with its output passed to the console.
 *
 * @author michtio
 */
final class ComposerRequire
{
    // Public Methods
    // =========================================================================

    /**
     * The action that requires a package, as a dev dependency when asked.
     *
     * @author michtio
     */
    public static function action(Project $project, string $package, bool $dev = false): PlannedAction
    {
        $command = [...($project->usesDdev() ? ['ddev', 'composer'] : ['composer']), 'require', ...($dev ? ['--dev'] : []), $package];

        return new PlannedAction(
            implode(' ', $command),
            // composer.json is read again: it may have changed since the plan was shown.
            static fn (): bool => ! Project::detect($project->root)->requires($package),
            static function (Closure $output) use ($command, $project): bool {
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
        );
    }
}
