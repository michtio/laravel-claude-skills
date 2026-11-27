<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Good;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Mail;

final class SendReceipt implements ShouldQueue
{
    use Dispatchable;
    use Queueable;

    public function __construct(public int $orderId)
    {
    }
}

final class Checkout
{
    public function afterTheTransaction(string $address): void
    {
        DB::transaction(function () {
            DB::table('orders')->insert(['status' => 'paid']);
        });

        Http::post('https://provider.test/charges', ['amount' => 100]);
        Mail::to($address)->send(new \stdClass());
    }

    public function wrappedInAfterCommit(string $address): void
    {
        DB::transaction(function () use ($address) {
            DB::table('orders')->insert(['status' => 'paid']);

            DB::afterCommit(function () use ($address) {
                Http::post('https://provider.test/charges', ['amount' => 100]);
                Mail::to($address)->send(new \stdClass());
            });
        });
    }

    public function wrappedInAfterCommitArrowFunction(): void
    {
        DB::transaction(function () {
            DB::afterCommit(fn () => Http::post('https://provider.test/charges', ['amount' => 100]));
        });
    }

    public function queuedAfterCommit(int $orderId): void
    {
        DB::transaction(function () use ($orderId) {
            DB::table('orders')->insert(['status' => 'paid']);

            SendReceipt::dispatch($orderId)->afterCommit();
        });
    }

    public function httpWithoutATransaction(): void
    {
        Http::get('https://provider.test/status');
    }
}
