<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Bad;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Mail;

final class Checkout
{
    public function httpInClosure(): void
    {
        DB::transaction(function () {
            DB::table('orders')->insert(['status' => 'paid']);
            Http::post('https://provider.test/charges', ['amount' => 100]);
        });
    }

    public function mailInClosure(string $address): void
    {
        DB::transaction(function () use ($address) {
            DB::table('orders')->insert(['status' => 'paid']);
            Mail::to($address)->send(new \stdClass());
        });
    }

    public function httpInArrowFunction(): void
    {
        DB::transaction(fn () => Http::post('https://provider.test/charges', ['amount' => 100]));
    }

    public function httpInNestedClosure(): void
    {
        DB::transaction(function () {
            array_map(function ($id) {
                Http::get('https://provider.test/items/'.$id);
            }, [1, 2]);
        }, 3);
    }
}
