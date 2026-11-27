<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9d-1 (laravel-layer): what the setup plans and prints beyond S9b.
 * Requirements R4, R8, R9, R10, R11, R23. Skills-gaps rows 1, 4, 16, 32, 41, 51, 128, 129, 133, 140.
 * Contract: tests/S9d1/CONTRACT.md sections 5 to 12.
 */

const S9D1_SETTINGS = '.claude/settings.json';

/**
 * Write a composer.json change through a callback on the decoded array.
 */
function s9d1Composer(string $dir, callable $change): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer = $change($composer);
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * Put a file into the project, creating its directories.
 */
function s9d1Put(string $dir, string $relative, string $content): void
{
    if (! is_dir(dirname($dir.'/'.$relative))) {
        mkdir(dirname($dir.'/'.$relative), 0777, true);
    }
    file_put_contents($dir.'/'.$relative, $content);
}

/**
 * The JSON object printed after the first line that names .claude/settings.json: from the next
 * line that starts with `{` (after indentation), the shortest run of lines that decodes.
 *
 * @return array<string, mixed>|null
 */
function s9d1SuggestedSettings(string $output): ?array
{
    $lines = preg_split('/\R/', $output) ?: [];
    $mention = null;
    foreach ($lines as $index => $line) {
        if (str_contains($line, S9D1_SETTINGS)) {
            $mention = $index;
            break;
        }
    }
    if ($mention === null) {
        return null;
    }
    for ($start = $mention + 1; $start < count($lines); $start++) {
        if (str_starts_with(ltrim($lines[$start]), '{')) {
            $buffer = '';
            for ($end = $start; $end < count($lines); $end++) {
                $buffer .= $lines[$end]."\n";
                $decoded = json_decode($buffer, true);
                if (is_array($decoded)) {
                    return $decoded;
                }
            }

            return null;
        }
    }

    return null;
}

/**
 * The number N of "N changes planned." / "1 change planned.", or null.
 */
function s9d1Planned(string $output): ?int
{
    if (preg_match('/(\d+) changes? planned\./', $output, $m) === 1) {
        return (int) $m[1];
    }

    return null;
}

/**
 * The number N of "Applied: N changes." / "Applied: 1 change.", or null.
 */
function s9d1Applied(string $output): ?int
{
    if (preg_match('/Applied: (\d+) changes?\./', $output, $m) === 1) {
        return (int) $m[1];
    }

    return null;
}

// 5. Suggested Claude Code permissions, never written (row 16)
// =========================================================================

it('prints suggested .claude/settings.json permissions with the runner-form gate command', function (bool $ddev, string $rule) {
    $dir = $this->project('app', ddev: $ddev);

    [, $output] = $this->setupRun($dir, ['--check' => true]);
    $settings = s9d1SuggestedSettings($output);

    expect($settings)->not->toBeNull('the output names .claude/settings.json and prints a JSON object after it')
        ->and($settings['permissions']['allow'] ?? null)->toBeArray()
        ->and($settings['permissions']['allow'])->toContain($rule);
})->with([
    'host' => [false, 'Bash(composer test)'],
    'DDEV' => [true, 'Bash(ddev composer test)'],
]);

it('suggests no blanket or tinker permission', function () {
    $dir = $this->project('package', ddev: true);

    [, $output] = $this->setupRun($dir, ['--check' => true]);
    $allow = s9d1SuggestedSettings($output)['permissions']['allow'] ?? null;

    expect($allow)->toBeArray()->not->toBe([]);
    foreach ($allow as $rule) {
        expect($rule)->toBeString()
            ->not->toBe('*')
            ->not->toBe('Bash')
            ->not->toBe('Bash(*)')
            ->not->toStartWith('mcp__*')
            ->not->toContain('tinker');
    }
});

