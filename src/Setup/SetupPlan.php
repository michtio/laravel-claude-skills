<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Michtio\LaravelClaudeSkills\Setup\Planners\ActionPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\Planner;

/**
 * The full plan of one setup run: every file change, hand edits marked, and the
 * state file that records what the run writes.
 *
 * For each planned file:
 * - wanted content equals the current content (line endings normalised): no change;
 * - otherwise a change, marked "edited by hand" when the file's owned part
 *   differs from the fingerprint the setup recorded last (or, for a file the
 *   setup has no record of, when the planner says an unrecorded file counts);
 *   a recorded file that is missing is noted as "deleted since the last run";
 * - a file the setup no longer writes is deleted only when it still matches the
 *   recorded fingerprint; a hand-edited one is left in place and forgotten.
 *
 * The record of a file the setup no longer writes and the person deleted (a
 * takeover: phpstan.neon.dist created, phpstan.neon deleted) is kept while
 * nothing else changes, so `--check` exits 0; the next real change drops it.
 * Proven by tests/Profile/S9d1OutputTest.php ("exits 0 on --check after the takeover").
 *
 * The state file change is shown with the others and computed again at apply
 * time from the files actually written (stateAfter()), so an aborted run never
 * records a file it did not write.
 *
 * Extra steps from the profile are planned when the state has no record of a step
 * with the same name and command; they run last and are recorded once they ran.
 * The records of steps no longer in the profile are dropped when the state is
 * written anyway, never as a change of their own, so removing a step plans nothing.
 *
 * @author michtio
 */
final class SetupPlan
{
    // Public Methods
    // =========================================================================

    /**
     * Hold the resolved changes.
     *
     * @param list<FileChange> $changes File changes, the state file change (if any) last.
     * @param list<string> $notices Lines shown before the diffs that change nothing on disk.
     * @param array<string, string> $settled Path => fingerprint for owned files that need no change.
     * @param array<string, string> $previous Path => fingerprint the state recorded before this run.
     * @param list<PlannedAction> $actions Changes that are not file writes, run after the files.
     * @param list<array{name: string, command: string}> $steps Extra steps to run, last, in profile order.
     * @param list<array{name: string, command: string}> $keptSteps Step records the state keeps.
     * @param list<array{name: string, command: string}> $profileSteps Every step of the profile, for the record order.
     * @param bool $keepStepOrder Whether the kept records stay exactly as recorded (nothing else changes).
     * @author michtio
     */
    public function __construct(
        public readonly array $changes,
        public readonly array $notices = [],
        public readonly array $settled = [],
        public readonly array $previous = [],
        public readonly array $actions = [],
        public readonly array $steps = [],
        private readonly array $keptSteps = [],
        private readonly array $profileSteps = [],
        private readonly bool $keepStepOrder = true,
    ) {
    }

    /**
     * Build the plan for a project from its planners and recorded state.
     *
     * @param list<Planner> $planners
     * @param list<ActionPlanner> $actionPlanners
     * @param list<array{name: string, command: string}> $profileSteps The profile's extra steps, in order.
     * @throws SetupException When a planner refuses the project's current state.
     * @author michtio
     */
    public static function build(Project $project, array $planners, array $actionPlanners = [], array $profileSteps = []): self
    {
        $state = SetupState::load($project->root);
        $settled = [];
        $stale = [];
        $changes = [];
        $notices = [];

        foreach ($planners as $planner) {
            $file = $planner->plan($project);
            $previous = $state->recorded($file->path);
            $handEdited = self::isHandEdited($file, $previous);

            if ($file->desired === null) {
                // A file the person deleted (a takeover through its .dist) keeps its record until a real change.
                if ($file->current === null && $previous !== null) {
                    $stale[$file->path] = $previous;
                }

                if ($file->current === null || $previous === null) {
                    continue;
                }

                if ($handEdited) {
                    $notices[] = 'edited by hand: '.$file->path.' (no longer written by the setup; left in place)';

                    continue;
                }

                $changes[] = new FileChange($file->path, $file->current, null);

                continue;
            }

            if ($file->current !== null && self::normalise($file->current) === self::normalise($file->desired)) {
                if ($file->executable && ! $file->currentExecutable) {
                    $changes[] = new FileChange($file->path, $file->current, $file->current, false, ['the executable bit is missing: '.$file->path.' (restored on apply)'], $file->desiredFingerprint, true);

                    continue;
                }

                $settled[$file->path] = (string) $file->desiredFingerprint;

                continue;
            }

            $notes = match (true) {
                $file->current === null && $previous !== null => ['deleted since the last run: '.$file->path],
                $handEdited && $previous !== null => $file->replaceNote === null
                    ? ['it differs from what the setup wrote last; applying replaces the edit']
                    : ['it differs from what the setup wrote last; applying replaces the edit', $file->replaceNote],
                $handEdited => ['the setup has no record of writing it; applying replaces its content'],
                $file->current !== null && $file->foreignNote !== null => [$file->path.': '.$file->foreignNote],
                default => [],
            };
            $changes[] = new FileChange($file->path, $file->current, $file->desired, $handEdited, $notes, $file->desiredFingerprint, $file->executable);
        }

        $pending = array_values(array_filter(
            $profileSteps,
            static fn (array $step): bool => ! $state->ran($step['name'], $step['command']),
        ));
        $keepStepOrder = $pending === [] && $changes === [];

        // Dropping only a stale record is no change of its own: --check stays clean after a takeover.
        if ($keepStepOrder) {
            $settled += $stale;
        }
        $kept = $keepStepOrder ? $state->steps : array_values(array_filter(
            $state->steps,
            static fn (array $record): bool => in_array($record, $profileSteps, true),
        ));

        $plan = new self($changes, $notices, $settled, $state->files, [], $pending, $kept, $profileSteps, $keepStepOrder);
        $stateFile = $plan->stateAfter(array_map(static fn (FileChange $change): string => $change->path, $changes), $pending);
        $currentState = PlannedFile::read($project->root, SetupState::PATH);

        if ($currentState === null || self::normalise($currentState) !== self::normalise($stateFile)) {
            $changes[] = new FileChange(SetupState::PATH, $currentState, $stateFile);
        }

        $actions = [];

        foreach ($actionPlanners as $actionPlanner) {
            [$action, $lines] = $actionPlanner->plan($project);
            array_push($notices, ...$lines);

            if ($action !== null) {
                $actions[] = $action;
            }
        }

        return new self($changes, $notices, $settled, $state->files, $actions, $pending, $kept, $profileSteps, $keepStepOrder);
    }

