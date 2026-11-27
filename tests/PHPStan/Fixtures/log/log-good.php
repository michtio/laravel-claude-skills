<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Log\Good;

use Illuminate\Cache\Repository;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;

final class Account extends Model
{
}

final class Handler
{
    public function ids(Account $account): void
    {
        Log::info('created', ['account_id' => $account->getKey(), 'status' => $account->getAttribute('status')]);
    }

    public function requestMeta(Request $request): void
    {
        Log::info('incoming', ['path' => $request->path(), 'method' => $request->method()]);
    }

    public function oneNamedField(Request $request): void
    {
        Log::debug('sorting', ['sort' => $request->input('sort')]);
    }

    public function plainMessage(): void
    {
        Log::warning('payment provider unreachable');
    }

    public function notALog(Request $request): void
    {
        Cache::put('last-request', $request->all());
    }
}
