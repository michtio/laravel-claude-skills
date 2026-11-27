<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills;

use Illuminate\Support\ServiceProvider;
use Michtio\LaravelClaudeSkills\Console\SetupCommand;

/**
 * Registers the package's console commands. Discovered through composer.json
 * extra.laravel.providers, in applications and under Testbench alike.
 *
 * @author michtio
 */
final class LaravelClaudeSkillsServiceProvider extends ServiceProvider
{
    // Public Methods
    // =========================================================================

    /**
     * Register the setup command for console runs.
     *
     * @author michtio
     */
    public function boot(): void
    {
        if ($this->app->runningInConsole()) {
            $this->commands([
                SetupCommand::class,
            ]);
        }
    }
}
