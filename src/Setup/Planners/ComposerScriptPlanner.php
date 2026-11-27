<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\JsonFile;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use stdClass;

/**
 * Sets composer.json `scripts.test` to the one gate command: `composer test` runs
 * the same steps locally and in CI.
 *
 * Steps: for an app first `@php artisan config:clear --ansi` (a cached config
 * would override the forced test pins); then, each only when its package is
 * required, `pint --test` (laravel/pint),
 * `phpstan analyse --no-progress` (phpstan/phpstan or larastan/larastan), `pest`
 * (pestphp/pest; otherwise `@php artisan test` for an app or
 * `@php vendor/bin/testbench package:test` for a package), and always last
 * `bash .githooks/gitleaks-check`.
 *
 * Owned: only `scripts.test`. Every other key, and the order of keys, is kept;
 * an existing different `scripts.test` the setup did not write is a hand edit.
 *
 * @author michtio
 */
final class ComposerScriptPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the Composer manifest.
     */
    public const PATH = 'composer.json';

    // Public Methods
    // =========================================================================

    /**
     * Plan composer.json with the gate script.
     *
     * @throws SetupException When composer.json is not a JSON object.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        $current = PlannedFile::read($project->root, self::PATH);

        if ($current === null) {
            return new PlannedFile(self::PATH, null, null, null, null);
        }

        $composer = JsonFile::decode(self::PATH, $current);
        $steps = $this->steps($project);
        $scripts = $composer->scripts ?? null;
        $existing = $scripts instanceof stdClass && property_exists($scripts, 'test') ? JsonFile::toArray($scripts->test) : null;

        if ($existing === $steps) {
            $desired = $current;
        } else {
            if (! $scripts instanceof stdClass) {
                $scripts = new stdClass();
            }

            $scripts->test = $steps;
            $composer->scripts = $scripts;
            $desired = JsonFile::encode($composer, $current);
        }

        return new PlannedFile(
            self::PATH,
            $current,
            $desired,
            $existing === null ? null : JsonFile::fingerprint($existing),
            JsonFile::fingerprint($steps),
        );
    }

    /**
     * The gate steps for the project, in order.
     *
     * @return list<string>
     * @author michtio
     */
    public function steps(Project $project): array
    {
        // A cached config would make PHPUnit's forced pins useless, so an app clears it first.
        $steps = $project->isPackage() ? [] : ['@php artisan config:clear --ansi'];

        if ($project->requires('laravel/pint')) {
            $steps[] = 'pint --test';
        }

        if ($project->requires('phpstan/phpstan') || $project->requires('larastan/larastan')) {
            $steps[] = 'phpstan analyse --no-progress';
        }

        if ($project->requires('pestphp/pest')) {
            $steps[] = 'pest';
        } else {
            $steps[] = $project->isPackage() ? '@php vendor/bin/testbench package:test' : '@php artisan test';
        }

        $steps[] = 'bash .githooks/gitleaks-check';

        return $steps;
    }
}
