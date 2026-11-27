<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * What one planner wants for one project file, before the plan compares it with
 * what the setup recorded last.
 *
 * The fingerprint covers the part of the file the setup owns: the whole file for
 * a generated guideline, only the laravel-boost entry for .mcp.json. It is what
 * the state file records and what hand-edit detection compares.
 *
 * @author michtio
 */
final class PlannedFile
{
    // Public Methods
    // =========================================================================

    /**
     * Describe the wanted state of one file.
     *
     * @param string $path Path relative to the project root, with forward slashes.
     * @param string|null $current The file's content now, null when it does not exist.
     * @param string|null $desired The content to write, or null when the setup no longer writes this file.
     * @param string|null $currentFingerprint Fingerprint of the owned part as it is now, null when absent.
     * @param string|null $desiredFingerprint Fingerprint of the owned part as the setup writes it, null with $desired.
     * @param bool $unrecordedIsHandEdit Whether an existing, differing file the setup has no record of counts as edited by hand.
     * @param string|null $foreignNote A note shown instead of the hand-edit warning when the owned part was rewritten by a known tool.
     * @param bool|null $unrecordedEdit The planner's own verdict for an existing file the setup has no record of (overrides the fingerprint rule).
     * @param bool $executable Whether the file must carry the executable bits.
     * @param bool $currentExecutable Whether the file carries them now.
     * @author michtio
     */
    public function __construct(
        public readonly string $path,
        public readonly ?string $current,
        public readonly ?string $desired,
        public readonly ?string $currentFingerprint,
        public readonly ?string $desiredFingerprint,
        public readonly bool $unrecordedIsHandEdit = true,
        public readonly ?string $foreignNote = null,
        public readonly ?bool $unrecordedEdit = null,
        public readonly bool $executable = false,
        public readonly bool $currentExecutable = false,
    ) {
    }

    /**
     * Plan a file the setup owns entirely: its fingerprint is that of the whole content.
     *
     * @author michtio
     */
    public static function whole(string $root, string $path, ?string $desired, bool $executable = false): self
    {
        $current = self::read($root, $path);

        return new self(
            $path,
            $current,
            $desired,
            $current === null ? null : SetupState::fingerprint($current),
            $desired === null ? null : SetupState::fingerprint($desired),
            executable: $executable,
            currentExecutable: $current !== null && (fileperms($root.'/'.$path) & 0111) !== 0,
        );
    }

    /**
     * Read a project file, or null when it does not exist.
     *
     * @author michtio
     */
    public static function read(string $root, string $path): ?string
    {
        $file = $root.'/'.$path;

        return is_file($file) ? (string) file_get_contents($file) : null;
    }
}
