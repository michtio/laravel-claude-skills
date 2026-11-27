<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Env\Good;

final class Good
{
    public function key(): string
    {
        return config('app.key');
    }

    public function environment(): string
    {
        return $this->env();
    }

    public function lookup(): string
    {
        return Registry::env('name');
    }

    private function env(): string
    {
        return 'testing';
    }
}
