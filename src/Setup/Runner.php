<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * Where the project's PHP, Composer and Node commands run: inside DDEV or on the host.
 *
 * @author michtio
 */
enum Runner: string
{
    case Ddev = 'ddev';
    case Host = 'host';
}
