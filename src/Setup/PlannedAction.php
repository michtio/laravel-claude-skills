<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Closure;

/**
 * A planned change that is not a file write (such as a git config setting): shown
 * in the plan as its command line, confirmed with the files, checked again right
 * before it runs.
 *
 * @author michtio
 */
final class PlannedAction
{
    // Public Methods
    // =========================================================================

    /**
     * Describe one action.
     *
     * @param string $line The command line shown in the plan.
     * @param Closure(): bool $stillValid Whether the situation the plan saw still holds.
     * @param Closure(): bool $run Run the action; false when it failed.
     * @author michtio
     */
    public function __construct(
        public readonly string $line,
        private readonly Closure $stillValid,
        private readonly Closure $run,
    ) {
    }

    /**
     * Whether the situation the plan saw still holds.
     *
     * @author michtio
     */
    public function stillValid(): bool
    {
        return ($this->stillValid)();
    }

    /**
     * Run the action.
     *
     * @author michtio
     */
    public function run(): bool
    {
        return ($this->run)();
    }
}
