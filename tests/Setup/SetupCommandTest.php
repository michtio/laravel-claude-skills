<?php

declare(strict_types=1);

/**
 * Gate tests for slice S6a (laravel-layer): runner and MCP, plan-confirm-apply,
 * idempotence, app vs package detection.
 * Requirements R4, R8 (first bullet), R9, R10. Acceptance criteria AC5 (the
 * integration half is tests/gate/test_s6a.py), AC9 (first bullet), AC11, AC12.
 *
 * Pinned contract (see TestCase for provider, signature, runner and kind rules):
 *
 * Output lines (substring match):
 *   "Detected: app" | "Detected: package"      project kind
 *   "Runner: ddev" | "Runner: host"            runner
 *   "--- /dev/null" and "+++ b/<path>"         a created file, unified diff
 *   "--- a/<path>" and "+++ b/<path>"          a changed file
 *   "edited by hand: <path>"                   a file that differs from what setup wrote last
 *   "No changes"                               nothing to do (plan, apply and --check)
 * Confirmation: ONE confirm() question, exactly "Apply these changes?" (default no).
 * --yes skips it. --check never asks, never writes; exit 1 when anything would change, else 0.
 *
 * Files, app with DDEV:
 *   .mcp.json  mcpServers.laravel-boost = {command: ddev, args: [exec, php, artisan, boost:mcp]}
 *              other servers already in .mcp.json are preserved
 *   .ai/guidelines/claude-skills-runner.md  contains "ddev artisan", "ddev composer", "ddev npm"
 *   .ai/guidelines/boost/core.blade.php     Boost's override-by-path for its core guideline
 *              (GuidelineComposer: 'boost/core' resolves to .ai/guidelines/boost/core.blade.php),
 *              no host "php artisan"; not written without DDEV
 * Files, app on host:
 *   .mcp.json  {command: php, args: [artisan, boost:mcp]} (Boost's own default); no override file
 * Package (Testbench), the rule: the Boost entry runs testbench instead of artisan:
 *   host: {command: php, args: [vendor/bin/testbench, boost:mcp]}
 *   DDEV: {command: ddev, args: [exec, php, vendor/bin/testbench, boost:mcp]}
 *   DDEV runner guideline contains "ddev exec php vendor/bin/testbench" and "ddev composer",
 *   and not "ddev artisan" (a package has no artisan file).
 * CLAUDE.md is never edited, in any case.
 */

use Illuminate\Support\Facades\Artisan;

const RUNNER_GUIDELINE = '.ai/guidelines/claude-skills-runner.md';
const CORE_OVERRIDE = '.ai/guidelines/boost/core.blade.php';

/**
 * Run the command non-interactively and return the exit code.
 */
function runSetup(string $dir, array $options = []): int
{
    return Artisan::call('claude-skills:setup', ['--path' => $dir] + $options);
}

it('registers the claude-skills:setup command', function () {
    expect(array_keys(Artisan::all()))->toContain('claude-skills:setup');
});

it('sets up a DDEV app: MCP through ddev, runner guideline, core override, CLAUDE.md untouched', function () {
    $dir = $this->project('app', ddev: true);
    $claude = $this->read($dir, 'CLAUDE.md');

    expect(runSetup($dir, ['--yes' => true]))->toBe(0);

    expect($this->boostServer($dir))->toBe(['command' => 'ddev', 'args' => ['exec', 'php', 'artisan', 'boost:mcp']]);

    $guideline = $this->read($dir, RUNNER_GUIDELINE);
    expect($guideline)->not->toBeNull()
        ->toContain('ddev artisan')
        ->toContain('ddev composer')
        ->toContain('ddev npm');

    $override = $this->read($dir, CORE_OVERRIDE);
    expect($override)->not->toBeNull()
        ->not->toContain('php artisan')
        ->toContain('ddev artisan');

    expect($this->read($dir, 'CLAUDE.md'))->toBe($claude);
});

it('preserves other servers already in .mcp.json', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', json_encode(['mcpServers' => ['other' => ['command' => 'node', 'args' => ['x.js']]]]));

    runSetup($dir, ['--yes' => true]);

    $servers = json_decode($this->read($dir, '.mcp.json'), true)['mcpServers'];
    expect($servers['other'])->toBe(['command' => 'node', 'args' => ['x.js']])
        ->and($servers['laravel-boost']['command'])->toBe('ddev');
});

it('sets up a host app with Boost default command and no override', function () {
    $dir = $this->project('app');

    expect(runSetup($dir, ['--yes' => true]))->toBe(0);

    expect($this->boostServer($dir))->toBe(['command' => 'php', 'args' => ['artisan', 'boost:mcp']])
        ->and($this->read($dir, CORE_OVERRIDE))->toBeNull();
});