it('never writes .claude/settings.json, and leaves an existing one byte for byte', function () {
    $dir = $this->project('app', ddev: true);
    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(file_exists($dir.'/'.S9D1_SETTINGS))->toBeFalse()
        ->and($output)->not->toContain('+++ b/'.S9D1_SETTINGS);

    $mine = "{\n    \"permissions\": {\"allow\": [\"Bash(ls *)\"]}\n}\n";
    s9d1Put($dir, S9D1_SETTINGS, $mine);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($this->read($dir, S9D1_SETTINGS))->toBe($mine);
});

it('prints the suggestion on a No changes run as well, exit 0', function () {
    $dir = $this->project('app');
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and(s9d1SuggestedSettings($output))->not->toBeNull();
});

// 6. The planned count equals the applied count (row 129)
// =========================================================================

it('counts the same changes in the plan and in the apply line', function (string $fixture, bool $ddev, ?string $profileChange) {
    $make = function () use ($fixture, $ddev, $profileChange): string {
        $dir = $this->project($fixture, ddev: $ddev);
        if ($profileChange !== null) {
            $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'auto']]);
            $this->setupRun($dir, ['--yes' => true]);
            $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => $profileChange, 'ci' => true]]);
        }

        return $dir;
    };

    [, $plan] = $this->setupRun($make(), ['--check' => true]);
    [$code, $apply] = $this->setupRun($make(), ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(s9d1Planned($plan))->not->toBeNull()
        ->and(s9d1Applied($apply))->toBe(s9d1Planned($plan));
})->with([
    'fresh app' => ['app', false, null],
    'fresh package on DDEV' => ['package', true, null],
    'package switched to test_database ddev' => ['package', true, 'ddev'],
]);

// 7. Boost output under the Testbench skeleton (row 1) and the boost.json seed (row 4)
// =========================================================================

it('warns when Boost wrote into the @testbench skeleton inside vendor/', function (string $file) {
    $dir = $this->project('package');
    s9d1Put($dir, 'vendor/orchestra/testbench-core/laravel/'.$file, "# written by Boost\n");

    [, $output] = $this->setupRun($dir, ['--check' => true]);
    $line = collect(preg_split('/\R/', $output) ?: [])->first(static fn (string $l): bool => str_contains($l, 'vendor/orchestra/testbench-core/laravel'));

    expect($line)->not->toBeNull('a line names the skeleton path')
        ->and($line)->toContain('boost:install');
})->with([
    'CLAUDE.md' => ['CLAUDE.md'],
    'AGENTS.md' => ['AGENTS.md'],
    'a skill' => ['.claude/skills/laravel-pitfalls/SKILL.md'],
]);

it('prints no skeleton warning for a package Boost has not written into vendor/', function () {
    $dir = $this->project('package');

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('vendor/orchestra/testbench-core/laravel');
});

it('creates the boost.json seed when it is missing', function (string $fixture) {
    $dir = $this->project($fixture);
    unlink($dir.'/boost.json');

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('+++ b/boost.json')
        ->and(json_decode((string) $this->read($dir, 'boost.json'), true))->toBe([
            'agents' => ['claude_code'],
            'packages' => ['michtio/laravel-claude-skills'],
            'cloud' => false,
        ]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0)->and($output)->toContain('No changes');
})->with(['app' => ['app'], 'package' => ['package']]);

it('never changes a boost.json that exists, whoever wrote it', function () {
    $dir = $this->project('app');
    $before = (string) file_get_contents($dir.'/boost.json');

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, 'boost.json'))->toBe($before)
        ->and($output)->not->toContain('b/boost.json');

    unlink($dir.'/boost.json');
    $this->setupRun($dir, ['--yes' => true]);
    file_put_contents($dir.'/boost.json', "{\"agents\": [\"claude_code\", \"cursor\"], \"mcp\": true}\n");
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($output)->not->toContain('edited by hand: boost.json');
});

// 8. The boost:update hint after the DDEV PHP version changes (row 32)
// =========================================================================

