<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): profile validation.
 * Requirements R23, R24. Acceptance criteria AC13 to AC15 (refusal half).
 * Contract: tests/Profile/CONTRACT.md, sections "Validation" and "Exit codes".
 *
 * An invalid profile is refused: exit 1, output holds `Invalid profile .ai/skills-profile.json:`
 * and the dotted path of the offending field (list items by index: builders.0.command),
 * and nothing is written, with --check, with --yes and when declined alike.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;

dataset('invalid profiles', [
    'missing version' => [['laravel' => ['ci' => true]], 'version'],
    'version 2' => [['version' => 2], 'version'],
    'version as string' => [['version' => '1'], 'version'],
    'gate_tests not in the enum' => [['version' => 1, 'gate_tests' => 'maybe'], 'gate_tests'],
    'builders not a list' => [['version' => 1, 'builders' => 'local'], 'builders'],
    'builder without command' => [['version' => 1, 'builders' => [['name' => 'x']]], 'builders.0.command'],
    'builder without name' => [['version' => 1, 'builders' => [['command' => 'x']]], 'builders.0.name'],
    'builder timeout negative' => [['version' => 1, 'builders' => [['name' => 'x', 'command' => 'y', 'timeout_minutes' => -1]]], 'builders.0.timeout_minutes'],
    'builder timeout a string' => [['version' => 1, 'builders' => [['name' => 'x', 'command' => 'y', 'timeout_minutes' => 'soon']]], 'builders.0.timeout_minutes'],
    'managed_by not an object' => [['version' => 1, 'managed_by' => 'tool'], 'managed_by'],
    'setup not an object' => [['version' => 1, 'setup' => 'steps'], 'setup'],
    'setup.steps not a list' => [['version' => 1, 'setup' => ['steps' => 'make']], 'setup.steps'],
    'setup step without name' => [['version' => 1, 'setup' => ['steps' => [['command' => 'make']]]], 'setup.steps.0.name'],
    'setup step command not a string' => [['version' => 1, 'setup' => ['steps' => [['name' => 'a', 'command' => 7]]]], 'setup.steps.0.command'],
    'second setup step broken' => [['version' => 1, 'setup' => ['steps' => [['name' => 'a', 'command' => 'true'], ['name' => 'b']]]], 'setup.steps.1.command'],
    'laravel not an object' => [['version' => 1, 'laravel' => 'yes'], 'laravel'],
    'laravel a list' => [['version' => 1, 'laravel' => ['ci', 'true']], 'laravel'],
    'runner unknown' => [['version' => 1, 'laravel' => ['runner' => 'podman']], 'laravel.runner'],
    'runner not a string' => [['version' => 1, 'laravel' => ['runner' => true]], 'laravel.runner'],
    'house_style a string' => [['version' => 1, 'laravel' => ['house_style' => 'false']], 'laravel.house_style'],
    'house_style an integer' => [['version' => 1, 'laravel' => ['house_style' => 0]], 'laravel.house_style'],
    'house_style null' => [['version' => 1, 'laravel' => ['house_style' => null]], 'laravel.house_style'],
    'house_style an object' => [['version' => 1, 'laravel' => ['house_style' => ['on' => true]]], 'laravel.house_style'],
    'phpstan_level a string' => [['version' => 1, 'laravel' => ['phpstan_level' => '8']], 'laravel.phpstan_level'],
    'phpstan_level above 10' => [['version' => 1, 'laravel' => ['phpstan_level' => 11]], 'laravel.phpstan_level'],
    'phpstan_level negative' => [['version' => 1, 'laravel' => ['phpstan_level' => -1]], 'laravel.phpstan_level'],
    'phpstan_level a float' => [['version' => 1, 'laravel' => ['phpstan_level' => 7.5]], 'laravel.phpstan_level'],
    'monitoring unknown' => [['version' => 1, 'laravel' => ['monitoring' => 'datadog']], 'laravel.monitoring'],
    'monitoring a boolean' => [['version' => 1, 'laravel' => ['monitoring' => false]], 'laravel.monitoring'],
    'ci a string' => [['version' => 1, 'laravel' => ['ci' => 'yes']], 'laravel.ci'],
    'verdicts a list' => [['version' => 1, 'verdicts' => [['use' => 'avoid']]], 'verdicts'],
    'verdict not an object' => [['version' => 1, 'verdicts' => ['vendor/pkg' => 'avoid']], 'verdicts.vendor/pkg'],
    'verdict use unknown' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['use' => 'banned', 'reason' => 'x']]], 'verdicts.vendor/pkg.use'],
    'verdict without use' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['reason' => 'x']]], 'verdicts.vendor/pkg.use'],
    'verdict without reason' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['use' => 'avoid']]], 'verdicts.vendor/pkg.reason'],
    'verdict reason empty' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['use' => 'avoid', 'reason' => '']]], 'verdicts.vendor/pkg.reason'],
    'verdict conditions not a string' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['use' => 'avoid', 'reason' => 'x', 'conditions' => 3]]], 'verdicts.vendor/pkg.conditions'],
    'verdict checked not a date' => [['version' => 1, 'verdicts' => ['vendor/pkg' => ['use' => 'avoid', 'reason' => 'x', 'checked' => 'yesterday']]], 'verdicts.vendor/pkg.checked'],
]);

