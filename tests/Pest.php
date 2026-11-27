<?php

declare(strict_types=1);

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Michtio\LaravelClaudeSkills\Tests\Setup\TestCase;

pest()->extend(TestCase::class)->in('Setup');
pest()->extend(ProfileTestCase::class)->in('Profile');