it('prints the runner-form boost:update when the DDEV PHP version changed since the setup ran', function (string $fixture, string $command) {
    $dir = $this->project($fixture, ddev: true);
    $config = (string) file_get_contents($dir.'/.ddev/config.yaml');
    file_put_contents($dir.'/.ddev/config.yaml', $config."php_version: \"8.4\"\n");
    file_put_contents($dir.'/CLAUDE.md', "# Laravel Boost Guidelines\n\n## Foundational Context\nThis application is a Laravel application running on PHP 8.4.\n");
    $this->setupRun($dir, ['--yes' => true]);

    file_put_contents($dir.'/.ddev/config.yaml', $config."php_version: \"8.3\"\n");
    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain($command);
})->with([
    'app' => ['app', 'ddev artisan boost:update'],
    'package' => ['package', 'ddev exec php vendor/bin/testbench boost:update'],
]);

it('prints no boost:update hint when the DDEV PHP version is unchanged', function () {
    $dir = $this->project('app', ddev: true);
    $config = (string) file_get_contents($dir.'/.ddev/config.yaml');
    file_put_contents($dir.'/.ddev/config.yaml', $config."php_version: \"8.4\"\n");
    file_put_contents($dir.'/CLAUDE.md', "# Laravel Boost Guidelines\n\n## Foundational Context\nThis application is a Laravel application running on PHP 8.4.\n");
    $this->setupRun($dir, ['--yes' => true]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('boost:update');
});

// 9. PHPStan ownership: a deleted setup file and a shadowing copy (rows 41, 51)
// =========================================================================

/**
 * An app on Larastan, set up, so the setup wrote phpstan.neon and recorded it.
 */
function s9d1PhpstanApp(object $test): string
{
    $dir = $test->project('app');
    s9d1Composer($dir, static function (array $c): array {
        $c['require-dev']['larastan/larastan'] = '^3.0';

        return $c;
    });
    \Illuminate\Support\Facades\Artisan::call('claude-skills:setup', ['--path' => $dir, '--yes' => true]);
    expect(file_exists($dir.'/phpstan.neon'))->toBeTrue();

    return $dir;
}

it('exits 0 on --check after the takeover: the .dist created and the setup copy deleted', function () {
    $dir = s9d1PhpstanApp($this);
    file_put_contents($dir.'/phpstan.neon.dist', "parameters:\n    level: 6\n    paths:\n        - app\n");
    unlink($dir.'/phpstan.neon');

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('Left alone: phpstan.neon.dist')
        ->and($output)->not->toContain('changes planned')
        ->and($output)->not->toContain('change planned');
});

it('warns that a hand-edited setup copy shadows the .dist', function () {
    $dir = s9d1PhpstanApp($this);
    file_put_contents($dir.'/phpstan.neon', (string) file_get_contents($dir.'/phpstan.neon')."    reportUnmatchedIgnoredErrors: false\n");
    file_put_contents($dir.'/phpstan.neon.dist', "parameters:\n    level: 6\n    paths:\n        - app\n");

    foreach ([1, 2] as $run) {
        [, $output] = $this->setupRun($dir, ['--yes' => true]);
        $line = collect(preg_split('/\R/', $output) ?: [])->first(static fn (string $l): bool => stripos($l, 'shadow') !== false);

        expect($line)->not->toBeNull('run '.$run.': a line says phpstan.neon shadows the .dist')
            ->and($line)->toContain('phpstan.neon.dist')
            ->and(str_replace('phpstan.neon.dist', '', (string) $line))->toContain('phpstan.neon');
    }
});

it('prints no shadow warning for a config the person wrote, nor without a .dist', function () {
    $dir = s9d1PhpstanApp($this);

    [, $output] = $this->setupRun($dir, ['--check' => true]);
    expect(stripos($output, 'shadow'))->toBeFalse();

    $own = $this->project('app');
    s9d1Composer($own, static function (array $c): array {
        $c['require-dev']['larastan/larastan'] = '^3.0';

        return $c;
    });
    file_put_contents($own.'/phpstan.neon.dist', "parameters:\n    level: 6\n");
    file_put_contents($own.'/phpstan.neon', "includes:\n    - phpstan.neon.dist\n");
    [, $output] = $this->setupRun($own, ['--check' => true]);

    expect(stripos($output, 'shadow'))->toBeFalse();
});

// 10. Moving an existing package suite to test_database ddev (row 128)
// =========================================================================

/**
 * A package on DDEV, set up on in-memory sqlite, with or without a test file.
 */
function s9d1SqlitePackage(object $test, bool $withTests): string
{
    $dir = $test->project('package', ddev: true);
    if ($withTests) {
        s9d1Put($dir, 'tests/Feature/MemberTest.php', "<?php\n\nit('works', fn () => expect(true)->toBeTrue());\n");
    }
    \Illuminate\Support\Facades\Artisan::call('claude-skills:setup', ['--path' => $dir, '--yes' => true]);

    return $dir;
}

/**
 * The output line that warns about moving an existing suite to the DDEV database, or null.
 */
function s9d1SuiteWarning(string $output): ?string
{
    return collect(preg_split('/\R/', $output) ?: [])->first(
        static fn (string $l): bool => str_contains($l, 'test_database') && stripos($l, 'tables') !== false && stripos($l, 'connections') !== false,
    );
}

it('warns when test_database ddev moves a package suite that has tests, pointing to the docs', function () {
    $dir = s9d1SqlitePackage($this, true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(s9d1SuiteWarning($output))->not->toBeNull('one line names test_database, kept tables and leaked connections')
        ->and(s9d1SuiteWarning($output))->toContain('docs/profile.md');
});

it('does not warn for a package with no tests, nor once the move is applied', function () {
    $empty = s9d1SqlitePackage($this, false);
    $this->writeProfile($empty, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    [, $output] = $this->setupRun($empty, ['--check' => true]);
    expect(s9d1SuiteWarning($output))->toBeNull();

    $dir = s9d1SqlitePackage($this, true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    $this->setupRun($dir, ['--yes' => true]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)->and(s9d1SuiteWarning($output))->toBeNull();
});

// 11. BCRYPT_ROUNDS pinned (row 133)
// =========================================================================

it('forces BCRYPT_ROUNDS=4 in a PHPUnit file that has no BCRYPT_ROUNDS', function (string $fixture, string $file) {
    $dir = $this->project($fixture, ddev: true);

    $this->setupRun($dir, ['--yes' => true]);

    expect((string) $this->read($dir, $file))->toContain('<env name="BCRYPT_ROUNDS" value="4" force="true"/>');

    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
})->with([
    'app' => ['app', 'phpunit.xml'],
    'package' => ['package', 'phpunit.xml.dist'],
]);

// 12. Other workflows when the suite moves to a real database (row 140)
// =========================================================================

it('names every workflow it does not own that runs the tests without a database service', function () {
    $dir = $this->project('package', ddev: true);
    s9d1Put($dir, '.github/workflows/tests.yml', "name: tests\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v7\n      - run: vendor/bin/pest\n");
    s9d1Put($dir, '.github/workflows/lint.yml', "name: lint\non: [push]\njobs:\n  lint:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v7\n      - run: vendor/bin/pint --test\n");
    s9d1Put($dir, '.github/workflows/db.yml', "name: db\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    services:\n      mysql:\n        image: mysql:8.0\n    steps:\n      - uses: actions/checkout@v7\n      - run: composer test\n");
    $before = [
        'tests.yml' => (string) file_get_contents($dir.'/.github/workflows/tests.yml'),
        'lint.yml' => (string) file_get_contents($dir.'/.github/workflows/lint.yml'),
        'db.yml' => (string) file_get_contents($dir.'/.github/workflows/db.yml'),
    ];
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('.github/workflows/tests.yml')
        ->and($output)->not->toContain('lint.yml')
        ->and($output)->not->toContain('db.yml');
    foreach ($before as $name => $content) {
        expect($this->read($dir, '.github/workflows/'.$name))->toBe($content);
    }
});

it('names no workflow while the package stays on in-memory sqlite', function () {
    $dir = $this->project('package', ddev: true);
    s9d1Put($dir, '.github/workflows/tests.yml', "name: tests\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: vendor/bin/pest\n");

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('tests.yml');
});
