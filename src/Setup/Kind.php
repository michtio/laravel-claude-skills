<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * What the setup runs against: a Laravel application or a package developed with Testbench.
 *
 * @author michtio
 */
enum Kind: string
{
    case App = 'app';
    case Package = 'package';
}
