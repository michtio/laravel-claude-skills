<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\Fixtures\S9d1DeadCode;

/**
 * A planted class for the S9d-1 gate: its public method is called nowhere, so the unused-public-code
 * check must report it.
 *
 * @author michtio
 */
final class S9d1Unused
{
    // Public Methods
    // =========================================================================

    /**
     * Never called by any code in the pack.
     *
     * @author michtio
     */
    public function neverCalled(): int
    {
        return 1;
    }
}