    /**
     * Whether the plan changes anything on disk.
     *
     * @author michtio
     */
    public function isEmpty(): bool
    {
        return $this->changes === [] && $this->actions === [] && $this->steps === [];
    }

    /**
     * The state file content after writing the given changed paths: settled files
     * and written files with their new fingerprints, files the run did not get to
     * with what was recorded before, deleted files dropped.
     *
     * @param list<string> $written Paths of the file changes actually applied.
     * @param list<array{name: string, command: string}> $ranSteps Extra steps that ran in this run.
     * @author michtio
     */
    public function stateAfter(array $written, array $ranSteps = []): string
    {
        $files = $this->settled;

        foreach ($this->changes as $change) {
            if ($change->path === SetupState::PATH) {
                continue;
            }

            if (in_array($change->path, $written, true)) {
                if ($change->after !== null && $change->fingerprint !== null) {
                    $files[$change->path] = $change->fingerprint;
                }

                continue;
            }

            if (isset($this->previous[$change->path])) {
                $files[$change->path] = $this->previous[$change->path];
            }
        }

        return (new SetupState($files, $this->stepRecords($ranSteps)))->render();
    }

    /**
     * Content with line endings normalised to LF, for comparisons.
     *
     * @author michtio
     */
    public static function normalise(string $content): string
    {
        return str_replace("\r\n", "\n", $content);
    }

    // Private Methods
    // =========================================================================

    /**
     * The step records after this run: the kept records and the steps that ran,
     * in profile order (or, when nothing else changes, exactly as recorded).
     *
     * @param list<array{name: string, command: string}> $ranSteps
     * @return list<array{name: string, command: string}>
     * @author michtio
     */
    private function stepRecords(array $ranSteps): array
    {
        if ($this->keepStepOrder) {
            $records = $this->keptSteps;

            foreach ($ranSteps as $step) {
                if (! in_array($step, $records, true)) {
                    $records[] = $step;
                }
            }

            return $records;
        }

        $records = [];

        foreach ($this->profileSteps as $step) {
            if ((in_array($step, $this->keptSteps, true) || in_array($step, $ranSteps, true)) && ! in_array($step, $records, true)) {
                $records[] = $step;
            }
        }

        return $records;
    }

    /**
     * Whether a planned file's owned part was changed by someone other than the setup.
     *
     * @author michtio
     */
    private static function isHandEdited(PlannedFile $file, ?string $previous): bool
    {
        if ($file->current === null || $file->currentFingerprint === null || $file->foreignNote !== null) {
            return false;
        }

        if ($previous !== null) {
            return $file->currentFingerprint !== $previous;
        }

        if ($file->unrecordedEdit !== null) {
            return $file->unrecordedEdit;
        }

        return $file->unrecordedIsHandEdit
            && $file->desired !== null
            && $file->currentFingerprint !== $file->desiredFingerprint;
    }
}
