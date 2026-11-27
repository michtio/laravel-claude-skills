<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Env\Bad;

final class Service
{
    public function key(): string
    {
        return env('PAYMENT_KEY');
    }

    public function withDefault(): bool
    {
        return \env('FEATURE_X', false);
    }

    public function inClosure(): callable
    {
        return fn () => env('REGION', 'eu');
    }
}
