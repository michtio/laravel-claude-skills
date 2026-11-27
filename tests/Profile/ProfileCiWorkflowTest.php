<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): the CI workflow the setup can write.
 * Requirement R11. Acceptance criterion AC32.
 * Contract: tests/Profile/CONTRACT.md, section "CI workflow".
 *
 * With "laravel": {"ci": true} the setup owns .github/workflows/claude-skills-gate.yml:
 * written, hand-edit detected, updated and removed like any other owned file.
 *
 * Action majors, verified 2026-11-27 with `gh api repos/<owner>/<action>/releases/latest`
 * and the `using:` line of action.yml at the tag (and at the major tag the workflow pins):
 *
 *   actions/checkout          latest v7.0.1   major tag v7 -> v7.0.1 (same commit)   runs: node24
 *   shivammathur/setup-php    latest 2.40.0   major tag v2                           runs: node24
 *   actions/cache             latest v6.1.0   major tag v6 -> v6.1.0 (same commit)   runs: node24
 *
 * Every `uses:` of the workflow must be one of these, pinned to exactly this major.
 * A new latest major means the builder re-verifies and updates this table with the gate writer.
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

const ACTION_MAJORS = [
    'actions/checkout' => 'v7',
    'shivammathur/setup-php' => 'v2',
    'actions/cache' => 'v6',
];

/**
 * Parse the written workflow.
 *
 * @return array<string, mixed>
 */
function workflow(string $dir): array
{
    $content = file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW);

    return Yaml::parse((string) $content);
}

/**
 * All steps of all jobs.
 *
 * @param array<string, mixed> $workflow
 * @return list<array<string, mixed>>
 */
function workflowSteps(array $workflow): array
{
    $steps = [];

    foreach ($workflow['jobs'] as $job) {
        foreach ($job['steps'] as $step) {
            $steps[] = $step;
        }
    }

    return $steps;
}

it('writes the workflow when ci is true, and shows it in the plan first (AC32)', function (string $fixture, bool $ddev) {
    $dir = $this->project($fixture, ddev: $ddev);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('--- /dev/null')
        ->toContain('+++ b/.github/workflows/claude-skills-gate.yml')
        ->and(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeFalse();

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();
})->with([
    'ddev app' => ['app', true],
    'host app' => ['app', false],
    'host package' => ['package', false],
]);

it('does not write a workflow without ci, or with ci false', function (array $profile) {
    $dir = $this->project('app');
    $this->writeProfile($dir, $profile);

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/.github'))->toBeFalse();
})->with([
    'no laravel section' => [['version' => 1]],
    'ci false' => [['version' => 1, 'laravel' => ['ci' => false]]],
]);

it('calls the same gate command as the local gate: composer test, after composer install (AC32)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $workflow = workflow($dir);
    $composer = json_decode($this->read($dir, 'composer.json'), true);

    $commands = [];
    foreach (workflowSteps($workflow) as $step) {
        foreach (preg_split('/\R/', trim((string) ($step['run'] ?? ''))) ?: [] as $line) {
            if (trim($line) !== '') {
                $commands[] = trim($line);
            }
        }
    }

    expect($composer['scripts'])->toHaveKey('test')
        ->and($commands)->toContain('composer test')
        ->and(array_count_values($commands)['composer test'])->toBe(1);

    $install = null;
    foreach ($commands as $position => $command) {
        if (str_starts_with($command, 'composer install')) {
            $install = $position;
        }
    }

    expect($install)->not->toBeNull()
        ->and($install)->toBeLessThan(array_search('composer test', $commands, true));
});

it('runs no gate step on its own: no direct pint, phpstan, pest or phpunit (one gate command)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);

    foreach (workflowSteps(workflow($dir)) as $step) {
        expect((string) ($step['run'] ?? ''))->not->toMatch('#\b(pint|phpstan|pest|phpunit|artisan test)\b#');
    }
});

it('uses only actions on their latest major, each pinned to that major tag (AC32)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $used = [];

    foreach (workflowSteps(workflow($dir)) as $step) {
        if (isset($step['uses'])) {
            $used[] = $step['uses'];
        }
    }

    expect($used)->not->toBeEmpty();

    foreach ($used as $uses) {
        expect($uses)->toMatch('#^[\w.-]+/[\w.-]+@v\d+$#');
        [$action, $ref] = explode('@', $uses);
        expect(ACTION_MAJORS)->toHaveKey($action)
            ->and($ref)->toBe(ACTION_MAJORS[$action]);
    }

    $actions = array_map(static fn (string $uses): string => explode('@', $uses)[0], $used);

    expect($actions)->toContain('actions/checkout')
        ->toContain('shivammathur/setup-php');
});

it('runs on push and pull_request with read-only contents permission', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $workflow = workflow($dir);
    $on = $workflow['on'] ?? $workflow[true] ?? [];

    expect(array_keys((array) $on))->toContain('push')
        ->toContain('pull_request')
        ->and($workflow['permissions'] ?? null)->toBe(['contents' => 'read']);

    foreach ($workflow['jobs'] as $job) {
        expect($job['runs-on'])->toBe('ubuntu-latest');
    }
});

it('sets up PHP from a php-version key', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);

    $php = null;
    foreach (workflowSteps(workflow($dir)) as $step) {
        if (str_starts_with((string) ($step['uses'] ?? ''), 'shivammathur/setup-php@')) {
            $php = $step['with']['php-version'] ?? null;
        }
    }

    expect($php)->not->toBeNull()
        ->and((string) $php)->toMatch('/^\d+\.\d+$/');
});

it('flags a hand-edited workflow, shows the diff and does not overwrite it silently', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $path = $dir.'/'.ProfileTestCase::WORKFLOW;
    file_put_contents($path, file_get_contents($path)."# a team note\n");

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: '.ProfileTestCase::WORKFLOW)
        ->and(file_get_contents($path))->toContain('# a team note');
});

it('does not touch a hand-edited workflow when the confirmation is declined', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $path = $dir.'/'.ProfileTestCase::WORKFLOW;
    $edited = file_get_contents($path)."# a team note\n";
    file_put_contents($path, $edited);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: '.ProfileTestCase::WORKFLOW)
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect(file_get_contents($path))->toBe($edited);
});

it('is idempotent: a second run reports no changes', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    expect(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeTrue();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});
