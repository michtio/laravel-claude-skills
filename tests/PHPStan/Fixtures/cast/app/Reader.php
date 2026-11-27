<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Cast\Good;

final class Reader
{
    public function port(): int
    {
        return config()->integer('services.port');
    }

    public function rate(string $raw): float
    {
        return (float) $raw;
    }
}
