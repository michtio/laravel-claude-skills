<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Console;

use Illuminate\Console\Command;
use Michtio\LaravelClaudeSkills\Setup\FileChange;
use Michtio\LaravelClaudeSkills\Setup\GitFiles;
use Michtio\LaravelClaudeSkills\Setup\PathGuard;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Planners\ComposerScriptPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\CoreOverridePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\DdevDatabasePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\HooksPathPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\McpPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\PhpunitPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\Planner;
use Michtio\LaravelClaudeSkills\Setup\Planners\RunnerGuidelinePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\StaticFilePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\TestbenchYamlPlanner;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Michtio\LaravelClaudeSkills\Setup\SetupPlan;
use Michtio\LaravelClaudeSkills\Setup\SetupState;
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
 * It also isolates the test suite (forced PHPUnit pins, a separate test database
 * with a DDEV post-start hook), sets the one gate command (composer test), writes
 * the commit-msg hook and the secret scan, plans `git config core.hooksPath`, and
 * makes a Testbench package its own skeleton so Boost reads the package's files.
 * Every change, the git setting included, is shown first and confirmed once.
 *
 * Exit codes: 0 when done, declined or nothing to do; 1 with --check when
 * something would change, and when the project is in a state it refuses to touch.
 *
 * @author michtio
 */
final class SetupCommand extends Command
{
    // Constants
    // =========================================================================

    /**
     * Every path the setup reads and writes as its own, checked for symlinks first.
     */
    private const OWNED_PATHS = [
        McpPlanner::PATH,
        RunnerGuidelinePlanner::PATH,
        CoreOverridePlanner::PATH,
        'phpunit.xml',
        'phpunit.xml.dist',
        ComposerScriptPlanner::PATH,
        DdevDatabasePlanner::PATH,
        GitFiles::COMMIT_MSG,
        GitFiles::GITLEAKS_CHECK,
        GitFiles::GITLEAKS_CONFIG,
        TestbenchYamlPlanner::PATH,
        ...GitFiles::SKELETON_IGNORES,
        SetupState::PATH,
    ];

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
    protected $description = 'Set up Claude Code for this project on top of Laravel Boost (runner, MCP, guidelines, test isolation, gate, hooks)';

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
            PathGuard::assertAllSafe($root, self::OWNED_PATHS);
            $plan = SetupPlan::build($project, $this->planners(), [new HooksPathPlanner()]);
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

        foreach ($plan->actions as $action) {
            $this->newLine();
            $this->line('Run: '.$action->line);
        }

        $count = count($plan->changes) + count($plan->actions);
        $summary = $count === 1 ? '1 change' : $count.' changes';

        if ($this->option('check')) {
            $this->line($summary.' would change. Run claude-skills:setup to apply.');

            return self::FAILURE;
        }

        if (! $this->option('yes') && ! $this->confirm('Apply these changes?', false)) {
            $this->line($this->input->isInteractive() ? 'Nothing written.' : 'Nothing written. Pass --yes to apply without a prompt.');

            return self::SUCCESS;
        }

        return $this->applyPlan($root, $plan) ? self::SUCCESS : self::FAILURE;
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
        $planners = [
            new McpPlanner(),
            new RunnerGuidelinePlanner(),
            new CoreOverridePlanner(),
            new PhpunitPlanner(),
            new ComposerScriptPlanner(),
            new DdevDatabasePlanner(),
            new StaticFilePlanner(GitFiles::COMMIT_MSG, GitFiles::commitMsg(), true),
            new StaticFilePlanner(GitFiles::GITLEAKS_CHECK, GitFiles::gitleaksCheck(), true),
            new StaticFilePlanner(GitFiles::GITLEAKS_CONFIG, GitFiles::gitleaksConfig()),
            new TestbenchYamlPlanner(),
        ];

        foreach (GitFiles::SKELETON_IGNORES as $path) {
            $planners[] = new StaticFilePlanner($path, GitFiles::IGNORE_ALL, false, static fn (Project $project): bool => $project->isPackage());
        }

        return $planners;
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
            $this->line(OutputFormatter::escape($note));
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
     * Apply the file changes in order, then the state file for the files actually
     * written. Each file is checked again right before it is written (no symlink,
     * unchanged since the plan); the first refusal stops the run.
     *
     * @author michtio
     */
    private function applyPlan(string $root, SetupPlan $plan): bool
    {
        $written = [];
        $actionsRun = 0;
        $stateChange = null;
        $failure = null;

        foreach ($plan->changes as $change) {
            if ($change->path === SetupState::PATH) {
                $stateChange = $change;

                continue;
            }

            $failure = $this->refusal($root, $change);

            if ($failure === null && ! $this->apply($root, $change)) {
                $failure = 'Could not write '.$change->path.'.';
            }

            if ($failure !== null) {
                break;
            }

            $written[] = $change->path;
        }

        if ($failure === null) {
            foreach ($plan->actions as $action) {
                if (! $action->stillValid()) {
                    $failure = 'The git configuration changed since the plan was shown; `'.$action->line.'` was not run.';

                    break;
                }

                if (! $action->run()) {
                    $failure = '`'.$action->line.'` failed.';

                    break;
                }

                $this->line('Ran '.$action->line);
                $actionsRun++;
            }
        }

        // The state records only what was written, so it is written even after a refusal.
        $state = $plan->stateAfter($written);
        $stateBefore = $stateChange !== null ? $stateChange->before : PlannedFile::read($root, SetupState::PATH);
        $stateRefusal = $this->refusal($root, new FileChange(SetupState::PATH, $stateBefore, $state));

        if ($stateRefusal !== null) {
            $failure ??= $stateRefusal;
        } elseif ($stateBefore === null || SetupPlan::normalise($stateBefore) !== SetupPlan::normalise($state)) {
            if ($this->apply($root, new FileChange(SetupState::PATH, $stateBefore, $state))) {
                $written[] = SetupState::PATH;
            } else {
                $failure ??= 'Could not write '.SetupState::PATH.'.';
            }
        }

        if ($failure !== null) {
            $this->error($failure.' Nothing further was written.');

            return false;
        }

        $count = count($written) + $actionsRun;
        $this->info('Applied: '.($count === 1 ? '1 change' : $count.' changes').'.');

        return true;
    }

    /**
     * Why a change must not be written now, or null: its path became unsafe, or the
     * file no longer holds what the plan showed.
     *
     * @author michtio
     */
    private function refusal(string $root, FileChange $change): ?string
    {
        try {
            PathGuard::assertSafe($root, $change->path);
        } catch (SetupException $exception) {
            return $exception->getMessage();
        }

        if (PlannedFile::read($root, $change->path) !== $change->before) {
            return $change->path.' changed since the plan was shown; it was not written.';
        }

        return null;
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

        if ($change->executable && ! chmod($file, (fileperms($file) & 0777) | 0111)) {
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
