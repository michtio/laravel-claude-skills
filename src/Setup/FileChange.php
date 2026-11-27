<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * One file the setup will create, change or delete, as shown in the plan.
 *
 * @author michtio
 */
final class FileChange
{
    // Public Methods
    // =========================================================================

    /**
     * Describe one change.
     *
     * @param string $path Path relative to the project root.
     * @param string|null $before Content when the plan was built, null when the file did not exist.
     * @param string|null $after Content after the change, null when the file is deleted.
     * @param bool $handEdited Whether the file differs from what the setup wrote last.
     * @param list<string> $notes Extra lines shown above the diff.
     * @param string|null $fingerprint Fingerprint of the owned part as written, recorded in the state once written.
     * @param bool $executable Whether the written file gets the executable bits.
     * @author michtio
     */
    public function __construct(
        public readonly string $path,
        public readonly ?string $before,
        public readonly ?string $after,
        public readonly bool $handEdited = false,
        public readonly array $notes = [],
        public readonly ?string $fingerprint = null,
        public readonly bool $executable = false,
    ) {
    }
}
