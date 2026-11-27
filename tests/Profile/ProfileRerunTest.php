<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): rerun applies only the difference.
 * Requirements R9, R24. Acceptance criterion AC15.
 * Contract: tests/Profile/CONTRACT.md, section "Rerun".
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;

it('plans only the workflow (and the state that records it) when one option changes, then --check exits 0 (AC15)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => false]], ddev: true);

    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain(ProfileTestCase::WORKFLOW)
        ->and(array_values(array_diff($this->diffPaths($output), [ProfileTestCase::WORKFLOW, ProfileTestCase::STATE])))->toBe([])
        ->and($this->runLines($output))->toBe([])
        ->and(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeFalse();

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    expect($code)->toBe(0)
        ->and(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('writes only the difference: untouched files keep their bytes when one option changes', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => false]], ddev: true);
    $before = $this->snapshot($dir);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);
    $profileHash = sha1_file($dir.'/'.ProfileTestCase::PROFILE);
    $this->setupRun($dir, ['--yes' => true]);
    $after = $this->snapshot($dir);

    $changed = array_keys(array_diff_assoc($after, $before));
    sort($changed);

    expect(array_values(array_diff($changed, [ProfileTestCase::PROFILE, ProfileTestCase::WORKFLOW, ProfileTestCase::STATE])))->toBe([])
        ->and($changed)->toContain(ProfileTestCase::WORKFLOW)
        ->and(array_keys(array_diff_key($before, $after)))->toBe([])
        ->and(sha1_file($dir.'/'.ProfileTestCase::PROFILE))->toBe($profileHash);
});

it('plans the workflow away again when ci goes back to false, and deletes it on apply (AC15)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]], ddev: true);
    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => false]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain(ProfileTestCase::WORKFLOW);

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeFalse();
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

it('plans the runner files when the runner option changes, and no workflow (AC15)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['runner' => 'auto']], ddev: true);
    expect($this->boostServer($dir)['command'])->toBe('ddev');

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['runner' => 'host']]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Runner: host')
        ->and($this->diffPaths($output))->toContain('.mcp.json')
        ->not->toContain(ProfileTestCase::WORKFLOW);

    $this->setupRun($dir, ['--yes' => true]);

    expect($this->boostServer($dir))->toBe(['command' => 'php', 'args' => ['artisan', 'boost:mcp']]);
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

it('changes nothing when a tool rewrites the profile with the same meaning (R24)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true, 'monitoring' => 'none'], 'gate_tests' => 'locked'], ddev: true);
    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();

    // Another tool writes it again: keys reordered, managed_by added, compact JSON.
    file_put_contents($dir.'/'.ProfileTestCase::PROFILE, json_encode([
        'gate_tests' => 'locked',
        'managed_by' => ['tool' => 'team-tool', 'version' => '9.9.9'],
        'laravel' => ['monitoring' => 'none', 'ci' => true],
        'version' => 1,
    ]));

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('ignores options that need no change in the project: house_style and gate_tests', function () {
    $dir = $this->applied('app', ['version' => 1], ddev: true);

    $this->writeProfile($dir, ['version' => 1, 'gate_tests' => 'builder-written', 'laravel' => ['house_style' => false]]);
    expect(Profile::load($dir)->laravel()['house_style'])->toBeFalse();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('applies the profile to a Testbench package too', function () {
    $dir = $this->applied('package', ['version' => 1, 'laravel' => ['ci' => true]]);

    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});
