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
     * @param string|null $before Content now, null when the file does not exist.
     * @param string|null $after Content after the change, null when the file is deleted.
     * @param bool $handEdited Whether the file differs from what the setup wrote last.
     * @param list<string> $notes Extra lines shown above the diff.
     * @author michtio
     */
    public function __construct(
        public readonly string $path,
        public readonly ?string $before,
        public readonly ?string $after,
        public readonly bool $handEdited = false,
        public readonly array $notes = [],
    ) {
    }
}
