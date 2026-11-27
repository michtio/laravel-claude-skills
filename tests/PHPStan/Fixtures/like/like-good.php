<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Fixtures\Like\Good;

use Illuminate\Support\Facades\DB;

final class Search
{
    public function literal(): void
    {
        DB::table('users')->where('name', 'like', '%abc%')->get();
    }

    public function literalWhereLike(): void
    {
        DB::table('users')->whereLike('name', 'abc%')->get();
    }

    public function addcslashesForm(string $term): void
    {
        DB::table('users')->where('name', 'like', '%'.addcslashes($term, '%_\\').'%')->get();
    }

    public function strReplaceForm(string $term): void
    {
        $escaped = str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $term);

        DB::table('users')->where('name', 'like', '%'.str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $term).'%')->get();
        DB::table('users')->where('name', 'like', $escaped)->get();
    }

    public function helperForm(string $term): void
    {
        DB::table('users')->whereLike('name', '%'.$this->escapeLike($term).'%')->get();
    }

    public function otherOperator(string $term): void
    {
        DB::table('users')->where('name', '=', '%'.$term)->get();
    }

    private function escapeLike(string $value): string
    {
        return addcslashes($value, '%_\\');
    }
}
