<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedAction;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Symfony\Component\Process\Process;

/**
 * Plans `git config core.hooksPath .githooks`, which turns on the commit-msg hook
 * the setup writes.
 *
 * - Not a git repository, or a directory inside another repository rather than
 *   its root: no action, and a line saying so (the setup never changes the
 *   configuration of a repository it is not the root of).
 * - core.hooksPath already `.githooks`: nothing to do.
 * - core.hooksPath set to anything else: never changed, and a line saying so.
 * - Unset, with an active hook in the repository's hooks directory (an executable
 *   file not ending in .sample): no action, since setting core.hooksPath would
 *   switch that hook off, and a line naming the hooks and the manual command.
 * - Unset otherwise: one planned action, confirmed with the file changes.
 *
 * @author michtio
 */
final class HooksPathPlanner
{
    // Constants
    // =========================================================================

    /**
     * The hooks directory the setup writes.
     */
    public const HOOKS = '.githooks';

    // Public Methods
    // =========================================================================

    /**
     * Plan the action for the project: the action (or null) and the lines to show.
     *
     * @return array{0: PlannedAction|null, 1: list<string>}
     * @author michtio
     */
    public function plan(Project $project): array
    {
        $root = $project->root;
        $top = $this->git($root, ['rev-parse', '--show-toplevel']);

        if ($top === null) {
            return [null, ['Not a git repository: skipping core.hooksPath']];
        }

        $realTop = realpath($top);

        if ($realTop === false || $realTop !== $root) {
            return [null, ['Not a git repository root (it is inside '.$top.'): skipping core.hooksPath']];
        }

        $value = $this->hooksPath($root);

        if ($value === self::HOOKS) {
            return [null, []];
        }

        if ($value !== null) {
            return [null, ['core.hooksPath is already set to '.$value.'; leaving it (the commit-msg hook in '.self::HOOKS.' is not active)']];
        }

        $existing = $this->existingHooks($root);

        if ($existing !== []) {
            return [null, [
                'Existing git hooks in .git/hooks ('.implode(', ', $existing).'): leaving core.hooksPath unset, since setting it would switch them off'
                .' (the commit-msg hook in '.self::HOOKS.' is not active). Move them to '.self::HOOKS.' and run `git config core.hooksPath '.self::HOOKS.'` to use both.',
            ]];
        }

        return [
            new PlannedAction(
                'git config core.hooksPath '.self::HOOKS,
                fn (): bool => $this->hooksPath($root) === null,
                fn (): bool => $this->git($root, ['config', 'core.hooksPath', self::HOOKS]) !== null,
            ),
            [],
        ];
    }

    // Private Methods
    // =========================================================================

    /**
     * Names of the active hooks in the repository's own hooks directory: executable
     * files not ending in .sample, sorted.
     *
     * @return list<string>
     * @author michtio
     */
    private function existingHooks(string $root): array
    {
        $directory = $this->git($root, ['rev-parse', '--git-path', 'hooks']);

        if ($directory === null || $directory === '') {
            return [];
        }

        if (! str_starts_with($directory, '/')) {
            $directory = $root.'/'.$directory;
        }

        if (! is_dir($directory)) {
            return [];
        }

        $hooks = [];

        foreach (new \FilesystemIterator($directory) as $file) {
            if ($file instanceof \SplFileInfo && $file->isFile() && $file->isExecutable() && ! str_ends_with($file->getFilename(), '.sample')) {
                $hooks[] = $file->getFilename();
            }
        }

        sort($hooks);

        return $hooks;
    }

    /**
     * The configured core.hooksPath, or null when unset.
     *
     * @author michtio
     */
    private function hooksPath(string $root): ?string
    {
        $value = $this->git($root, ['config', '--get', 'core.hooksPath']);

        return $value === null || $value === '' ? null : $value;
    }

    /**
     * Run git in the project root; trimmed output, or null when git failed or is missing.
     *
     * @param list<string> $arguments
     * @author michtio
     */
    private function git(string $root, array $arguments): ?string
    {
        try {
            $process = new Process(['git', '-C', $root, ...$arguments]);
            $process->setTimeout(30);
            $process->run();
        } catch (\Throwable) {
            return null;
        }

        return $process->isSuccessful() ? trim($process->getOutput()) : null;
    }
}
