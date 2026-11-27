<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills;

use Illuminate\Support\ServiceProvider;
use Michtio\LaravelClaudeSkills\Console\SetupCommand;
use Michtio\LaravelClaudeSkills\Setup\DdevCliDatabaseSource;
use Michtio\LaravelClaudeSkills\Setup\DdevDatabaseSource;

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
     * Bind the reader of DDEV's database, which tests replace with their own.
     *
     * @author michtio
     */
    public function register(): void
    {
        $this->app->bindIf(DdevDatabaseSource::class, DdevCliDatabaseSource::class);
    }

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
