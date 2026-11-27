<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;

/**
 * Writes `.ai/guidelines/claude-skills-runner.md`, a custom Boost guideline that
 * maps the host command forms other guidelines and skills use to the project's runner.
 *
 * Boost merges every file under `.ai/guidelines/` into the agent guidelines on
 * `boost:install` and `boost:update`, so the mapping survives a regenerated
 * CLAUDE.md without the setup touching CLAUDE.md. A host application needs no
 * mapping (Boost's host forms are right there), so none is written for it. A
 * Testbench package gets one on the host too: it has no artisan file. For a
 * package it also says where package classes go (`src/`, the composer namespace),
 * that `make:` generators write into the skeleton, and to test with Pest. On DDEV
 * it names Boost's `tinker` MCP tool first and gives the raw tinker form
 * (Project::rawArtisan()), which `ddev exec` does not expand a `$` in.
 *
 * @author michtio
 */
final class RunnerGuidelinePlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the runner guideline.
     */
    public const PATH = '.ai/guidelines/claude-skills-runner.md';

    // Public Methods
    // =========================================================================

    /**
     * Plan the runner guideline, or its absence for a host application.
     *
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        return PlannedFile::whole($project->root, self::PATH, $this->content($project));
    }

    /**
     * The guideline for the project, or null when it needs none.
     *
     * @author michtio
     */
    public function content(Project $project): ?string
    {
        if (! $project->usesDdev() && ! $project->isPackage()) {
            return null;
        }

        $artisan = $project->artisan();
        $lines = [];

        if ($project->usesDdev()) {
            $lines[] = '# Command runner: DDEV';
            $lines[] = '';
            $lines[] = 'This project runs PHP, Composer and Node inside DDEV. Run every command through DDEV, never on the host. Other guidelines and skills show commands in their host form; run them in the DDEV form below instead.';

            if ($project->isPackage()) {
                $lines[] = '';
                $lines[] = 'It is a Laravel package developed with Orchestra Testbench, not an application.';
            }
        } else {
            $lines[] = '# Command runner: Testbench';
            $lines[] = '';
            $lines[] = 'This project is a Laravel package developed with Orchestra Testbench. Other guidelines and skills show commands in their application form; run them in the form below instead.';
        }

        $lines[] = '';

        if ($project->isPackage()) {
            $namespace = $this->namespace($project);
            $lines[] = '- Artisan: there is no artisan file in a package; Testbench boots the application. Instead of `php artisan <command>`, run `'.$artisan.' <command>`, for example `'.$artisan.' route:list` or `'.$artisan.' list`.';
            $lines[] = '- Package classes: they live under `src/`'.($namespace === null ? ', in the namespace composer.json autoloads from it' : ' in the `'.$namespace.'` namespace (composer.json autoload)').'. Create them there by hand.';
            $lines[] = '- Generators: `make:` commands write into the Testbench skeleton (with `laravel: ./` in testbench.yaml, under the package root\'s app/ and database/ paths), never into `src/`; move or rewrite what they create.';
            $lines[] = '- Tests: instead of `php artisan test`, run `'.$project->vendorBin().'pest`, for example `'.$project->vendorBin().'pest --filter=Name`.';
        } else {
            $lines[] = '- Artisan: instead of `php artisan <command>`, run `'.$artisan.' <command>`, for example `'.$artisan.' route:list`, `'.$artisan.' make:model Post` or `'.$artisan.' test --compact`.';
        }

        if ($project->usesDdev()) {
            $lines[] = '- Tinker: prefer Boost\'s `tinker` MCP tool when it is enabled; it needs no shell quoting.';
            $lines[] = '- Tinker on the command line: `'.$project->rawArtisan()." tinker --execute 'Your::code();'`, with single quotes around the code."
                .($project->rawArtisan() === $artisan ? '' : ' Keep `--raw --`: plain `ddev exec` expands a `$` in the code.');
            $lines[] = '- Composer: instead of `composer <command>`, run `ddev composer <command>`, for example `ddev composer require vendor/package` or `ddev composer show --direct`.';
            $lines[] = '- Node: instead of `npm <command>`, run `ddev npm <command>`, for example `ddev npm run build` or `ddev npm run dev`; `npx` becomes `ddev npx` and `yarn` becomes `ddev yarn`.';
            $lines[] = '- Vendor binaries: instead of `vendor/bin/<tool>`, run `ddev exec vendor/bin/<tool>`, for example `ddev exec vendor/bin/pint --dirty` or `ddev exec vendor/bin/pest`.';
            $lines[] = '- PHP scripts: instead of `php <script>`, run `ddev exec php <script>`.';
            $lines[] = '- The Laravel Boost MCP server already runs inside DDEV (see `.mcp.json`); use its tools as usual.';
        } else {
            $lines[] = '- Composer, npm and vendor binaries run as usual from the package root.';
            $lines[] = '- The Laravel Boost MCP server runs through `php vendor/bin/testbench boost:mcp` (see `.mcp.json`); use its tools as usual.';
        }

        $lines[] = '';
        $lines[] = 'This file is written by `claude-skills:setup` and refreshed when the runner changes. Put project notes in another file under `.ai/guidelines/`.';

        return implode("\n", $lines)."\n";
    }

    // Private Methods
    // =========================================================================

    /**
     * The PSR-4 namespace composer.json autoloads from `src/`, or null when none does.
     *
     * @author michtio
     */
    private function namespace(Project $project): ?string
    {
        $autoload = $project->composerJson()['autoload']['psr-4'] ?? null;

        if (! is_array($autoload)) {
            return null;
        }

        foreach ($autoload as $namespace => $paths) {
            foreach ((array) $paths as $path) {
                if (is_string($namespace) && $namespace !== '' && is_string($path) && rtrim($path, '/') === 'src') {
                    return $namespace;
                }
            }
        }

        return null;
    }
}
