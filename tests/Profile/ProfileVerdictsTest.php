<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): verdict merge and profile precedence.
 * Requirement R13 (a profile's verdicts take precedence over the package's own), AD6.
 * Acceptance criterion AC13 (the override wins in the merged verdicts).
 * Contract: tests/Profile/CONTRACT.md, section "Verdicts".
 *
 * Michtio\LaravelClaudeSkills\Profile\Verdicts:
 *   register(): array   the package's own register, parsed from
 *                       resources/boost/skills/laravel-package-verdicts/references/register.md:
 *                       package name (no backticks) => [use, reason, conditions, checked] (strings).
 *   merged(string $root): array   the register with the verdicts of <root>/.ai/skills-profile.json
 *                       merged over it by package name: a profile entry REPLACES the register row
 *                       (a missing conditions or checked is ''), a package only in the profile
 *                       is added. Throws ProfileException on an invalid profile.
 */

use Michtio\LaravelClaudeSkills\Profile\ProfileException;
use Michtio\LaravelClaudeSkills\Profile\Verdicts;

const REGISTER = __DIR__.'/../../resources/boost/skills/laravel-package-verdicts/references/register.md';

it('parses the whole register: every row, with the five fields (R13)', function () {
    $rows = array_values(array_filter(
        file(REGISTER, FILE_IGNORE_NEW_LINES) ?: [],
        static fn (string $line): bool => str_starts_with($line, '| `'),
    ));

    $register = Verdicts::register();

    expect($rows)->not->toBeEmpty()
        ->and($register)->toHaveCount(count($rows));

    foreach ($register as $package => $verdict) {
        expect($package)->toMatch('#^[a-z0-9._-]+/[a-z0-9._-]+$#')
            ->and(array_keys($verdict))->toBe(['use', 'reason', 'conditions', 'checked'])
            ->and($verdict['use'])->toBeIn(['use', 'avoid', 'depends'])
            ->and($verdict['reason'])->not->toBe('')
            ->and($verdict['checked'])->toMatch('/^\d{4}-\d{2}-\d{2}$/');
    }

    expect($register['laravel/sanctum']['use'])->toBe('use')
        ->and($register['laravel/passport']['use'])->toBe('depends')
        ->and($register['laravel/sanctum']['checked'])->toBe('2026-11-27');
});

it('returns the register unchanged when there is no profile, or no verdicts in it', function () {
    $dir = $this->project('app');

    expect(Verdicts::merged($dir))->toBe(Verdicts::register());

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    expect(Verdicts::merged($dir))->toBe(Verdicts::register());
});

it('lets a profile verdict win over the register row for that package, and leaves every other row alone (R13, AC13)', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'verdicts' => [
        'laravel/sanctum' => ['use' => 'avoid', 'reason' => 'We run OAuth only.', 'conditions' => 'Use laravel/passport.', 'checked' => '2026-12-01'],
    ]]);
    $register = Verdicts::register();

    $merged = Verdicts::merged($dir);

    expect($merged['laravel/sanctum'])->toBe(['use' => 'avoid', 'reason' => 'We run OAuth only.', 'conditions' => 'Use laravel/passport.', 'checked' => '2026-12-01'])
        ->and($register['laravel/sanctum']['use'])->toBe('use')
        ->and($merged)->toHaveCount(count($register));

    unset($merged['laravel/sanctum'], $register['laravel/sanctum']);

    expect($merged)->toBe($register);
});

it('replaces the whole row: fields the profile entry leaves out are empty, not inherited', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'verdicts' => ['laravel/sanctum' => ['use' => 'depends', 'reason' => 'Ruled by the team.']]]);

    expect(Verdicts::merged($dir)['laravel/sanctum'])->toBe(['use' => 'depends', 'reason' => 'Ruled by the team.', 'conditions' => '', 'checked' => '']);
});

it('adds a package that only the profile knows', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'verdicts' => ['acme/internal-kit' => ['use' => 'use', 'reason' => 'Our shared kit.', 'checked' => '2026-12-01']]]);

    $merged = Verdicts::merged($dir);

    expect($merged)->toHaveCount(count(Verdicts::register()) + 1)
        ->and($merged['acme/internal-kit'])->toBe(['use' => 'use', 'reason' => 'Our shared kit.', 'conditions' => '', 'checked' => '2026-12-01']);
});

it('applies an override and an addition together, the way AC13 runs them', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, [
        'version' => 1,
        'laravel' => ['monitoring' => 'none'],
        'setup' => ['steps' => [['name' => 'team', 'command' => 'true']]],
        'verdicts' => ['maatwebsite/excel' => ['use' => 'avoid', 'reason' => 'We stream exports.', 'conditions' => 'Use openspout/openspout.', 'checked' => '2026-11-27']],
    ]);

    $merged = Verdicts::merged($dir);

    expect($merged['maatwebsite/excel']['use'])->toBe('avoid')
        ->and(Verdicts::register()['maatwebsite/excel']['use'])->toBe('depends')
        ->and($merged['openspout/openspout'])->toBe(Verdicts::register()['openspout/openspout']);
});

it('refuses to merge an invalid profile, naming the field', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'verdicts' => ['laravel/sanctum' => ['use' => 'banned', 'reason' => 'x']]]);

    expect(fn () => Verdicts::merged($dir))->toThrow(ProfileException::class, 'verdicts.laravel/sanctum.use');
});

it('changes nothing in the setup plan when only a verdict changes: verdicts are read, not written', function () {
    $dir = $this->applied('app', ['version' => 1], ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'verdicts' => ['laravel/sanctum' => ['use' => 'avoid', 'reason' => 'x']]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and(Verdicts::merged($dir)['laravel/sanctum']['use'])->toBe('avoid');
});
