<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Log\Bad;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;

final class Account extends Model
{
}

final class Handler
{
    public function modelInContext(Account $account): void
    {
        Log::info('created', ['account' => $account]);
    }

    public function modelAsMessage(Account $account): void
    {
        Log::warning($account);
    }

    public function requestAll(Request $request): void
    {
        Log::info('incoming', $request->all());
    }

    public function requestInput(Request $request): void
    {
        Log::debug('incoming', ['body' => $request->input()]);
    }

    public function helperAll(): void
    {
        Log::error('failed', ['payload' => request()->all()]);
    }

    public function wholeRequest(Request $request): void
    {
        Log::critical('incoming', ['request' => $request]);
    }
}