it('refuses an invalid profile, names the field and writes nothing (AC13 to AC15, validation)', function (array $profile, string $field) {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, $profile);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json')
            ->toContain($field)
            ->not->toContain('Applied')
            ->not->toContain('No changes')
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with('invalid profiles');

it('names only the offending field when one of several is wrong', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'house_style' => 'off', 'monitoring' => 'sentry']]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('laravel.house_style')
        ->not->toContain('laravel.ci')
        ->not->toContain('laravel.monitoring');
});

it('refuses a profile that is not JSON, or not a JSON object, and writes nothing', function (string $content) {
    $dir = $this->project('app');
    $this->writeProfile($dir, $content);
    $before = $this->snapshot($dir);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Invalid profile .ai/skills-profile.json')
        ->and($this->snapshot($dir))->toBe($before);
})->with([
    'broken JSON' => ['{"version": 1,'],
    'a JSON list' => ['[1]'],
    'a JSON string' => ['"profile"'],
    'empty file' => [''],
]);

it('throws a ProfileException naming the field from Profile::load', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'datadog']]);

    expect(fn () => Profile::load($dir))->toThrow(ProfileException::class, 'laravel.monitoring');
});

it('keeps and ignores unknown keys at every level (AD6, the shared schema), and never rewrites the profile', function () {
    $dir = $this->project('app');
    $content = json_encode([
        'version' => 1,
        'future_key' => ['kept' => true],
        'managed_by' => ['tool' => 'team-tool', 'version' => '0.3.0', 'extra' => 1],
        'craft' => ['answers' => ['dev_root' => '~/dev'], 'unknown' => 1],
        'laravel' => ['ci' => false, 'queue_driver' => 'redis'],
    ], JSON_PRETTY_PRINT)."\n";
    $this->writeProfile($dir, $content);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->not->toContain('Invalid profile')
        ->and(Profile::load($dir)->exists())->toBeTrue()
        ->and($this->read($dir, '.ai/skills-profile.json'))->toBe($content);
});

it('tells the developer about an unknown key inside the laravel section, so a typo is not silent', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['hosue_style' => false]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('Invalid profile')
        ->toContain('Ignoring unknown profile key: laravel.hosue_style')
        ->and(Profile::load($dir)->laravel()['house_style'])->toBeTrue();
});

it('accepts every documented laravel value', function (array $laravel) {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => $laravel]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('Invalid profile')
        ->and(Profile::load($dir)->laravel())->toMatchArray($laravel);
})->with([
    'runner ddev' => [['runner' => 'ddev']],
    'runner host' => [['runner' => 'host']],
    'house style off' => [['house_style' => false]],
    'phpstan 0' => [['phpstan_level' => 0]],
    'phpstan 10' => [['phpstan_level' => 10]],
    'monitoring sentry' => [['monitoring' => 'sentry']],
    'monitoring nightwatch' => [['monitoring' => 'nightwatch']],
    'ci on' => [['ci' => true]],
]);
