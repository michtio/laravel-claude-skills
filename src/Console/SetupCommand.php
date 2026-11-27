<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Console;

use Illuminate\Console\Command;
use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;
use Michtio\LaravelClaudeSkills\Setup\Advisories;
use Michtio\LaravelClaudeSkills\Setup\DdevDatabaseSource;
use Michtio\LaravelClaudeSkills\Setup\FileChange;
use Michtio\LaravelClaudeSkills\Setup\GitFiles;
use Michtio\LaravelClaudeSkills\Setup\PathGuard;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Planners\ComposerScriptPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\CoreOverridePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\CreatedOnceFilePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\DdevDatabasePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\HooksPathPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\LarastanPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\McpPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\MonitoringPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\PhpstanPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\PhpunitPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\Planner;
use Michtio\LaravelClaudeSkills\Setup\Planners\RunnerGuidelinePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\StaticFilePlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\TestbenchYamlPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\WorkflowPlanner;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\Runner;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Michtio\LaravelClaudeSkills\Setup\SetupPlan;
use Michtio\LaravelClaudeSkills\Setup\SetupState;
use Michtio\LaravelClaudeSkills\Setup\UnifiedDiff;
use Symfony\Component\Console\Formatter\OutputFormatter;
use Symfony\Component\Process\Process;

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
 * It reads the optional profile `.ai/skills-profile.json` (never writes it): the
 * Laravel options (runner, monitoring, ci and the rest, over their documented
 * defaults, which it states when there is no profile), and the extra setup steps,
 * shown last in the plan and run last, each once (a rerun runs only a new or
 * changed step). An invalid profile is refused before anything is planned.
 *
 * Every run also prints the advisories (Advisories, PhpstanPlanner::shadowNotice())
 * and the suggested `.claude/settings.json`, which it never writes.
 *
 * Exit codes: 0 when done, declined or nothing to do; 1 with --check when
 * something would change, for an invalid profile, when a step or action fails,
 * and when the project is in a state it refuses to touch.
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
        GitFiles::GITLEAKS_DOCKERFILE,
        TestbenchYamlPlanner::PATH,
        WorkflowPlanner::PATH,
        PhpstanPlanner::PATH,
        ...GitFiles::SKELETON_IGNORES,
        SetupState::PATH,
    ];

    /**
     * The GitHub repository of the plugin marketplace that ships the agents.
     */
    private const MARKETPLACE = 'michtio/laravel-claude-skills';

    /**
     * The agents plugin, as `<plugin>@<marketplace>` in Claude Code's enabledPlugins.
     */
    private const PLUGIN = 'laravel-claude-skills@laravel-claude-skills';

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

        try {
            $profile = Profile::load($root);
        } catch (ProfileException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }

        $options = $profile->effective();
        $runner = $options['runner'] === 'auto' ? null : Runner::from((string) $options['runner']);
        $ddevTestDatabase = $options['test_database'] === 'ddev';
        $project = Project::detect($root, $runner, $ddevTestDatabase);
        $this->line('Detected: '.$project->kind->value);
        $this->line('Runner: '.$project->runner->value);
        $this->showProfile($profile);

        if ($ddevTestDatabase && ! $project->usesDdev()) {
            $this->error('laravel.test_database is ddev, but this project does not run on DDEV (no .ddev/ directory, or laravel.runner is host): there is no DDEV database to test on. Set it to auto, or run the project on DDEV. Nothing was written.');

            return self::FAILURE;
        }

        if ($project->ddevTestDatabase) {
            try {
                $project = $project->withDdevDatabase($project->resolveDdevDatabase($this->laravel->make(DdevDatabaseSource::class)));
            } catch (SetupException $exception) {
                $this->error($exception->getMessage());

                return self::FAILURE;
            }
        }

        $phpstan = new PhpstanPlanner((int) $options['phpstan_level'], $profile->sets('phpstan_level'));

        try {
            PathGuard::assertAllSafe($root, self::OWNED_PATHS);

            // tests/Pest.php may be created in a Pest package; CLAUDE.md may be created, never written once it exists.
            if ($project->isPackage() && $project->requires('pestphp/pest')) {
                PathGuard::assertSafe($root, CreatedOnceFilePlanner::PEST);
            }

            PathGuard::assertLinkInside($root, CreatedOnceFilePlanner::CLAUDE_MD);
            PathGuard::assertLinkInside($root, CreatedOnceFilePlanner::BOOST_JSON);
            $plan = SetupPlan::build(
                $project,
                [...$this->planners($profile), $phpstan],
                [new HooksPathPlanner(), new MonitoringPlanner((string) $options['monitoring']), new LarastanPlanner($phpstan)],
                $profile->steps(),
            );
            $phpstanNotice = $phpstan->notice($project);
            $shadowNotice = $phpstan->shadowNotice($project);
        } catch (SetupException $exception) {
            $this->error($exception->getMessage());

            return self::FAILURE;
        }

        foreach ($plan->notices as $notice) {
            $this->warn($notice);
        }

        if ($phpstanNotice !== null) {
            $this->line($phpstanNotice);
        }

        if ($shadowNotice !== null) {
            $this->warn($shadowNotice);
        }

        foreach (Advisories::lines($project) as $advisory) {
            $this->warn(OutputFormatter::escape($advisory));
        }

        if (CreatedOnceFilePlanner::claudeMd()->creates($project) && file_exists($root.'/AGENTS.md')) {
            $this->warn('AGENTS.md exists but CLAUDE.md does not: the setup creates an empty CLAUDE.md, so Boost writes its guidelines there and Claude Code reads them. AGENTS.md is left alone.');
        }

        $databaseNotice = (new DdevDatabasePlanner())->notice($project);

        if ($databaseNotice !== null) {
            $this->warn($databaseNotice);
        }

        $this->showAgentsInstall($root);
        $this->showSuggestedSettings($project);

        if ($plan->isEmpty()) {
            $this->info('No changes.');

            return self::SUCCESS;
        }

        foreach ($plan->changes as $change) {
            $this->show($change);
        }

        foreach ($plan->actions as $action) {
            $this->newLine();
            $this->commandLine('Run: ', $action->line);
        }

        foreach ($plan->steps as $step) {
            $this->newLine();
            $this->line(OutputFormatter::escape('Extra step: '.$step['name']));
            $this->commandLine('Run: ', $step['command']);
        }

        // The state file only records the others: it counts when it is the one change.
        $files = array_filter($plan->changes, static fn (FileChange $change): bool => $change->path !== SetupState::PATH);
        $count = max(1, count($files) + count($plan->actions) + count($plan->steps));
        $summary = $count === 1 ? '1 change planned.' : $count.' changes planned.';

        if ($this->option('check')) {
            $this->line($summary.' Run claude-skills:setup to apply.');

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
     * State where the options come from and list every effective option with its
     * source, `(profile)` or `(default)`, on every run. Unknown keys under `laravel`
     * are named, so a typo is not silent.
     *
     * @author michtio
     */
    private function showProfile(Profile $profile): void
    {
        if ($profile->exists()) {
            $this->line('Profile: '.Profile::PATH);
        } else {
            $this->line('No profile found at '.Profile::PATH.'; using the defaults:');
        }

        foreach ($profile->effective() as $key => $value) {
            $source = $profile->sets($key) ? 'profile' : 'default';
            $this->line(OutputFormatter::escape('  '.$key.': '.$this->optionValue($key, $value).' ('.$source.')'));
        }

        if ($profile->setsCiServices()) {
            $services = $profile->ciServices();
            $this->line(OutputFormatter::escape('  ci_services: '.($services === [] ? 'none' : implode(', ', $services)).' (profile)'));
        }

        foreach ($profile->unknownLaravelKeys() as $key) {
            $this->warn(OutputFormatter::escape('Ignoring unknown profile key: laravel.'.$key));
        }
    }

    /**
     * An option's value as printed: booleans as true/false, a PHP matrix list joined
     * by commas, the test pins as NAME=value (or `none`).
     *
     * @author michtio
     */
    private function optionValue(string $key, mixed $value): string
    {
        if ($key === 'test_pins') {
            if (! is_array($value) || $value === []) {
                return 'none';
            }

            return implode(', ', array_map(
                static fn (string|int $name, mixed $pin): string => $name.'='.(is_scalar($pin) ? (string) $pin : ''),
                array_keys($value),
                $value,
            ));
        }

        return match (true) {
            is_bool($value) => $value ? 'true' : 'false',
            is_array($value) => implode(', ', array_map(static fn (mixed $item): string => is_scalar($item) ? (string) $item : '', $value)),
            is_scalar($value) => (string) $value,
            default => '',
        };
    }

    /**
     * Print the two Claude Code commands that install this pack's agents, unless the
     * project's `.claude/settings.json` already enables the plugin. Printed text only:
     * the setup never writes Claude Code's settings.
     *
     * @author michtio
     */
    private function showAgentsInstall(string $root): void
    {
        $settings = PlannedFile::read($root, '.claude/settings.json');
        $decoded = $settings === null ? null : json_decode($settings, true);
        $enabled = is_array($decoded) && is_array($decoded['enabledPlugins'] ?? null)
            ? ($decoded['enabledPlugins'][self::PLUGIN] ?? null)
            : null;

        if ($enabled === true) {
            return;
        }

        $this->line('The agents (builder, gate writer, reviewers) ship as a Claude Code plugin. In Claude Code, run:');
        $this->line('  /plugin marketplace add '.self::MARKETPLACE);
        $this->line('  /plugin install '.self::PLUGIN);
    }

    /**
     * Print the Claude Code permissions suggested for the project's
     * `.claude/settings.json`, on every run: the gate command as one exact rule
     * (`Bash(composer test)`, `Bash(ddev composer test)` on DDEV), and the agents
     * plugin. No wildcard rule: `ddev exec` runs its arguments through the
     * container's `bash -c`, which expands `$(...)` even inside single quotes, and
     * on the host `pest -c <file>` skips the pins and `pint *` can rewrite locked
     * gate files. Printed text only: the setup never writes Claude Code's settings.
     * Proven by tests/Profile/S9d1OutputTest.php ("prints suggested .claude/settings.json
     * permissions", "never writes .claude/settings.json").
     *
     * @author michtio
     */
    private function showSuggestedSettings(Project $project): void
    {
        $settings = [
            'permissions' => [
                'allow' => ['Bash('.$project->composer().' test)'],
            ],
            'extraKnownMarketplaces' => [
                'laravel-claude-skills' => ['source' => ['source' => 'github', 'repo' => self::MARKETPLACE]],
            ],
            'enabledPlugins' => [self::PLUGIN => true],
        ];

        $this->line('Suggested for .claude/settings.json (the setup never writes it; merge what you want):');

        foreach (explode("\n", (string) json_encode($settings, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)) as $line) {
            $this->line(OutputFormatter::escape($line));
        }
    }

    /**
     * The planners, one per concern, in the order their changes are shown.
     *
     * @return list<Planner>
     * @author michtio
     */
    private function planners(Profile $profile): array
    {
        $options = $profile->effective();
        $testPins = is_array($options['test_pins']) ? array_map('strval', $options['test_pins']) : [];
        $planners = [
            CreatedOnceFilePlanner::claudeMd(),
            CreatedOnceFilePlanner::boostJson(),
            new McpPlanner(),
            new RunnerGuidelinePlanner(),
            new CoreOverridePlanner(),
            new PhpunitPlanner($testPins),
            new ComposerScriptPlanner(),
            new DdevDatabasePlanner(),
            new StaticFilePlanner(GitFiles::COMMIT_MSG, GitFiles::commitMsg(), true),
            new StaticFilePlanner(GitFiles::GITLEAKS_CHECK, static fn (Project $project): string => GitFiles::gitleaksCheck($project->usesDdev()), true),
            new StaticFilePlanner(GitFiles::GITLEAKS_CONFIG, GitFiles::gitleaksConfig()),
            new StaticFilePlanner(GitFiles::GITLEAKS_DOCKERFILE, GitFiles::gitleaksDockerfile(), false, static fn (Project $project): bool => $project->usesDdev()),
            new TestbenchYamlPlanner(),
        ];

        foreach (GitFiles::SKELETON_IGNORES as $path) {
            $planners[] = new StaticFilePlanner($path, GitFiles::IGNORE_ALL, false, static fn (Project $project): bool => $project->isPackage());
        }

        $planners[] = CreatedOnceFilePlanner::pest();
        $planners[] = new WorkflowPlanner(
            $options['ci'] === true,
            is_array($options['php_matrix']) ? array_values(array_map('strval', $options['php_matrix'])) : 'auto',
            $profile->ciServices(),
        );

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
     * Apply the file changes in order, then the actions, then the state file for the
     * files actually written, then the profile's extra steps, and finally the state
     * again with the steps that ran. Each file is checked again right before it is
     * written (no symlink, unchanged since the plan); the first refusal or failure
     * stops the run, and what was written stays written and recorded.
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
                    $failure = 'The situation changed since the plan was shown; `'.$action->line.'` was not run.';

                    break;
                }

                if (! $action->run($this->rawWriter())) {
                    $failure = '`'.$action->line.'` failed.';

                    break;
                }

                $this->commandLine('Ran ', $action->line);
                $actionsRun++;
            }
        }

        // The state records only what was written, so it is written even after a refusal.
        $stateBefore = $stateChange !== null ? $stateChange->before : PlannedFile::read($root, SetupState::PATH);
        [$stateWritten, $stateFailure] = $this->writeState($root, $stateBefore, $plan->stateAfter($written));
        $failure ??= $stateFailure;
        $ran = [];
        $stepFailed = false;

        if ($failure === null && $plan->steps !== []) {
            foreach ($plan->steps as $step) {
                if (! $this->runStep($root, $step['command'])) {
                    $failure = '`'.$step['command'].'` failed. Later steps were not run; it is planned again on the next run.';
                    $stepFailed = true;

                    break;
                }

                $this->commandLine('Ran ', $step['command']);
                $ran[] = $step;
            }

            if ($ran !== []) {
                [$stepsRecorded, $stateFailure] = $this->writeState($root, PlannedFile::read($root, SetupState::PATH), $plan->stateAfter($written, $ran));
                $stateWritten = $stateWritten || $stepsRecorded;
                $failure ??= $stateFailure;
            }
        }

        if ($failure !== null) {
            $this->error(OutputFormatter::escape($stepFailed ? $failure : $failure.' Nothing further was written.'));

            return false;
        }

        // Counted as the plan counts: the state file only when it is the one change
        // (S9d1OutputTest "counts the same changes", S9bOutputTest "1 change planned.").
        $count = count($written) + $actionsRun + count($ran);
        $count = $count === 0 && $stateWritten ? 1 : $count;
        $this->info('Applied: '.($count === 1 ? '1 change' : $count.' changes').'.');

        return true;
    }

    /**
     * Print a command after its prefix (`Run: `, `Ran `). A multi-line command reads
     * as one block: each continuation line is indented under the first.
     *
     * @author michtio
     */
    private function commandLine(string $prefix, string $command): void
    {
        $lines = preg_split('/\R/', $command) ?: [$command];
        $this->line(OutputFormatter::escape($prefix.array_shift($lines)));

        foreach ($lines as $line) {
            $this->line(OutputFormatter::escape(str_repeat(' ', strlen($prefix)).$line));
        }
    }

    /**
     * A writer that passes a process's output (stdout and stderr) to the console as is.
     *
     * @return \Closure(string): void
     * @author michtio
     */
    private function rawWriter(): \Closure
    {
        return function (string $buffer): void {
            $this->output->write($buffer, false, \Symfony\Component\Console\Output\OutputInterface::OUTPUT_RAW);
        };
    }

    /**
     * Write the state file when its content changes: [whether it was written, the
     * failure or null].
     *
     * @return array{0: bool, 1: string|null}
     * @author michtio
     */
    private function writeState(string $root, ?string $before, string $state): array
    {
        $change = new FileChange(SetupState::PATH, $before, $state);
        $refusal = $this->refusal($root, $change);

        if ($refusal !== null) {
            return [false, $refusal];
        }

        if ($before !== null && SetupPlan::normalise($before) === SetupPlan::normalise($state)) {
            return [false, null];
        }

        return $this->apply($root, $change) ? [true, null] : [false, 'Could not write '.SetupState::PATH.'.'];
    }

    /**
     * Run one extra step as `sh -c <command>` in the project root, its output passed
     * through; false when it exits non-zero or cannot start.
     *
     * @author michtio
     */
    private function runStep(string $root, string $command): bool
    {
        try {
            $process = new Process(['sh', '-c', $command], $root);
            $process->setTimeout(null);
            $write = $this->rawWriter();
            $process->run(static function (string $type, string $buffer) use ($write): void {
                $write($buffer);
            });
        } catch (\Throwable $exception) {
            $this->rawWriter()($exception->getMessage()."\n");

            return false;
        }

        return $process->isSuccessful();
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
