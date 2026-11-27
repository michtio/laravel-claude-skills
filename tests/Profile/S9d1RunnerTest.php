<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9d-1 (laravel-layer): the runner guideline, the core override and testbench.yaml.
 * Requirements R4, R8, R9. Skills-gaps rows 5, 14, 15.
 * Contract: tests/S9d1/CONTRACT.md sections 1 to 3.
 */

use Symfony\Component\Yaml\Yaml;

const S9D1_RUNNER = '.ai/guidelines/claude-skills-runner.md';

const S9D1_CORE = '.ai/guidelines/boost/core.blade.php';

/**
 * A DDEV project whose type is not laravel, so artisan runs as `ddev exec php artisan`.
 */
function s9d1DdevPhpType(string $dir): void
{
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\n");
}

/**
 * Every `ddev exec ...` command in the text that runs tinker with --execute but is not a raw exec.
 * `ddev exec` joins its arguments into one double-quoted `bash -c` string, so a `$` in the code is
 * expanded by the container shell; `ddev exec --raw -- ...` passes the arguments as they are.
 *
 * @return list<string>
 */
function s9d1BrokenTinker(string $text): array
{
    preg_match_all('/ddev exec (?!--raw\b)[^`\n]*\btinker\b[^`\n]*--execute/', $text, $matches);

    return $matches[0];
}

// 1. Tinker under DDEV (row 5)
// =========================================================================

it('gives a tinker form in the DDEV runner guideline that survives ddev exec', function (string $fixture, bool $phpType) {
    $dir = $this->project($fixture, ddev: true);
    if ($phpType) {
        s9d1DdevPhpType($dir);
    }

    $this->setupRun($dir, ['--yes' => true]);
    $guideline = (string) $this->read($dir, S9D1_RUNNER);
    $tinker = array_values(array_filter(preg_split('/\R/', $guideline) ?: [], static fn (string $line): bool => stripos($line, 'tinker') !== false));

    expect($tinker)->not->toBe([], 'the DDEV runner guideline has a tinker line')
        ->and(s9d1BrokenTinker($guideline))->toBe([])
        ->and(implode("\n", $tinker))->toMatch('/--raw --|tinker </');
})->with([
    'package on DDEV' => ['package', false],
    'app on a non-laravel DDEV type' => ['app', true],
]);

it('points to Boost\'s tinker MCP tool first in the DDEV runner guideline', function () {
    $dir = $this->project('package', ddev: true);

    $this->setupRun($dir, ['--yes' => true]);
    $guideline = (string) $this->read($dir, S9D1_RUNNER);

    expect($guideline)->toMatch('/`tinker`[^\n]*(MCP|tool)|(MCP|tool)[^\n]*`tinker`/i');
});

it('carries no plain ddev exec tinker --execute in the core override', function (string $fixture, bool $phpType) {
    $dir = $this->project($fixture, ddev: true);
    if ($phpType) {
        s9d1DdevPhpType($dir);
    }

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $override = (string) $this->read($dir, S9D1_CORE);

    expect($code)->toBe(0)
        ->and($override)->toContain('tinker')
        ->and(s9d1BrokenTinker($override))->toBe([]);
})->with([
    'package on DDEV' => ['package', false],
    'app on a non-laravel DDEV type' => ['app', true],
]);

it('keeps ddev artisan tinker --execute for a laravel-type DDEV app (ddev artisan passes its arguments raw)', function () {
    $dir = $this->project('app', ddev: true);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9d1BrokenTinker((string) $this->read($dir, S9D1_RUNNER)))->toBe([])
        ->and(s9d1BrokenTinker((string) $this->read($dir, S9D1_CORE)))->toBe([]);
});

// 2. The package runner guideline (row 15)
// =========================================================================

it('says in the package runner guideline that classes go under src/ with the composer namespace', function (bool $ddev) {
    $dir = $this->project('package', ddev: $ddev);

    $this->setupRun($dir, ['--yes' => true]);
    $guideline = (string) $this->read($dir, S9D1_RUNNER);

    expect($guideline)->toMatch('/^.*src\/.*Example\\\\Package\\\\.*$|^.*Example\\\\Package\\\\.*src\/.*$/m')
        ->toMatch('/Laravel package/');
})->with(['host' => [false], 'DDEV' => [true]]);

it('says in the package runner guideline that make: generators do not write into src/', function (bool $ddev) {
    $dir = $this->project('package', ddev: $ddev);

    $this->setupRun($dir, ['--yes' => true]);

    expect((string) $this->read($dir, S9D1_RUNNER))->toMatch('/^.*\bmake:.*\bsrc\/.*$/m');
})->with(['host' => [false], 'DDEV' => [true]]);

