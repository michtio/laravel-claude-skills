<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): CLAUDE.md exists before Boost runs.
 * Requirements R4, R8. Skills-gaps row 3.
 * Contract: tests/S9b/CONTRACT.md section 5.
 *
 * Boost 2.10.4 writes its guidelines to AGENTS.md when CLAUDE.md does not exist, so on a fresh
 * repo the runner guideline, the core override and the house style landed in the wrong file.
 * The setup creates an empty CLAUDE.md once, when Claude Code is the agent and the file is
 * missing. It never edits a CLAUDE.md that exists (R4), whoever wrote it.
 */

/**
 * Remove CLAUDE.md from a temp copy of a fixture.
 */
function s9bWithoutClaudeMd(string $dir): void
{
    unlink($dir.'/CLAUDE.md');
}

it('plans an empty CLAUDE.md for a project that has none, as a created file', function (string $fixture) {
    $dir = $this->project($fixture);
    s9bWithoutClaudeMd($dir);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('--- /dev/null')
        ->toContain('+++ b/CLAUDE.md')
        ->and(file_exists($dir.'/CLAUDE.md'))->toBeFalse();
})->with(['app', 'package']);

it('creates it empty on apply, so Boost finds it and writes there', function (string $fixture) {
    $dir = $this->project($fixture);
    s9bWithoutClaudeMd($dir);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(file_exists($dir.'/CLAUDE.md'))->toBeTrue()
        ->and(trim((string) file_get_contents($dir.'/CLAUDE.md')))->toBe('')
        ->and(file_exists($dir.'/AGENTS.md'))->toBeFalse();
})->with(['app', 'package']);

it('does not create it when the person declines the plan', function () {
    $dir = $this->project('app');
    s9bWithoutClaudeMd($dir);
    expect($this->setupRun($dir, ['--check' => true])[1])->toContain('+++ b/CLAUDE.md');

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect(file_exists($dir.'/CLAUDE.md'))->toBeFalse();
});

it('never touches a CLAUDE.md that exists and does not list it in the plan', function () {
    $dir = $this->project('app');
    $claude = $this->read($dir, 'CLAUDE.md');

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, 'CLAUDE.md'))->toBe($claude)
        ->and($output)->not->toContain('b/CLAUDE.md');
});

it('leaves what Boost wrote into it alone: byte for byte, No changes, exit 0', function () {
    $dir = $this->project('app');
    s9bWithoutClaudeMd($dir);
    $this->setupRun($dir, ['--yes' => true]);
    expect(file_exists($dir.'/CLAUDE.md'))->toBeTrue();
    $boost = "<laravel-boost-guidelines>\n=== foundation rules ===\nPHP 8.4\n</laravel-boost-guidelines>\n";
    file_put_contents($dir.'/CLAUDE.md', $boost);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($this->read($dir, 'CLAUDE.md'))->toBe($boost);
});

it('creates it when boost.json is missing, and when it lists claude_code', function (?array $boost) {
    $dir = $this->project('app');
    s9bWithoutClaudeMd($dir);
    unlink($dir.'/boost.json');

    if ($boost !== null) {
        file_put_contents($dir.'/boost.json', json_encode($boost));
    }

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/CLAUDE.md'))->toBeTrue();
})->with([
    'no boost.json' => [null],
    'claude_code among others' => [['agents' => ['cursor', 'claude_code']]],
]);

it('does not create it when boost.json lists agents without claude_code', function () {
    $dir = $this->project('app');
    s9bWithoutClaudeMd($dir);
    file_put_contents($dir.'/boost.json', json_encode(['agents' => ['cursor']]));

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/CLAUDE.md'))->toBeFalse()
        ->and($output)->not->toContain('b/CLAUDE.md');
});

it('creates it and warns by name when AGENTS.md exists without CLAUDE.md', function () {
    $dir = $this->project('app');
    s9bWithoutClaudeMd($dir);
    file_put_contents($dir.'/AGENTS.md', "# Agents\n");

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(file_exists($dir.'/CLAUDE.md'))->toBeTrue()
        ->and($this->read($dir, 'AGENTS.md'))->toBe("# Agents\n")
        ->and($output)->toContain('AGENTS.md')
        ->toContain('CLAUDE.md');
});
