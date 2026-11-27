<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Like\Bad;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Facades\DB;

final class Customer extends Model
{
}

final class Search
{
    public function concatenated(string $term): void
    {
        DB::table('users')->where('name', 'like', '%'.$term.'%')->get();
    }

    public function interpolated(string $term): void
    {
        DB::table('users')->where('name', 'like', "%{$term}%")->get();
    }

    public function orWhere(string $term): void
    {
        DB::table('users')->where('active', 1)->orWhere('email', 'like', $term.'%')->get();
    }

    public function whereLike(string $term): void
    {
        DB::table('users')->whereLike('name', '%'.$term.'%')->get();
    }

    public function upperCaseNotLike(string $term): void
    {
        DB::table('users')->where('name', 'NOT LIKE', '%'.$term)->get();
    }

    public function staticCall(string $term): void
    {
        Customer::where('name', 'like', '%'.$term.'%')->get();
    }

    public function partlyEscaped(string $first, string $second): void
    {
        DB::table('users')->where('name', 'like', '%'.addcslashes($first, '%_\\').$second.'%')->get();
    }
}