it('runs a package\'s tests with vendor/bin/pest in the runner form, instead of artisan test', function (bool $ddev, string $pest) {
    $dir = $this->project('package', ddev: $ddev);

    $this->setupRun($dir, ['--yes' => true]);
    $guideline = (string) $this->read($dir, S9D1_RUNNER);
    $line = collect(preg_split('/\R/', $guideline) ?: [])->first(static fn (string $l): bool => str_contains($l, 'artisan test'));

    expect($line)->not->toBeNull('a line of the package guideline replaces `php artisan test`')
        ->and($line)->toContain($pest)
        ->and($guideline)->not->toContain('test --compact');
})->with([
    'host' => [false, '`vendor/bin/pest'],
    'DDEV' => [true, '`ddev exec vendor/bin/pest'],
]);

// 3. testbench.yaml is edited as text (row 14)
// =========================================================================

/**
 * What `testbench workbench:install --basic --devtool` writes (orchestra/workbench v11.3.0,
 * src/Console/stubs/testbench.yaml), placeholders filled in.
 */
function s9d1WorkbenchYaml(): string
{
    return implode("\n", [
        "laravel: '@testbench'",
        '',
        'providers:',
        '  # - Workbench\App\Providers\WorkbenchServiceProvider',
        '',
        'migrations:',
        '  - workbench/database/migrations',
        '',
        'seeders:',
        '  - Workbench\Database\Seeders\DatabaseSeeder',
        '',
        'workbench:',
        "  start: '/'",
        '  install: true',
        '  health: false',
        '  discovers:',
        '    web: true',
        '    api: true',
        '    commands: true',
        '    components: false',
        '    factories: true',
        '    views: false',
        '  build:',
        '    - asset-publish',
        '    - create-sqlite-db',
        '    - db-wipe',
        '    - migrate-fresh',
        '  assets:',
        '    - laravel-assets',
        '  sync:',
        '    - from: storage',
        '      to: workbench/storage',
        '      reverse: true',
    ])."\n";
}

it('keeps every line of testbench.yaml it does not own, comments and blank lines included, in order', function () {
    $dir = $this->project('package');
    $original = s9d1WorkbenchYaml();
    file_put_contents($dir.'/testbench.yaml', $original);

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $after = (string) $this->read($dir, 'testbench.yaml');
    $afterLines = preg_split('/\R/', $after) ?: [];

    expect($code)->toBe(0)
        ->and($after)->not->toContain('providers: null')
        ->toContain('  # - Workbench\App\Providers\WorkbenchServiceProvider');

    // Every original line except the owned `laravel:` line appears unchanged, in the same order.
    $position = -1;
    foreach (preg_split('/\R/', rtrim($original, "\n")) ?: [] as $line) {
        if (str_starts_with($line, 'laravel:')) {
            continue;
        }
        $found = null;
        foreach ($afterLines as $index => $candidate) {
            if ($index > $position && $candidate === $line) {
                $found = $index;
                break;
            }
        }
        expect($found)->not->toBeNull('kept in order: '.var_export($line, true));
        $position = $found;
    }

    $data = Yaml::parse($after);
    expect($data['laravel'])->toBe('./')
        ->and($data['env']['APP_DEBUG'] ?? null)->toBeTrue()
        ->and($data['workbench']['discovers']['views'])->toBeFalse();
});

it('reports No changes on the rerun after the text edit', function () {
    $dir = $this->project('package');
    file_put_contents($dir.'/testbench.yaml', s9d1WorkbenchYaml());
    $this->setupRun($dir, ['--yes' => true]);
    expect((string) $this->read($dir, 'testbench.yaml'))->toContain('  # - Workbench\App\Providers\WorkbenchServiceProvider');

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)->and($output)->toContain('No changes');
});

it('keeps a comment inside an env map it adds APP_DEBUG to', function () {
    $dir = $this->project('package');
    file_put_contents($dir.'/testbench.yaml', "laravel: '@testbench'\n\n# local settings\nenv:\n  # keep me\n  APP_NAME: Example\n\nproviders: []\n");

    $this->setupRun($dir, ['--yes' => true]);
    $after = (string) $this->read($dir, 'testbench.yaml');

    expect($after)->toContain("# local settings\n")
        ->toContain('  # keep me')
        ->toContain('  APP_NAME: Example')
        ->and(Yaml::parse($after)['env'])->toMatchArray(['APP_NAME' => 'Example', 'APP_DEBUG' => true]);
});
