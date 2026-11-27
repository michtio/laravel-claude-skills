<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Michtio\LaravelClaudeSkills\Setup\Planners\Planner;

/**
 * The full plan of one setup run: every file change, hand edits marked, and the
 * state file that records what the run writes.
 *
 * For each planned file:
 * - wanted content equals the current content: no change;
 * - otherwise a change, marked "edited by hand" when the file's owned part
 *   differs from the fingerprint the setup recorded last (or, for a file the
 *   setup has no record of, when the planner says an unrecorded file counts);
 * - a file the setup no longer writes is deleted only when it still matches the
 *   recorded fingerprint; a hand-edited one is left in place and forgotten.
 *
 * The state file is a change like any other, so it is shown and only written
 * together with the files it describes.
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
     * @param list<FileChange> $changes
     * @param list<string> $notices Lines shown before the diffs that change nothing on disk.
     * @author michtio
     */
    public function __construct(
        public readonly array $changes,
        public readonly array $notices = [],
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
        $recorded = [];
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

            $recorded[$file->path] = (string) $file->desiredFingerprint;

            if ($file->current === $file->desired) {
                continue;
            }

            $notes = match (true) {
                $handEdited && $previous !== null => ['it differs from what the setup wrote last; applying replaces the edit'],
                $handEdited => ['the setup has no record of writing it; applying replaces its content'],
                $file->current !== null && $file->foreignNote !== null => [$file->foreignNote],
                default => [],
            };
            $changes[] = new FileChange($file->path, $file->current, $file->desired, $handEdited, $notes);
        }

        $stateFile = (new SetupState($recorded))->render();
        $currentState = PlannedFile::read($project->root, SetupState::PATH);

        if ($currentState !== $stateFile) {
            $changes[] = new FileChange(SetupState::PATH, $currentState, $stateFile);
        }

        return new self($changes, $notices);
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

    // Private Methods
    // =========================================================================

    /**
     * Whether a planned file's owned part was changed by someone other than the setup.
     *
     * @author michtio
     */
    private static function isHandEdited(PlannedFile $file, ?string $previous): bool
    {
        if ($file->current === null || $file->currentFingerprint === null) {
            return false;
        }

        if ($previous !== null) {
            return $file->currentFingerprint !== $previous && $file->foreignNote === null;
        }

        return $file->unrecordedIsHandEdit
            && $file->desired !== null
            && $file->currentFingerprint !== $file->desiredFingerprint;
    }
}
