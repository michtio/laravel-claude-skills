<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): extra setup steps and the monitoring option.
 * Requirements R23 (extra steps, monitoring), R24. Acceptance criteria AC13, AC15.
 * Contract: tests/Profile/CONTRACT.md, sections "Extra steps" and "Monitoring".
 *
 * Steps are `sh -c <command>` with the project root as working directory, shown as
 * "Extra step: <name>" then "Run: <command>", run after every file write and after every
 * other action, in profile order. A step that ran is recorded; a rerun plans only steps
 * that are new or whose name or command changed.
 *
 * Monitoring never runs composer in these tests: a plan is read with --check, or the
 * package is already in composer.json.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;

/**
 * Two steps that log to steps.log; the second also checks the generated files exist.
 *
 * @return array<string, mixed>
 */
function twoSteps(): array
{
    return [
        'version' => 1,
        'setup' => ['steps' => [
            ['name' => 'first', 'command' => 'echo first >> steps.log'],
            ['name' => 'second', 'command' => 'test -f composer.json && grep -q "\"test\"" composer.json && test -f .githooks/commit-msg && echo second >> steps.log'],
        ]],
    ];
}

it('shows the steps in the plan, in order, after everything else, and runs none on --check (AC13)', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, twoSteps());

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Extra step: first')
        ->toContain('Extra step: second')
        ->and(strpos($output, 'Extra step: first'))->toBeLessThan(strpos($output, 'Extra step: second'))
        ->and($this->runLines($output))->toBe(['echo first >> steps.log', 'test -f composer.json && grep -q "\"test\"" composer.json && test -f .githooks/commit-msg && echo second >> steps.log'])
        ->and(file_exists($dir.'/steps.log'))->toBeFalse();

    // Last: every file diff of the plan comes before the first step.
    $lastDiff = strrpos($output, '+++ b/');
    expect(strpos($output, 'Extra step: first'))->toBeGreaterThan($lastDiff);
});

it('runs no step when the confirmation is declined', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, twoSteps());

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('Extra step: first')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect(file_exists($dir.'/steps.log'))->toBeFalse()
        ->and($this->read($dir, '.mcp.json'))->toBeNull();
});

it('runs the steps last, in order, once files exist, from the project root (AC13)', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, twoSteps());

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($this->read($dir, 'steps.log'))->toBe("first\nsecond\n")
        ->and($output)->toContain('Ran echo first >> steps.log')
        ->toContain('Applied');

    // Every file is written (and reported) before the first step runs.
    expect(strpos($output, 'Ran echo first >> steps.log'))->toBeGreaterThan(strrpos($output, 'Created '));
});

it('runs a step after the other actions of the plan', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'sentry'], 'setup' => ['steps' => [['name' => 'team', 'command' => 'echo team >> steps.log']]]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);
    $runs = $this->runLines($output);

    expect($runs)->not->toBeEmpty()
        ->and(end($runs))->toBe('echo team >> steps.log')
        ->and($runs[0])->toMatch('/^ddev composer require sentry\/sentry-laravel\b/');
});

it('does not rerun a step that ran: the second run reports no changes (R24)', function () {
    $dir = $this->applied('app', twoSteps(), ddev: true);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($this->read($dir, 'steps.log'))->toBe("first\nsecond\n");
});

it('plans only a new step, and runs only that one (AC15)', function () {
    $dir = $this->applied('app', twoSteps(), ddev: true);
    $profile = twoSteps();
    $profile['setup']['steps'][] = ['name' => 'third', 'command' => 'echo third >> steps.log'];
    $this->writeProfile($dir, $profile);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->runLines($output))->toBe(['echo third >> steps.log'])
        ->and(array_values(array_diff($this->diffPaths($output), [ProfileTestCase::STATE])))->toBe([]);

    $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, 'steps.log'))->toBe("first\nsecond\nthird\n");
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

