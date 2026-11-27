<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use RuntimeException;

/**
 * A project state the setup refuses to work on, such as an unreadable .mcp.json.
 * The message is shown to the person running the setup as is.
 *
 * @author michtio
 */
final class SetupException extends RuntimeException
{
}
