<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

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
 * The state file change is shown with the others and computed again at apply
 * time from the files actually written (stateAfter()), so an aborted run never
 * records a file it did not write.
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
     * @author michtio
     */
    public function __construct(
        public readonly array $changes,
        public readonly array $notices = [],
        public readonly array $settled = [],
        public readonly array $previous = [],
    ) {
    }

    /**
     * Build the plan for a project from its planners and recorded state.
     *
     * @param list<Planner> $planners
     * @throws SetupException When a planner refuses the project's current state.
     * @author michtio
     */
    public static function build(Project $project, array $planners): self
    {
        $state = SetupState::load($project->root);
        $settled = [];
        $changes = [];
        $notices = [];

        foreach ($planners as $planner) {
            $file = $planner->plan($project);
            $previous = $state->recorded($file->path);
            $handEdited = self::isHandEdited($file, $previous);

            if ($file->desired === null) {
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
                $settled[$file->path] = (string) $file->desiredFingerprint;

                continue;
            }

            $notes = match (true) {
                $file->current === null && $previous !== null => ['deleted since the last run: '.$file->path],
                $handEdited && $previous !== null => ['it differs from what the setup wrote last; applying replaces the edit'],
                $handEdited => ['the setup has no record of writing it; applying replaces its content'],
                $file->current !== null && $file->foreignNote !== null => [$file->path.': '.$file->foreignNote],
                default => [],
            };
            $changes[] = new FileChange($file->path, $file->current, $file->desired, $handEdited, $notes, $file->desiredFingerprint);
        }

        $plan = new self($changes, $notices, $settled, $state->files);
        $stateFile = $plan->stateAfter(array_map(static fn (FileChange $change): string => $change->path, $changes));
        $currentState = PlannedFile::read($project->root, SetupState::PATH);

        if ($currentState === null || self::normalise($currentState) !== self::normalise($stateFile)) {
            $changes[] = new FileChange(SetupState::PATH, $currentState, $stateFile);
        }

        return new self($changes, $notices, $settled, $state->files);
    }

    /**
     * Whether the plan changes anything on disk.
     *
     * @author michtio
     */
    public function isEmpty(): bool
    {
        return $this->changes === [];
    }

    /**
     * The state file content after writing the given changed paths: settled files
     * and written files with their new fingerprints, files the run did not get to
     * with what was recorded before, deleted files dropped.
     *
     * @param list<string> $written Paths of the file changes actually applied.
     * @author michtio
     */
    public function stateAfter(array $written): string
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

        return (new SetupState($files))->render();
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

        return $file->unrecordedIsHandEdit
            && $file->desired !== null
            && $file->currentFingerprint !== $file->desiredFingerprint;
    }
}
