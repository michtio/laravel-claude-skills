<?php

declare(strict_types=1);

/**
 * Gate tests for the outside builder names (laravel-layer R18), ruled 2026-11-28 in the
 * "S10 review round 1 follow-ups" decision: a builder name must match
 * ^[A-Za-z0-9._-]{1,64}$ in the profile schema and in the setup's ProfileValidator, so
 * the setup refuses an unsafe name. The whole name must match: a trailing newline is
 * refused too (PHP's `$` alone would let it through; the JSON Schema `$` does not).
 *
 * A refused name exits 1 with `Invalid profile .ai/skills-profile.json: builders.<i>.name: `
 * and a reason, writes nothing, and Profile::load throws a ProfileException with that field.
 * The schema half is pinned by tests/gate/test_s7.py (byte pin) and tests/gate/test_s10_round3.py.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;

dataset('unsafe builder names', [
    'a command substitution' => ['x$(curl a)'],
    'a space' => ['a b'],
    'a single quote' => ["a'b"],
    'empty' => [''],
    '65 characters' => [str_repeat('a', 65)],
    'a trailing newline' => ["local-ai\n"],
]);

dataset('safe builder names', [
    'local-ai' => ['local-ai'],
    'glm_5.3' => ['glm_5.3'],
    '64 characters' => [str_repeat('a', 64)],
]);

it('refuses an unsafe builder name, names the field and writes nothing', function (string $name) {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'builders' => [['name' => $name, 'command' => 'run-builder']]]);
    $before = $this->snapshot($dir);

    try {
        Profile::load($dir);
        $thrown = null;
    } catch (ProfileException $e) {
        $thrown = $e;
    }

    expect($thrown)->toBeInstanceOf(ProfileException::class)
        ->and($thrown?->getMessage())->toStartWith('Invalid profile .ai/skills-profile.json: builders.0.name: ')
        ->and(strlen((string) $thrown?->getMessage()))->toBeGreaterThan(strlen('Invalid profile .ai/skills-profile.json: builders.0.name: '));

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: builders.0.name: ')
            ->not->toContain('Applied')
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with('unsafe builder names')->group('R18');

it('checks the name of every builder in the list, not only the first', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'builders' => [
        ['name' => 'local-ai', 'command' => 'run-builder'],
        ['name' => 'x$(curl a)', 'command' => 'run-builder'],
    ]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Invalid profile .ai/skills-profile.json: builders.1.name: ')
        ->not->toContain('builders.0.name');
})->group('R18');

it('accepts a safe builder name', function (string $name) {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'builders' => [['name' => $name, 'command' => 'run-builder']]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('Invalid profile')
        ->and(Profile::load($dir)->exists())->toBeTrue();
})->with('safe builder names')->group('R18');
