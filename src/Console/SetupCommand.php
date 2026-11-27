<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Console;

use Illuminate\Console\Command;
use Michtio\LaravelClaudeSkills\Setup\FileChange;
use Michtio\LaravelClaudeSkills\Setup\Planners\CoreOverridePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\McpPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\Planner;
use Michtio\LaravelClaudeSkills\Setup\Planners\RunnerGuidelinePlanner;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Michtio\LaravelClaudeSkills\Setup\SetupPlan;
use Michtio\LaravelClaudeSkills\Setup\UnifiedDiff;
use Symfony\Component\Console\Formatter\OutputFormatter;

/**
 * Brings a Laravel application or Testbench package with Boost to the baseline:
 * plan, then confirm, then apply.
 *
 * It detects the project kind (app, or package: orchestra/testbench plus a
 * workbench/ directory) and the runner (DDEV when .ddev/ exists, else host),
 * prints every file it would create, change or delete as a unified diff, marks
 * files that differ from what it wrote last as "edited by hand", and asks once.
 * A second run on an unchanged project reports "No changes". It never edits
 * CLAUDE.md or any other file Boost generates; it corrects Boost's host-command
 * guidance through Boost's own paths (.ai/guidelines/, .mcp.json).
 *
 * Exit codes: 0 when done, declined or nothing to do; 1 with --check when
 * something would change, and when the project is in a state it refuses to touch.
 *
 * @author michtio
 */
final class SetupCommand extends Command
{
    // Properties
    // =========================================================================

    /**
     * The console command signature.
     *
     * @var string
     */
    protected $signature = 'claude-skills:setup
        {--check : Exit 1 when anything would change; never asks, never writes}
        {--yes : Apply without asking}
        {--path= : Project root (default: the application base path, or the package root under Testbench)}';

    /**
     * The console command description.
     *
     * @var string
     */
    protected $description = 'Set up Claude Code for this project on top of Laravel Boost (runner, MCP, guidelines)';

    // Public Methods
    // =========================================================================

    /**
     * Plan, show, confirm and apply.
     *
     * @author michtio
     */
    public function handle(): int
    {
        $root = $this->root();

        if ($root === null) {
            $path = $this->option('path');
            $this->error('The project root does not exist: '.(is_string($path) ? $path : ''));

            return self::FAILURE;
        }

        $project = Project::detect($root);
        $this->line('Detected: '.$project->kind->value);
        $this->line('Runner: '.$project->runner->value);

        try {
            $plan = SetupPlan::build($project, $this->planners());
        } catch (SetupException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }

        foreach ($plan->notices as $notice) {
            $this->warn($notice);
        }

        if ($plan->isEmpty()) {
            $this->info('No changes.');

            return self::SUCCESS;
        }

        foreach ($plan->changes as $change) {
            $this->show($change);
        }

        $count = count($plan->changes);
        $summary = $count === 1 ? '1 file' : $count.' files';

        if ($this->option('check')) {
            $this->line($summary.' would change. Run claude-skills:setup to apply.');

            return self::FAILURE;
        }

        if (! $this->option('yes') && ! $this->confirm('Apply these changes?', false)) {
            $this->line($this->input->isInteractive() ? 'Nothing written.' : 'Nothing written. Pass --yes to apply without a prompt.');

            return self::SUCCESS;
        }

        foreach ($plan->changes as $change) {
            if (! $this->apply($root, $change)) {
                $this->error('Could not write '.$change->path.'; the files listed above it were applied.');

                return self::FAILURE;
            }
        }

        $this->info('Applied: '.$summary.'.');

        return self::SUCCESS;
    }

    // Private Methods
    // =========================================================================

    /**
     * The planners, one per concern, in the order their changes are shown.
     *
     * @return list<Planner>
     * @author michtio
     */
    private function planners(): array
    {
        return [
            new McpPlanner(),
            new RunnerGuidelinePlanner(),
            new CoreOverridePlanner(),
        ];
    }

    /**
     * The project root: --path, else the package root under the Testbench CLI, else base_path().
     *
     * @author michtio
     */
    private function root(): ?string
    {
        $path = $this->option('path');

        if (! is_string($path) || $path === '') {
            $working = defined('TESTBENCH_WORKING_PATH') ? constant('TESTBENCH_WORKING_PATH') : null;
            $path = is_string($working) ? $working : base_path();
        }

        $real = realpath($path);

        return $real !== false && is_dir($real) ? $real : null;
    }

    /**
     * Print one change: the hand-edit warning and notes, then its diff.
     *
     * @author michtio
     */
    private function show(FileChange $change): void
    {
        $this->newLine();

        if ($change->handEdited) {
            $this->warn('edited by hand: '.$change->path);
        }

        foreach ($change->notes as $note) {
            $this->line($change->path.': '.$note);
        }

        foreach (UnifiedDiff::render($change->path, $change->before, $change->after) as $line) {
            $this->output->writeln($this->styled($line));
        }
    }

    /**
     * Escape a diff line for the console and colour it by its first character.
     *
     * @author michtio
     */
    private function styled(string $line): string
    {
        $escaped = OutputFormatter::escape($line);

        return match (true) {
            str_starts_with($line, '+++'), str_starts_with($line, '---') => '<options=bold>'.$escaped.'</>',
            str_starts_with($line, '@@') => '<fg=cyan>'.$escaped.'</>',
            str_starts_with($line, '+') => '<fg=green>'.$escaped.'</>',
            str_starts_with($line, '-') => '<fg=red>'.$escaped.'</>',
            default => $escaped,
        };
    }

    /**
     * Write or delete one file; false when the filesystem refused.
     *
     * @author michtio
     */
    private function apply(string $root, FileChange $change): bool
    {
        $file = $root.'/'.$change->path;

        if ($change->after === null) {
            if (is_file($file) && ! unlink($file)) {
                return false;
            }

            $this->removeEmptyParents($root, dirname($change->path));

            $this->line('Deleted '.$change->path);

            return true;
        }

        $directory = dirname($file);

        if (! is_dir($directory) && ! mkdir($directory, 0777, true) && ! is_dir($directory)) {
            return false;
        }

        if (file_put_contents($file, $change->after) === false) {
            return false;
        }

        $this->line(($change->before === null ? 'Created ' : 'Updated ').$change->path);

        return true;
    }

    /**
     * Remove directories left empty by a deletion, up to (not including) .ai/guidelines/.
     *
     * @author michtio
     */
    private function removeEmptyParents(string $root, string $relative): void
    {
        while (! in_array($relative, ['.', '', '.ai', '.ai/guidelines'], true)) {
            $directory = $root.'/'.$relative;

            if (! is_dir($directory) || (new \FilesystemIterator($directory))->valid()) {
                return;
            }

            rmdir($directory);
            $relative = dirname($relative);
        }
    }
}