it('reruns only the step whose command changed (AC15)', function () {
    $dir = $this->applied('app', twoSteps(), ddev: true);
    $profile = twoSteps();
    $profile['setup']['steps'][0]['command'] = 'echo first-again >> steps.log';
    $this->writeProfile($dir, $profile);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('Ran echo first-again >> steps.log')
        ->and($this->read($dir, 'steps.log'))->toBe("first\nsecond\nfirst-again\n");
});

it('fails the run when a step fails, keeps the files, skips the later steps and plans the step again (AC15)', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'setup' => ['steps' => [
        ['name' => 'breaks', 'command' => 'exit 3'],
        ['name' => 'after', 'command' => 'echo after >> steps.log'],
    ]]]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('`exit 3` failed')
        ->and(file_exists($dir.'/steps.log'))->toBeFalse()
        ->and($this->boostServer($dir))->not->toBeNull();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->runLines($output))->toBe(['exit 3', 'echo after >> steps.log']);
});

it('plans no monitoring package with monitoring none, and keeps none out of composer.json (AC13)', function () {
    $dir = $this->project('app', ddev: true);
    $require = json_decode($this->read($dir, 'composer.json'), true)['require'];
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'none'], 'setup' => ['steps' => [['name' => 'team', 'command' => 'echo team >> steps.log']]]]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($this->runLines($output))->each->not->toMatch('/sentry|nightwatch|composer require/i')
        ->and(json_decode($this->read($dir, 'composer.json'), true)['require'])->toBe($require)
        ->and($this->read($dir, 'steps.log'))->toBe("team\n");
});

it('plans the monitoring package the profile names, through the runner', function (string $monitoring, string $package, bool $ddev, string $expected) {
    $dir = $this->project('app', ddev: $ddev);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => $monitoring]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->runLines($output))->toBe([$expected]);
})->with([
    'sentry on ddev' => ['sentry', 'sentry/sentry-laravel', true, 'ddev composer require sentry/sentry-laravel'],
    'sentry on host' => ['sentry', 'sentry/sentry-laravel', false, 'composer require sentry/sentry-laravel'],
    'nightwatch on ddev' => ['nightwatch', 'laravel/nightwatch', true, 'ddev composer require laravel/nightwatch'],
    'nightwatch on host' => ['nightwatch', 'laravel/nightwatch', false, 'composer require laravel/nightwatch'],
]);

it('plans no monitoring install when the package is already required (idempotent)', function (string $monitoring, string $package, string $section) {
    $dir = $this->project('app', ddev: true);
    $composer = json_decode($this->read($dir, 'composer.json'), true);
    $composer[$section][$package] = '^1.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => $monitoring]]);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($this->runLines($output))->toBe([]);

    // The same project without the package would plan the install, so the silence above is the idempotence.
    unset($composer[$section][$package]);
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->runLines($output))->toBe(['ddev composer require '.$package]);
})->with([
    'sentry in require' => ['sentry', 'sentry/sentry-laravel', 'require'],
    'nightwatch in require' => ['nightwatch', 'laravel/nightwatch', 'require'],
    'sentry in require-dev' => ['sentry', 'sentry/sentry-laravel', 'require-dev'],
]);

it('never plans to remove a monitoring package when the profile goes back to none', function () {
    $dir = $this->project('app', ddev: true);
    $composer = json_decode($this->read($dir, 'composer.json'), true);
    $composer['require']['sentry/sentry-laravel'] = '^4.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'none']]);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and(Profile::load($dir)->laravel()['monitoring'])->toBe('none')
        ->and($this->runLines($output))->toBe([])
        ->and(json_decode($this->read($dir, 'composer.json'), true)['require'])->toHaveKey('sentry/sentry-laravel');
});

it('plans no monitoring package for a Testbench package, whatever the profile says', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'sentry']]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(Profile::load($dir)->laravel()['monitoring'])->toBe('sentry')
        ->and($this->runLines($output))->toBe([]);
});
