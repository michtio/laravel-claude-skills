<?php

declare(strict_types=1);

namespace Tests;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use Orchestra\Testbench\TestCase;

class DatabaseTest extends TestCase
{
    public function test_the_suite_runs_on_the_real_test_database(): void
    {
        $this->assertSame('mysql', DB::connection()->getDriverName());
        $this->assertSame('s9b_package_test', DB::connection()->getDatabaseName());

        Schema::dropIfExists('s9b_probe');
        Schema::create('s9b_probe', function ($table): void {
            $table->id();
            $table->string('name');
        });
        DB::table('s9b_probe')->insert(['name' => 'row']);
        $this->assertSame(1, DB::table('s9b_probe')->count());
        Schema::drop('s9b_probe');
    }
}
