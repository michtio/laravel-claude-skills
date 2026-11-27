<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Profile;

use RuntimeException;

/**
 * Thrown when `.ai/skills-profile.json` is invalid. The message names the file,
 * the dotted path of the offending field and the reason, for example
 * `Invalid profile .ai/skills-profile.json: laravel.ci: must be true or false`.
 *
 * @author michtio
 */
final class ProfileException extends RuntimeException
{
    // Public Methods
    // =========================================================================

    /**
     * Create the exception for one offending field.
     *
     * @param string $field Dotted path of the field (list items by index), or the file path for the file itself.
     * @param string $reason Why the value is refused.
     * @author michtio
     */
    public static function field(string $field, string $reason): self
    {
        return new self('Invalid profile '.Profile::PATH.': '.$field.': '.$reason);
    }
}
