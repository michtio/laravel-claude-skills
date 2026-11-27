<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Michtio\LaravelClaudeSkills\Setup\SetupState;

/**
 * Writes `phpstan.neon` at the profile's `laravel.phpstan_level` (default 8), with
 * Larastan's extension and this pack's rules included.
 *
 * Managed only for a project on Larastan (`larastan/larastan` in `require` or
 * `require-dev`) or whose profile sets `laravel.phpstan_level` itself; any other
 * project gets nothing, so the pack stays unopinionated about PHPStan.
 *
 * Paths: for an app, those of app, config, database and routes that exist, in that
 * order; when none does, src if it exists, else app. For a Testbench package, src.
 *
 * With phpstan/extension-installer required, the file has no includes: the
 * installer already includes Larastan's and this pack's extensions, and a second
 * include makes PHPStan fail ("included multiple times").
 *
 * An existing PHPStan config the setup did not write (`phpstan.neon`,
 * `phpstan.neon.dist` or `phpstan.dist.neon`) is never changed: notice() names it
 * as left alone, and a `phpstan.neon` the setup wrote earlier is removed (when
 * still its own output) so it cannot shadow that config. The written file is owned
 * like every setup file, so a level change plans only that file.
 *
 * @author michtio
 */
final class PhpstanPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the config the setup writes.
     */
    public const PATH = 'phpstan.neon';

    /**
     * Every file name PHPStan reads its config from by default.
     */
    public const CONFIG_FILES = ['phpstan.neon', 'phpstan.neon.dist', 'phpstan.dist.neon'];

    /**
     * The Larastan package.
     */
    public const LARASTAN = 'larastan/larastan';

    /**
     * The installer that includes PHPStan extensions on its own.
     */
    public const EXTENSION_INSTALLER = 'phpstan/extension-installer';

    /**
     * The includes, in order: Larastan's extension, then this pack's rules.
     */
    public const INCLUDES = [
        'vendor/larastan/larastan/extension.neon',
        'vendor/michtio/laravel-claude-skills/extension.neon',
    ];

    /**
     * The app directories analysed when they exist, in order.
     */
    public const APP_PATHS = ['app', 'config', 'database', 'routes'];

    // Public Methods
    // =========================================================================

    /**
     * Take the level and whether the profile sets it itself.
     *
     * @author michtio
     */
    public function __construct(
        private readonly int $level,
        private readonly bool $levelInProfile,
    ) {
    }

    /**
     * Plan phpstan.neon, or its absence.
     *
     * @throws SetupException When the state file holds a tampered step.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        return PlannedFile::whole(
            $project->root,
            self::PATH,
            $this->writes($project) ? $this->content($project) : null,
            replaceNote: self::PATH.': applying replaces your changes with level '.$this->level,
        );
    }

    /**
     * Whether the setup writes phpstan.neon for this project: it manages PHPStan
     * here and no config of the project's own exists.
     *
     * @throws SetupException When the state file holds a tampered step.
     * @author michtio
     */
    public function writes(Project $project): bool
    {
        return $this->manages($project) && $this->foreignConfig($project) === null;
    }

    /**
     * The line saying an existing config is left alone, or null.
     *
     * @throws SetupException When the state file holds a tampered step.
     * @author michtio
     */
    public function notice(Project $project): ?string
    {
        if (! $this->manages($project)) {
            return null;
        }

        $file = $this->foreignConfig($project);

        return $file === null ? null : 'Left alone: '.$file.' (laravel.phpstan_level is not applied to an existing PHPStan config)';
    }

    /**
     * The config for the project.
     *
     * @author michtio
     */
    public function content(Project $project): string
    {
        $lines = [
            '# Written by claude-skills:setup at laravel.phpstan_level from .ai/skills-profile.json (default 8).',
            '# The setup refreshes this file when the level changes: edit it by hand only if you accept that.',
        ];

        // phpstan/extension-installer includes both extensions itself; a second include makes PHPStan fail.
        if (! $project->requires(self::EXTENSION_INSTALLER)) {
            $lines[] = 'includes:';

            foreach (self::INCLUDES as $include) {
                $lines[] = '    - '.$include;
            }

            $lines[] = '';
        }

        array_push($lines, 'parameters:', '    level: '.$this->level, '    paths:');

        foreach ($this->paths($project) as $path) {
            $lines[] = '        - '.$path;
        }

        return implode("\n", $lines)."\n";
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether the setup manages PHPStan for this project.
     *
     * @author michtio
     */
    private function manages(Project $project): bool
    {
        return $this->levelInProfile || $project->requires(self::LARASTAN);
    }

    /**
     * The first PHPStan config the project has that the setup did not write, or null.
     *
     * @throws SetupException When the state file holds a tampered step.
     * @author michtio
     */
    private function foreignConfig(Project $project): ?string
    {
        $state = SetupState::load($project->root);

        foreach (self::CONFIG_FILES as $file) {
            if (! file_exists($project->root.'/'.$file)) {
                continue;
            }

            if ($file === self::PATH && $state->recorded(self::PATH) !== null) {
                continue;
            }

            return $file;
        }

        return null;
    }

    /**
     * The analysed paths.
     *
     * @return list<string>
     * @author michtio
     */
    private function paths(Project $project): array
    {
        if ($project->isPackage()) {
            return ['src'];
        }

        $paths = array_values(array_filter(self::APP_PATHS, static fn (string $path): bool => is_dir($project->root.'/'.$path)));

        if ($paths !== []) {
            return $paths;
        }

        return is_dir($project->root.'/src') ? ['src'] : ['app'];
    }
}
