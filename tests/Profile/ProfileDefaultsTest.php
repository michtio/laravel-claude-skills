<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): no profile, the documented defaults.
 * Requirement R23 (last sentence). Acceptance criterion AC14.
 * Contract: tests/Profile/CONTRACT.md, section "Defaults".
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;

it('says it uses the defaults when there is no profile, and lists them (AC14)', function () {
    $dir = $this->project('app');

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('No profile found at .ai/skills-profile.json')
        ->toContain('using the defaults')
        ->toContain('runner: auto')
        ->toContain('house_style: true')
        ->toContain('phpstan_level: 8')
        ->not->toContain('env_schema')
        ->toContain('monitoring: none')
        ->toContain('ci: false');
});

it('states the defaults on every run, also when nothing changes', function () {
    $dir = $this->project('app');
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->toContain('No profile found at .ai/skills-profile.json')
        ->toContain('using the defaults');
});

it('never writes a profile file itself', function () {
    $dir = $this->project('app');

    $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, ProfileTestCase::PROFILE))->toBeNull();
});

it('does not say it uses the defaults when a profile exists, and names the file', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('Profile: .ai/skills-profile.json')
        ->not->toContain('No profile found')
        ->not->toContain('using the defaults');
});

it('plans no workflow, no monitoring package and no extra step by default', function () {
    $dir = $this->project('app');

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($this->diffPaths($output))->not->toContain(ProfileTestCase::WORKFLOW)
        ->and($this->runLines($output))->toBe([])
        ->and($output)->not->toContain('Extra step');
});

it('gives the documented defaults through Profile::load when the file is missing', function () {
    $dir = $this->project('app');

    $profile = Profile::load($dir);

    expect($profile->exists())->toBeFalse()
        ->and($profile->laravel())->toBe([
            'runner' => 'auto',
            'house_style' => true,
            'phpstan_level' => 8,
            'monitoring' => 'none',
            'ci' => false,
        ])
        ->and($profile->steps())->toBe([])
        ->and($profile->verdicts())->toBe([]);
});

it('lets profile options win over the defaults and keeps the defaults for the rest (R13 precedence of options)', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'phpstan_level' => 5]]);

    $profile = Profile::load($dir);

    expect($profile->exists())->toBeTrue()
        ->and($profile->laravel())->toBe([
            'runner' => 'auto',
            'house_style' => true,
            'phpstan_level' => 5,
            'monitoring' => 'none',
            'ci' => true,
        ]);
});

it('lets the profile runner win over detection, and auto follow detection', function () {
    $ddev = $this->project('app', ddev: true);
    $this->writeProfile($ddev, ['version' => 1, 'laravel' => ['runner' => 'host']]);

    [$code, $output] = $this->setupRun($ddev, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('Runner: host')
        ->and($this->boostServer($ddev))->toBe(['command' => 'php', 'args' => ['artisan', 'boost:mcp']]);

    $auto = $this->project('app', ddev: true);
    $this->writeProfile($auto, ['version' => 1, 'laravel' => ['runner' => 'auto']]);

    [, $autoOutput] = $this->setupRun($auto, ['--yes' => true]);

    expect($autoOutput)->toContain('Runner: ddev')
        ->and($this->boostServer($auto)['command'])->toBe('ddev');
});