it('detects a Testbench package and points MCP at testbench on the host', function () {
    $dir = $this->project('package');

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('Detected: package')
        ->expectsOutputToContain('Runner: host')
        ->assertExitCode(0);

    expect($this->boostServer($dir))->toBe(['command' => 'php', 'args' => ['vendor/bin/testbench', 'boost:mcp']]);
});

it('runs a DDEV package through ddev exec php vendor/bin/testbench', function () {
    $dir = $this->project('package', ddev: true);
    $claude = $this->read($dir, 'CLAUDE.md');

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('Detected: package')
        ->expectsOutputToContain('Runner: ddev')
        ->assertExitCode(0);

    expect($this->boostServer($dir))->toBe(['command' => 'ddev', 'args' => ['exec', 'php', 'vendor/bin/testbench', 'boost:mcp']]);

    $guideline = $this->read($dir, RUNNER_GUIDELINE);
    expect($guideline)->toContain('ddev exec php vendor/bin/testbench')
        ->toContain('ddev composer')
        ->not->toContain('ddev artisan');
    expect($this->read($dir, 'CLAUDE.md'))->toBe($claude);
});

it('detects a plain app as an app', function () {
    $dir = $this->project('app', ddev: true);

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--check' => true])
        ->expectsOutputToContain('Detected: app')
        ->expectsOutputToContain('Runner: ddev')
        ->assertExitCode(1);
});

it('treats testbench without a workbench directory as an app, not a package', function () {
    $dir = $this->project('package');
    unlink($dir.'/workbench/.gitkeep');
    rmdir($dir.'/workbench');

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--check' => true])
        ->expectsOutputToContain('Detected: app');
});

it('prints a diff for every file and writes nothing when the confirmation is declined', function () {
    $dir = $this->project('app', ddev: true);
    $before = $this->snapshot($dir);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('--- /dev/null')
        ->expectsOutputToContain('+++ b/.mcp.json')
        ->expectsOutputToContain('+++ b/'.RUNNER_GUIDELINE)
        ->expectsOutputToContain('+++ b/'.CORE_OVERRIDE)
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->snapshot($dir))->toBe($before);
});

it('applies when the single confirmation is answered yes', function () {
    $dir = $this->project('app', ddev: true);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'yes')
        ->assertExitCode(0);

    expect($this->boostServer($dir))->not->toBeNull()
        ->and($this->read($dir, RUNNER_GUIDELINE))->not->toBeNull();
});

it('--check exits 1 and writes nothing on a fresh project', function () {
    $dir = $this->project('app', ddev: true);
    $before = $this->snapshot($dir);

    expect(runSetup($dir, ['--check' => true]))->toBe(1)
        ->and($this->snapshot($dir))->toBe($before);
});

it('is idempotent: the second run reports no changes and --check exits 0', function (string $fixture, bool $ddev) {
    $dir = $this->project($fixture, ddev: $ddev);
    runSetup($dir, ['--yes' => true]);
    $after = $this->snapshot($dir);

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('No changes')
        ->assertExitCode(0);
    $this->artisan('claude-skills:setup', ['--path' => $dir, '--check' => true])
        ->expectsOutputToContain('No changes')
        ->assertExitCode(0);

    expect($this->snapshot($dir))->toBe($after);
})->with([
    'ddev app' => ['app', true],
    'host app' => ['app', false],
    'ddev package' => ['package', true],
    'host package' => ['package', false],
]);

it('--check exits 1 after a hand edit of the runner guideline', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    file_put_contents($dir.'/'.RUNNER_GUIDELINE, $this->read($dir, RUNNER_GUIDELINE)."\n- Project note added by hand.\n");

    expect(runSetup($dir, ['--check' => true]))->toBe(1);
});

it('shows the diff for a hand-edited guideline, asks, and keeps the edit on no', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    $edited = $this->read($dir, RUNNER_GUIDELINE)."\n- Project note added by hand.\n";
    file_put_contents($dir.'/'.RUNNER_GUIDELINE, $edited);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: '.RUNNER_GUIDELINE)
        ->expectsOutputToContain('--- a/'.RUNNER_GUIDELINE)
        ->expectsOutputToContain('+++ b/'.RUNNER_GUIDELINE)
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, RUNNER_GUIDELINE))->toBe($edited);
});

it('shows the diff for a hand-edited .mcp.json Boost entry, asks, and keeps the edit on no', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    $edited = json_encode(['mcpServers' => ['laravel-boost' => ['command' => 'my-wrapper', 'args' => ['boost']]]], JSON_PRETTY_PRINT);
    file_put_contents($dir.'/.mcp.json', $edited);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: .mcp.json')
        ->expectsOutputToContain('+++ b/.mcp.json')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, '.mcp.json'))->toBe($edited);
});

it('overwrites a hand-edited file only after the confirmation is yes', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    file_put_contents($dir.'/'.RUNNER_GUIDELINE, "hand written\n");

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'yes')
        ->assertExitCode(0);

    expect($this->read($dir, RUNNER_GUIDELINE))->toContain('ddev artisan')->not->toContain('hand written');
});
