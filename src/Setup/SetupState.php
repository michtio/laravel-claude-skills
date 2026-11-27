<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * What the setup wrote last, kept in `.ai/claude-skills-setup.json`.
 *
 * Hand-edit detection: for every file it writes, the setup records a fingerprint
 * (sha256 of the part it owns, line endings normalised to LF) of the content it
 * wrote. On the next run a file whose owned part no longer matches the recorded
 * fingerprint was changed by someone else, and the plan says
 * "edited by hand: <path>" before its diff. A file that still matches is the
 * setup's own output and is refreshed silently, so the setup never flags what it
 * wrote itself. Generated files carry no marker of their own, so nothing extra
 * leaks into the CLAUDE.md that Boost composes from them.
 *
 * It also records the profile's extra setup steps that ran (name and command), so
 * a rerun plans only a step that is new or whose name or command changed.
 *
 * The file is written only together with the files it describes, shown in the
 * plan like any other change, and meant to be committed so every clone and CI
 * agree on what the setup wrote.
 *
 * @author michtio
 */
final class SetupState
{
    // Constants
    // =========================================================================

    /**
     * Path of the state file, relative to the project root.
     */
    public const PATH = '.ai/claude-skills-setup.json';

    // Public Methods
    // =========================================================================

    /**
     * Create a state from recorded fingerprints.
     *
     * @param array<string, string> $files Path => fingerprint of the content the setup wrote.
     * @param list<array{name: string, command: string}> $steps The extra steps that ran, in profile order.
     * @author michtio
     */
    public function __construct(
        public readonly array $files = [],
        public readonly array $steps = [],
    ) {
    }

    /**
     * Load the state of a project; a missing or unreadable file is an empty state.
     *
     * @author michtio
     */
    public static function load(string $root): self
    {
        $content = PlannedFile::read($root, self::PATH);
        $decoded = $content === null ? null : json_decode($content, true);
        $files = [];

        if (is_array($decoded) && is_array($decoded['files'] ?? null)) {
            foreach ($decoded['files'] as $path => $fingerprint) {
                if (is_string($path) && is_string($fingerprint)) {
                    $files[$path] = $fingerprint;
                }
            }
        }

        $steps = [];

        if (is_array($decoded) && is_array($decoded['steps'] ?? null)) {
            foreach ($decoded['steps'] as $step) {
                if (is_array($step) && is_string($step['name'] ?? null) && is_string($step['command'] ?? null)) {
                    $steps[] = ['name' => $step['name'], 'command' => $step['command']];
                }
            }
        }

        return new self($files, $steps);
    }

    /**
     * Whether an extra step with this name and command was recorded as run.
     *
     * @author michtio
     */
    public function ran(string $name, string $command): bool
    {
        foreach ($this->steps as $step) {
            if ($step['name'] === $name && $step['command'] === $command) {
                return true;
            }
        }

        return false;
    }

    /**
     * The fingerprint of a piece of content: sha256 with line endings normalised to LF.
     *
     * @author michtio
     */
    public static function fingerprint(string $content): string
    {
        return 'sha256:'.hash('sha256', str_replace("\r\n", "\n", $content));
    }

    /**
     * The recorded fingerprint for a path, or null when the setup has no record of it.
     *
     * @author michtio
     */
    public function recorded(string $path): ?string
    {
        return $this->files[$path] ?? null;
    }

    /**
     * The state file's content for this state.
     *
     * @author michtio
     */
    public function render(): string
    {
        $files = $this->files;
        ksort($files);

        $data = [
            'about' => 'Written by claude-skills:setup: what it last wrote to each file, to tell its own output from hand edits. Commit this file.',
            'files' => $files === [] ? new \stdClass() : $files,
        ];

        if ($this->steps !== []) {
            $data['steps'] = $this->steps;
        }

        return json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n";
    }
}
