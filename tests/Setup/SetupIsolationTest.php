<?php

declare(strict_types=1);

/**
 * Gate tests for slice S6b (laravel-layer): test isolation, one gate command,
 * commit-message hook, secret scanning, package-local skeleton.
 * Requirements R8 (rest), R9, R10. Acceptance criteria AC9, AC10, AC11, AC12.
 * Integration halves (a real suite in DDEV, the test database, Boost on a
 * package) are in tests/gate/test_s6b.py. Built on the S6a contract (see
 * tests/Setup/TestCase.php and SetupCommandTest.php): same command, output
 * phrases, "Apply these changes?" confirmation, `edited by hand: <path>`,
 * `No changes`, --yes, --check.
 *
 * ---------------------------------------------------------------------------
 * PINNED CONTRACT
 * ---------------------------------------------------------------------------
 *
 * 1. PHPUNIT FILE
 *    Which file: phpunit.xml if it exists, else phpunit.xml.dist if it exists,
 *    else a new one: phpunit.xml for an app, phpunit.xml.dist for a package.
 *    Owned: only the `<env>` elements below, inside `<php>` (created when
 *    absent). Everything else in the file (testsuites, source, other env) is
 *    kept. Each owned element is written exactly as
 *    `<env name="X" value="v" force="true"/>`, in place when an element with
 *    that name exists (stock Laravel's unforced element is replaced, it is NOT
 *    a hand edit), appended otherwise.
 *    A new file is a complete PHPUnit config: bootstrap="vendor/autoload.php";
 *    app suites Unit (tests/Unit) and Feature (tests/Feature); package one
 *    suite "Test" (tests).
 *    Pins (name => value), always force="true":
 *      APP_ENV=testing, CACHE_STORE=array, QUEUE_CONNECTION=sync,
 *      MAIL_MAILER=array, SESSION_DRIVER=array, DB_URL="" (an empty URL cannot
 *      point the suite at the dev database), DB_CONNECTION and DB_DATABASE:
 *    DB rule. connection = DB_CONNECTION from .env, else .env.example (.env
 *      wins), else "mysql" for a DDEV app and "sqlite" otherwise.
 *      - package, or connection sqlite: DB_CONNECTION=sqlite, DB_DATABASE=:memory:
 *      - otherwise DB_CONNECTION=<connection>, DB_DATABASE=<slug>_test
 *    <slug>: the part of composer.json "name" after the slash (the whole name
 *      when there is no slash); without a name, the project directory's
 *      basename. Lowercased, every run of characters outside [a-z0-9] becomes
 *      one underscore, leading/trailing underscores trimmed.
 *      "laravel/laravel" -> laravel_test, "Acme/My-Shop.v2" -> my_shop_v2_test.
 *
 * 1b. SERVER TWINS: DB_URL, DB_CONNECTION, DB_DATABASE and every live flag
 *    also get `<server name="X" value="v"/>` with the same value (Laravel reads
 *    $_SERVER first). Twins for other keys are allowed, none is required for
 *    APP_ENV.
 *
 * 2. LIVE-PROVIDER FLAGS
 *    A key is a live-provider flag when it matches, case-sensitively,
 *    /^[A-Z][A-Z0-9_]*_LIVE(_MODE)?$/ in the lines of .env.example or .env
 *    (union, comments and blank lines ignored, any value, including false).
 *    PAYMENTS_LIVE, STRIPE_LIVE_MODE match; LIVE_RELOAD, OLIVE_OIL, ALIVE do
 *    not. Each found key gets `<env name="KEY" value="false" force="true"/>`.
 *    `*_SANDBOX` style flags are out of scope.
 *
 * 3. DDEV TEST DATABASE (DDEV app with a non-sqlite connection only)
 *    .ddev/config.claude-skills.yaml, a hooks override DDEV merges:
 *      hooks.post-start: a list with one entry
 *        {exec: "<shell>", service: db}
 *    <shell> contains "CREATE DATABASE IF NOT EXISTS <slug>_test" and
 *    "GRANT ALL" (idempotent, runs in the db container). No `exec-host` entry
 *    anywhere. Not written for a host app, a package, or a sqlite app.
 *
 * 4. GATE SCRIPT: composer.json scripts.test (key order and the rest of the
 *    file kept). A list of strings, in this order, each present only when its
 *    package is in require or require-dev:
 *      laravel/pint                         "pint --test"
 *      phpstan/phpstan or larastan/larastan "phpstan analyse --no-progress"
 *      pestphp/pest                         "pest"
 *      none of pest: an app "@php artisan test", a package
 *        "@php vendor/bin/testbench package:test"
 *      always last                          "bash .githooks/gitleaks-check"
 *    An APP additionally starts with "@php artisan config:clear --ansi" (stale
 *    cached config would break the suite; Laravel's stock script has it); a
 *    package has no config:clear.
 *    An existing scripts.test that differs and was not written by setup is a
 *    hand edit: "edited by hand: composer.json", diff shown, asked.
 *
 * 5. HOOKS AND SECRET SCAN, files (executable, mode & 0111):
 *    .githooks/commit-msg: sh script, argument = message file. It blocks AI
 *      attribution only, never human collaboration (round 2 ruling). Exit 1 with a
 *      message naming the line when a non-comment line (not starting with #)
 *      matches, case-insensitively: a Co-Authored-By trailer (any leading
 *      whitespace) naming an AI tool or vendor (see SetupIsolationRound2Test.php),
 *      Generated with/by followed by an AI tool, a Claude-Session: line, the robot
 *      emoji footer. A human Co-authored-by trailer and "generated with Faker"
 *      exit 0. Exit 0 otherwise.
 *    .githooks/gitleaks-check: sh script. gitleaks on PATH: runs
 *      `gitleaks detect --source . --config .gitleaks.toml --no-banner`.
 *      Absent: with CI set (non-empty) exit 1, stderr "gitleaks is required in CI";
 *      without CI exit 0, output "gitleaks not found, skipping the secret scan".
 *    .gitleaks.toml: contains `useDefault = true` under [extend], an
 *      [[allowlists]] table (current gitleaks schema), and the paths tests/Fixtures/ and .env.example.
 *    core.hooksPath: a plan action line "git config core.hooksPath .githooks"
 *      inside the same single confirmation; --yes or a yes runs it (in the project
 *      root); a no does not. Not a git repository: no action, output contains
 *      "Not a git repository: skipping core.hooksPath". Already .githooks: not an
 *      action. Set to another value: never changed, output contains
 *      "core.hooksPath is already set to <value>". --check: an unset hooksPath in
 *      a git repo counts as a change (exit 1).
 *
 * 6. PACKAGE-LOCAL SKELETON (Testbench). Boost reads .ai/guidelines, boost.json
 *    and writes CLAUDE.md under base_path(), which Testbench sets from
 *    testbench.yaml `laravel:` (vendor/orchestra/testbench-core
 *    src/Foundation/Config.php, "@testbench" = the vendored skeleton). Pointing it
 *    at the package root works (verified by hand with Boost 2.5, Testbench 11):
 *      testbench.yaml: laravel: ./     (other keys kept)
 *                      env: APP_DEBUG: true   (Boost registers its commands only
 *                      when debug is on; a map entry, other env keys kept)
 *      directories Laravel needs under that base, each with a .gitignore of
 *      "*\n!.gitignore\n": bootstrap/cache, storage/logs, storage/framework/cache,
 *      storage/framework/sessions, storage/framework/views.
 *    A `laravel:` value other than absent, "@testbench" or "./" is a hand edit
 *    ("edited by hand: testbench.yaml").
 *
 * 7. Every new file takes part in idempotence and hand-edit detection like the
 *    S6a files: second run "No changes", --check 0, hand edit shown and asked.
 */

use Illuminate\Support\Facades\Artisan;
use Symfony\Component\Yaml\Yaml;

defined('RUNNER_GUIDELINE') || define('RUNNER_GUIDELINE', '.ai/guidelines/claude-skills-runner.md');

const ISO_DDEV_HOOK = '.ddev/config.claude-skills.yaml';
const ISO_STANDARD_PINS = [
    'APP_ENV' => 'testing',
    'CACHE_STORE' => 'array',
    'QUEUE_CONNECTION' => 'sync',
    'MAIL_MAILER' => 'array',
    'SESSION_DRIVER' => 'array',
    'DB_URL' => '',
];

/**
 * Run the command and return [exit code, output].
 *
 * @return array{0: int, 1: string}
 */
function isoSetup(string $dir, array $options = []): array
{
    $code = Artisan::call('claude-skills:setup', ['--path' => $dir] + $options);

    return [$code, Artisan::output()];
}

/**
 * Write a project file, creating directories.
 */
function isoPut(string $dir, string $relative, string $content): void
{
    if (! is_dir(dirname($dir.'/'.$relative))) {
        mkdir(dirname($dir.'/'.$relative), 0777, true);
    }
    file_put_contents($dir.'/'.$relative, $content);
}

/**
 * Set composer.json keys of a project copy.
 *
 * @param  array<string, mixed>  $merge  Top-level keys replaced.
 */
function isoComposer(string $dir, array $merge): void
{
    $composer = json_decode(file_get_contents($dir.'/composer.json'), true);
    foreach ($merge as $key => $value) {
        $composer[$key] = $value;
    }
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * Parse the env elements of a PHPUnit file as name => [value, force].
 *
 * @return array<string, array{0: string, 1: string|null}>
 */
function isoEnv(?string $xml): array
{
    expect($xml)->not->toBeNull('the PHPUnit file was not written');
    $doc = simplexml_load_string($xml);
    $out = [];
    foreach ($doc->php->env ?? [] as $env) {
        $out[(string) $env['name']] = [(string) $env['value'], isset($env['force']) ? (string) $env['force'] : null];
    }

    return $out;
}

/**
 * Parse the server elements of a PHPUnit file as name => value.
 *
 * @return array<string, string>
 */
function isoServer(?string $xml): array
{
    $doc = simplexml_load_string((string) $xml);
    $out = [];
    foreach ($doc->php->server ?? [] as $server) {
        $out[(string) $server['name']] = (string) $server['value'];
    }

    return $out;
}

/**
 * Assert the `<server name="X" value="v"/>` twin of a pin. Laravel reads $_SERVER
 * before $_ENV, so a forced env alone does not beat a variable the process
 * already has. Required for DB_URL, DB_CONNECTION, DB_DATABASE and live flags.
 */
function isoTwin(?string $xml, string $name, string $value): void
{
    $server = isoServer($xml);
    expect(array_key_exists($name, $server))->toBeTrue("no <server> twin for $name");
    expect($server[$name])->toBe($value);
}

/**
 * Assert a forced pin.
 */
function isoPinned(array $env, string $name, string $value): void
{
    expect($env)->toHaveKey($name);
    expect($env[$name])->toBe([$value, 'true']);
}

/**
 * Run git in a project directory.
 *
 * @return array{0: int, 1: string}
 */
function isoGit(string $dir, string $args): array
{
    exec('git -C '.escapeshellarg($dir).' '.$args.' 2>&1', $out, $code);

    return [$code, trim(implode("\n", $out))];
}

/**
 * Run a project script with sh and a clean environment.
 *
 * @param  array<string, string>  $env
 * @return array{0: int, 1: string}
 */
function isoRun(string $dir, string $script, array $env = [], string $arg = ''): array
{
    $vars = '';
    foreach ($env + ['PATH' => '/usr/bin:/bin'] as $key => $value) {
        $vars .= ' '.$key.'='.escapeshellarg($value);
    }
    exec('cd '.escapeshellarg($dir).' && env -i'.$vars.' sh '.escapeshellarg($script).($arg === '' ? '' : ' '.escapeshellarg($arg)).' 2>&1', $out, $code);

    return [$code, implode("\n", $out)];
}

// 1. PHPUnit file
// =========================================================================

it('creates phpunit.xml for an app with forced pins and its own database (DDEV)', function () {
    $dir = $this->project('app', ddev: true);

    [$code] = isoSetup($dir, ['--yes' => true]);

    expect($code)->toBe(0);
    $xml = $this->read($dir, 'phpunit.xml');
    expect($xml)->not->toBeNull()->and($this->read($dir, 'phpunit.xml.dist'))->toBeNull();
    $env = isoEnv($xml);
    foreach (ISO_STANDARD_PINS as $name => $value) {
        isoPinned($env, $name, $value);
    }
    isoPinned($env, 'DB_CONNECTION', 'mysql');
    isoPinned($env, 'DB_DATABASE', 'app_test');
    expect($xml)->toContain('<env name="APP_ENV" value="testing" force="true"/>');
    isoTwin($xml, 'DB_URL', '');
    isoTwin($xml, 'DB_CONNECTION', 'mysql');
    isoTwin($xml, 'DB_DATABASE', 'app_test');

    $doc = simplexml_load_string($xml);
    expect((string) $doc['bootstrap'])->toBe('vendor/autoload.php');
    $suites = [];
    foreach ($doc->testsuites->testsuite as $suite) {
        $suites[(string) $suite['name']] = (string) $suite->directory;
    }
    expect($suites)->toBe(['Unit' => 'tests/Unit', 'Feature' => 'tests/Feature']);
});

it('creates phpunit.xml.dist for a package with an in-memory sqlite database', function () {
    $dir = $this->project('package');

    isoSetup($dir, ['--yes' => true]);

    expect($this->read($dir, 'phpunit.xml'))->toBeNull();
    $xml = $this->read($dir, 'phpunit.xml.dist');
    expect($xml)->not->toBeNull();
    $env = isoEnv($xml);
    foreach (ISO_STANDARD_PINS as $name => $value) {
        isoPinned($env, $name, $value);
    }
    isoPinned($env, 'DB_CONNECTION', 'sqlite');
    isoPinned($env, 'DB_DATABASE', ':memory:');
    isoTwin($xml, 'DB_CONNECTION', 'sqlite');
    isoTwin($xml, 'DB_DATABASE', ':memory:');
    $doc = simplexml_load_string($xml);
    expect((string) $doc['bootstrap'])->toBe('vendor/autoload.php')
        ->and((string) $doc->testsuites->testsuite['name'])->toBe('Test')
        ->and((string) $doc->testsuites->testsuite->directory)->toBe('tests');
});

it('defaults a host app without database config to in-memory sqlite', function () {
    $dir = $this->project('app');

    isoSetup($dir, ['--yes' => true]);

    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    isoPinned($env, 'DB_CONNECTION', 'sqlite');
    isoPinned($env, 'DB_DATABASE', ':memory:');
});

it('reads the connection from .env.example and lets .env win', function () {
    $dir = $this->project('app');
    isoPut($dir, '.env.example', "DB_CONNECTION=pgsql\n");

    isoSetup($dir, ['--yes' => true]);
    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    isoPinned($env, 'DB_CONNECTION', 'pgsql');
    isoPinned($env, 'DB_DATABASE', 'app_test');

    $dir = $this->project('app');
    isoPut($dir, '.env.example', "DB_CONNECTION=pgsql\n");
    isoPut($dir, '.env', "DB_CONNECTION=mariadb\n");
    isoSetup($dir, ['--yes' => true]);
    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'DB_CONNECTION', 'mariadb');
});

it('derives the database name from the composer name', function (?string $name, string $expected) {
    $dir = $this->project('app', ddev: true);
    $composer = json_decode(file_get_contents($dir.'/composer.json'), true);
    unset($composer['name']);
    if ($name !== null) {
        $composer['name'] = $name;
    }
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");

    isoSetup($dir, ['--yes' => true]);

    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'DB_DATABASE', $expected);
    expect($this->read($dir, ISO_DDEV_HOOK))->toContain('CREATE DATABASE IF NOT EXISTS '.$expected);
})->with([
    'plain' => ['laravel/laravel', 'laravel_test'],
    'punctuation and case' => ['Acme/My-Shop.v2', 'my_shop_v2_test'],
    'no slash' => ['solo', 'solo_test'],
]);

it('falls back to the directory name when composer.json has no name', function () {
    $dir = $this->project('app', ddev: true);
    $composer = json_decode(file_get_contents($dir.'/composer.json'), true);
    unset($composer['name']);
    file_put_contents($dir.'/composer.json', json_encode($composer)."\n");
    $slug = trim(preg_replace('/[^a-z0-9]+/', '_', strtolower(basename($dir))), '_');

    isoSetup($dir, ['--yes' => true]);

    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'DB_DATABASE', $slug.'_test');
});

it('forces every live-provider flag found in .env.example and .env off', function () {
    $dir = $this->project('app');
    isoPut($dir, '.env.example', "APP_NAME=Fixture\n# OLD_LIVE=true\nPAYMENTS_LIVE=false\nLIVE_RELOAD=true\nOLIVE_OIL=1\nALIVE=1\n");
    isoPut($dir, '.env', "PAYMENTS_LIVE=true\nSTRIPE_LIVE_MODE=1\nMOLLIE_API_LIVE=yes\nlower_live=1\n");

    isoSetup($dir, ['--yes' => true]);

    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    foreach (['PAYMENTS_LIVE', 'STRIPE_LIVE_MODE', 'MOLLIE_API_LIVE'] as $key) {
        isoPinned($env, $key, 'false');
    }
    foreach (['PAYMENTS_LIVE', 'STRIPE_LIVE_MODE', 'MOLLIE_API_LIVE'] as $key) {
        isoTwin($this->read($dir, 'phpunit.xml'), $key, 'false');
    }
    foreach (['OLD_LIVE', 'LIVE_RELOAD', 'OLIVE_OIL', 'ALIVE', 'lower_live', 'APP_NAME'] as $key) {
        expect($env)->not->toHaveKey($key);
    }
});

it('writes no live-flag element when none exists', function () {
    $dir = $this->project('app');

    isoSetup($dir, ['--yes' => true]);

    $names = array_keys(isoEnv($this->read($dir, 'phpunit.xml')));
    expect(array_filter($names, fn ($n) => preg_match('/_LIVE(_MODE)?$/', $n)))->toBe([]);
});

it('uses phpunit.xml.dist when it is the only file and phpunit.xml when both exist', function () {
    $dir = $this->project('app');
    isoPut($dir, 'phpunit.xml.dist', "<?xml version=\"1.0\"?>\n<phpunit bootstrap=\"vendor/autoload.php\">\n</phpunit>\n");
    isoSetup($dir, ['--yes' => true]);
    expect($this->read($dir, 'phpunit.xml'))->toBeNull();
    isoPinned(isoEnv($this->read($dir, 'phpunit.xml.dist')), 'APP_ENV', 'testing');

    $dir = $this->project('app');
    $dist = "<?xml version=\"1.0\"?>\n<phpunit bootstrap=\"vendor/autoload.php\">\n</phpunit>\n";
    isoPut($dir, 'phpunit.xml.dist', $dist);
    isoPut($dir, 'phpunit.xml', $dist);
    isoSetup($dir, ['--yes' => true]);
    expect($this->read($dir, 'phpunit.xml.dist'))->toBe($dist);
    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'APP_ENV', 'testing');
});

it('merges into a stock Laravel phpunit.xml: unforced pins replaced, everything else kept', function () {
    $dir = $this->project('app');
    $stock = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<phpunit bootstrap=\"vendor/autoload.php\" colors=\"true\">\n    <testsuites>\n        <testsuite name=\"Unit\">\n            <directory>tests/Unit</directory>\n        </testsuite>\n    </testsuites>\n    <php>\n        <env name=\"APP_ENV\" value=\"testing\"/>\n        <env name=\"BCRYPT_ROUNDS\" value=\"4\"/>\n        <env name=\"CACHE_STORE\" value=\"file\"/>\n    </php>\n</phpunit>\n";
    isoPut($dir, 'phpunit.xml', $stock);

    [$code, $output] = isoSetup($dir, ['--yes' => true]);

    expect($code)->toBe(0)->and($output)->not->toContain('edited by hand: phpunit.xml');
    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    isoPinned($env, 'CACHE_STORE', 'array');
    expect($env['BCRYPT_ROUNDS'][0])->toBe('4')
        ->and(substr_count($this->read($dir, 'phpunit.xml'), '<env name="CACHE_STORE"'))->toBe(1)
        ->and($this->read($dir, 'phpunit.xml'))->toContain('<testsuite name="Unit">');
});

it('adds a php section when the file has none', function () {
    $dir = $this->project('app');
    isoPut($dir, 'phpunit.xml', "<?xml version=\"1.0\"?>\n<phpunit bootstrap=\"vendor/autoload.php\">\n    <testsuites>\n        <testsuite name=\"Unit\">\n            <directory>tests</directory>\n        </testsuite>\n    </testsuites>\n</phpunit>\n");

    isoSetup($dir, ['--yes' => true]);

    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'APP_ENV', 'testing');
    expect($this->read($dir, 'phpunit.xml'))->toContain('<testsuite name="Unit">');
});

it('treats a forced pin with another value as a hand edit when the file was never written by setup', function () {
    $dir = $this->project('app');
    isoPut($dir, 'phpunit.xml', "<?xml version=\"1.0\"?>\n<phpunit bootstrap=\"vendor/autoload.php\">\n    <php>\n        <env name=\"CACHE_STORE\" value=\"redis\" force=\"true\"/>\n    </php>\n</phpunit>\n");
    $before = $this->read($dir, 'phpunit.xml');

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: phpunit.xml')
        ->expectsOutputToContain('--- a/phpunit.xml')
        ->expectsOutputToContain('+++ b/phpunit.xml')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, 'phpunit.xml'))->toBe($before);
});

it('shows the diff for a hand-edited phpunit.xml, asks, and keeps the edit on no', function () {
    $dir = $this->project('app', ddev: true);
    isoSetup($dir, ['--yes' => true]);
    $edited = str_replace('value="array" force="true"', 'value="redis" force="true"', $this->read($dir, 'phpunit.xml'));
    expect($edited)->not->toBe($this->read($dir, 'phpunit.xml'));
    file_put_contents($dir.'/phpunit.xml', $edited);

    expect(isoSetup($dir, ['--check' => true])[0])->toBe(1);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: phpunit.xml')
        ->expectsOutputToContain('--- a/phpunit.xml')
        ->expectsOutputToContain('+++ b/phpunit.xml')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, 'phpunit.xml'))->toBe($edited);
});

it('restores a hand-edited phpunit.xml pin only after a yes', function () {
    $dir = $this->project('app', ddev: true);
    isoSetup($dir, ['--yes' => true]);
    file_put_contents($dir.'/phpunit.xml', str_replace('value="array" force="true"', 'value="redis" force="true"', $this->read($dir, 'phpunit.xml')));

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'yes')
        ->assertExitCode(0);

    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'CACHE_STORE', 'array');
});

it('keeps other content a person added to phpunit.xml when setup changes a pin', function () {
    $dir = $this->project('app', ddev: true);
    isoSetup($dir, ['--yes' => true]);
    $added = str_replace('</php>', '    <env name="MY_FLAG" value="1"/>'."\n    </php>", $this->read($dir, 'phpunit.xml'));
    file_put_contents($dir.'/phpunit.xml', $added);
    isoComposer($dir, ['name' => 'example/renamed']);

    isoSetup($dir, ['--yes' => true]);

    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    isoPinned($env, 'DB_DATABASE', 'renamed_test');
    expect($env['MY_FLAG'][0])->toBe('1');
});

// 3. DDEV test database hook
// =========================================================================

it('writes a DDEV post-start hook that creates the test database in the db container', function () {
    $dir = $this->project('app', ddev: true);

    isoSetup($dir, ['--yes' => true]);

    $raw = $this->read($dir, ISO_DDEV_HOOK);
    expect($raw)->not->toBeNull()->not->toContain('exec-host');
    $hooks = Yaml::parse($raw)['hooks'];
    expect(array_keys($hooks))->toBe(['post-start'])
        ->and($hooks['post-start'])->toHaveCount(1);
    $entry = $hooks['post-start'][0];
    expect(array_keys($entry))->toEqualCanonicalizing(['exec', 'service'])
        ->and($entry['service'])->toBe('db')
        ->and($entry['exec'])->toContain('CREATE DATABASE IF NOT EXISTS app_test')
        ->toContain('GRANT ALL');
});

it('writes no DDEV hook for a host app, a package, a sqlite DDEV app, or a rerun that changes nothing else', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    expect(is_file($dir.'/'.ISO_DDEV_HOOK))->toBeFalse();

    $dir = $this->project('package', ddev: true);
    isoSetup($dir, ['--yes' => true]);
    expect(is_file($dir.'/'.ISO_DDEV_HOOK))->toBeFalse();

    $dir = $this->project('app', ddev: true);
    isoPut($dir, '.env.example', "DB_CONNECTION=sqlite\n");
    isoSetup($dir, ['--yes' => true]);
    expect(is_file($dir.'/'.ISO_DDEV_HOOK))->toBeFalse();
    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'DB_DATABASE', ':memory:');
});

it('does not touch .ddev/config.yaml', function () {
    $dir = $this->project('app', ddev: true);
    $config = $this->read($dir, '.ddev/config.yaml');

    isoSetup($dir, ['--yes' => true]);

    expect($this->read($dir, '.ddev/config.yaml'))->toBe($config);
});

it('shows the hook as a created file in the plan', function () {
    $dir = $this->project('app', ddev: true);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('+++ b/'.ISO_DDEV_HOOK)
        ->expectsOutputToContain('+++ b/phpunit.xml')
        ->expectsOutputToContain('+++ b/composer.json')
        ->expectsOutputToContain('+++ b/.githooks/commit-msg')
        ->expectsOutputToContain('+++ b/.gitleaks.toml')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);
});

// 4. Gate script
// =========================================================================

it('adds scripts.test for an app with no tools installed: artisan test then the secret scan', function () {
    $dir = $this->project('app');

    isoSetup($dir, ['--yes' => true]);

    $composer = json_decode($this->read($dir, 'composer.json'), true);
    expect($composer['scripts']['test'])->toBe(['@php artisan config:clear --ansi', '@php artisan test', 'bash .githooks/gitleaks-check'])
        ->and($composer['require']['laravel/boost'])->toBe('^2.5');
});

it('orders the gate steps pint, phpstan, pest, secret scan from what is installed', function (array $require, array $expected) {
    $dir = $this->project('app');
    $composer = json_decode($this->read($dir, 'composer.json'), true);
    $composer['require-dev'] = $require;
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");

    isoSetup($dir, ['--yes' => true]);

    expect(json_decode($this->read($dir, 'composer.json'), true)['scripts']['test'])->toBe($expected);
})->with([
    'pint and pest' => [['laravel/pint' => '^1.0', 'pestphp/pest' => '^4.0'], ['@php artisan config:clear --ansi', 'pint --test', 'pest', 'bash .githooks/gitleaks-check']],
    'all four' => [['laravel/pint' => '^1.0', 'larastan/larastan' => '^3.0', 'pestphp/pest' => '^4.0'], ['@php artisan config:clear --ansi', 'pint --test', 'phpstan analyse --no-progress', 'pest', 'bash .githooks/gitleaks-check']],
    'phpstan, no pest' => [['phpstan/phpstan' => '^2.0'], ['@php artisan config:clear --ansi', 'phpstan analyse --no-progress', '@php artisan test', 'bash .githooks/gitleaks-check']],
]);

it('gates a package with testbench package:test, or pest when installed', function () {
    $dir = $this->project('package');
    isoSetup($dir, ['--yes' => true]);
    expect(json_decode($this->read($dir, 'composer.json'), true)['scripts']['test'])
        ->toBe(['@php vendor/bin/testbench package:test', 'bash .githooks/gitleaks-check']);

    $dir = $this->project('package');
    $composer = json_decode($this->read($dir, 'composer.json'), true);
    $composer['require-dev']['pestphp/pest'] = '^4.0';
    $composer['require-dev']['laravel/pint'] = '^1.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    isoSetup($dir, ['--yes' => true]);
    expect(json_decode($this->read($dir, 'composer.json'), true)['scripts']['test'])
        ->toBe(['pint --test', 'pest', 'bash .githooks/gitleaks-check']);
});

it('keeps the rest of composer.json and its other scripts', function () {
    $dir = $this->project('app');
    isoComposer($dir, ['scripts' => ['dev' => ['@php artisan serve'], 'post-install-cmd' => ['@php artisan about']]]);
    $before = json_decode($this->read($dir, 'composer.json'), true);

    isoSetup($dir, ['--yes' => true]);

    $after = json_decode($this->read($dir, 'composer.json'), true);
    expect($after['scripts']['dev'])->toBe(['@php artisan serve'])
        ->and($after['scripts']['post-install-cmd'])->toBe(['@php artisan about'])
        ->and(array_keys($after['scripts']))->toBe(['dev', 'post-install-cmd', 'test']);
    unset($after['scripts']['test']);
    expect($after)->toBe($before);
});

it('treats a different existing scripts.test as a hand edit: diff, ask, keep on no', function () {
    $dir = $this->project('app');
    isoComposer($dir, ['scripts' => ['test' => ['@php artisan test --parallel']]]);
    $before = $this->read($dir, 'composer.json');

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: composer.json')
        ->expectsOutputToContain('--- a/composer.json')
        ->expectsOutputToContain('+++ b/composer.json')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, 'composer.json'))->toBe($before);
});

it('replaces a hand-edited scripts.test only after a yes', function () {
    $dir = $this->project('app');
    isoComposer($dir, ['scripts' => ['test' => 'phpunit']]);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'yes')
        ->assertExitCode(0);

    expect(json_decode($this->read($dir, 'composer.json'), true)['scripts']['test'])->toBe(['@php artisan config:clear --ansi', '@php artisan test', 'bash .githooks/gitleaks-check']);
});

it('leaves an identical existing scripts.test alone (no hand edit, no change)', function () {
    $dir = $this->project('app');
    isoComposer($dir, ['scripts' => ['test' => ['@php artisan config:clear --ansi', '@php artisan test', 'bash .githooks/gitleaks-check']]]);

    [, $output] = isoSetup($dir, ['--yes' => true]);

    expect($output)->not->toContain('edited by hand: composer.json')
        ->and(is_file($dir.'/.githooks/gitleaks-check'))->toBeTrue('the script the existing entry calls must be written')
        ->and(json_decode($this->read($dir, 'composer.json'), true)['scripts']['test'])->toBe(['@php artisan config:clear --ansi', '@php artisan test', 'bash .githooks/gitleaks-check']);
});

// 5. Commit-message hook, secret scan, hooksPath
// =========================================================================

it('writes executable hook scripts and the gitleaks config', function () {
    $dir = $this->project('app');

    isoSetup($dir, ['--yes' => true]);

    foreach (['.githooks/commit-msg', '.githooks/gitleaks-check'] as $script) {
        expect(is_file($dir.'/'.$script))->toBeTrue("$script missing")
            ->and(fileperms($dir.'/'.$script) & 0111)->not->toBe(0, "$script is not executable");
    }
    $toml = $this->read($dir, '.gitleaks.toml');
    expect($toml)->not->toBeNull()
        ->toContain('[extend]')->toContain('useDefault = true')
        ->toContain('[[allowlists]]')->toContain('tests/Fixtures/')->toContain('env\\.example');
});

it('commit-msg rejects AI attribution trailers and accepts clean messages', function (string $message, int $expected) {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    isoPut($dir, 'MSG', $message);

    [$code, $output] = isoRun($dir, '.githooks/commit-msg', arg: 'MSG');

    expect($code)->toBe($expected);
    if ($expected !== 0) {
        expect($output)->not->toBe('');
    }
})->with([
    'co-authored-by' => ["Add thing\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", 1],
    'lowercase co-authored-by' => ["Add thing\n\nco-authored-by: GitHub Copilot\n", 1],
    'claude-session' => ["Add thing\n\nClaude-Session: https://example.com/s/1\n", 1],
    'assisted-by' => ["Add thing\n\nAssisted-by: Claude\n", 1],
    'generated-by' => ["Add thing\n\nGenerated-by: ChatGPT\n", 1],
    'generated with' => ["Add thing\n\nGenerated with Claude Code\n", 1],
    'generated with mid-line' => ["Add thing\n\nThis was Generated With Cursor help.\n", 1],
    'clean' => ["Add thing\n\nBody text about the change.\n", 0],
    'attribution only in a comment line' => ["Add thing\n\n# Co-Authored-By: X\n# Generated with y\n", 0],
    'word co-authored in prose is not a trailer' => ["Fix the co-authored-by parser\n", 0],
]);

it('commit-msg names the offending trailer', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    isoPut($dir, 'MSG', "Add thing\n\nClaude-Session: abc\n");

    [, $output] = isoRun($dir, '.githooks/commit-msg', arg: 'MSG');

    expect($output)->toContain('Claude-Session');
});

it('gitleaks-check skips with a message locally and is required in CI when gitleaks is absent', function () {
    exec('env -i PATH=/usr/bin:/bin sh -c "command -v gitleaks" 2>&1', $found, $present);
    if ($present === 0) {
        $this->markTestSkipped('gitleaks is installed in /usr/bin or /bin; the absence case cannot be exercised');
    }
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);

    [$code, $output] = isoRun($dir, '.githooks/gitleaks-check');
    expect($code)->toBe(0)->and($output)->toContain('gitleaks not found, skipping the secret scan');

    [$code, $output] = isoRun($dir, '.githooks/gitleaks-check', ['CI' => 'true']);
    expect($code)->toBe(1)->and($output)->toContain('gitleaks is required in CI');
});

it('gitleaks-check runs gitleaks with the project config when it is on PATH', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    mkdir($dir.'/fakebin');
    file_put_contents($dir.'/fakebin/gitleaks', "#!/bin/sh\necho \"FAKE-GITLEAKS \$*\"\nexit 7\n");
    chmod($dir.'/fakebin/gitleaks', 0755);

    [$code, $output] = isoRun($dir, '.githooks/gitleaks-check', ['PATH' => $dir.'/fakebin:/usr/bin:/bin', 'CI' => 'true']);

    expect($code)->toBe(7)
        ->and($output)->toContain('FAKE-GITLEAKS detect --source . --config .gitleaks.toml --no-banner');
});

it('lists git config core.hooksPath .githooks in the plan and does not run it on a no', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('git config core.hooksPath .githooks')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect(isoGit($dir, 'config --get core.hooksPath')[1])->toBe('');
});

it('runs git config core.hooksPath .githooks with --yes or a yes', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    isoSetup($dir, ['--yes' => true]);
    expect(isoGit($dir, 'config --get core.hooksPath'))->toBe([0, '.githooks']);

    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsConfirmation('Apply these changes?', 'yes')
        ->assertExitCode(0);
    expect(isoGit($dir, 'config --get core.hooksPath'))->toBe([0, '.githooks']);
});

it('a git commit with an attribution trailer is blocked once hooksPath is set', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    isoGit($dir, 'config user.email t@example.com');
    isoGit($dir, 'config user.name T');
    isoSetup($dir, ['--yes' => true]);
    isoGit($dir, 'add -A');

    [$bad] = isoGit($dir, 'commit -q -m "Add thing" -m "Co-Authored-By: Claude <noreply@anthropic.com>"');
    [$good] = isoGit($dir, 'commit -q -m "Add thing"');

    expect($bad)->not->toBe(0)->and($good)->toBe(0);
});

it('skips hooksPath outside a git repository and says so', function () {
    $dir = $this->project('app');

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('Not a git repository: skipping core.hooksPath')
        ->assertExitCode(0);
});

it('never changes a core.hooksPath that points elsewhere, and says so', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    isoGit($dir, 'config core.hooksPath .husky');

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('core.hooksPath is already set to .husky')
        ->assertExitCode(0);

    expect(isoGit($dir, 'config --get core.hooksPath')[1])->toBe('.husky');
});

it('--check counts an unset hooksPath in a git repo as a change, but not outside a repo', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    expect(isoSetup($dir, ['--check' => true])[0])->toBe(0);

    isoGit($dir, 'init -q');
    expect(isoSetup($dir, ['--check' => true])[0])->toBe(1);

    isoSetup($dir, ['--yes' => true]);
    expect(isoSetup($dir, ['--check' => true])[0])->toBe(0);
});

it('shows a diff for a hand-edited hook, asks, and keeps the edit on no', function (string $path) {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    $edited = $this->read($dir, $path)."\n# local note\n";
    file_put_contents($dir.'/'.$path, $edited);

    expect(isoSetup($dir, ['--check' => true])[0])->toBe(1);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: '.$path)
        ->expectsOutputToContain('--- a/'.$path)
        ->expectsOutputToContain('+++ b/'.$path)
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, $path))->toBe($edited);
})->with(['.githooks/commit-msg', '.githooks/gitleaks-check', '.gitleaks.toml']);

it('restores an executable bit lost on a hook (reported, not silent)', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    chmod($dir.'/.githooks/commit-msg', 0644);

    expect(isoSetup($dir, ['--check' => true])[0])->toBe(1);
    isoSetup($dir, ['--yes' => true]);

    expect(fileperms($dir.'/.githooks/commit-msg') & 0111)->not->toBe(0);
});

// 6. Package-local skeleton
// =========================================================================

it('points a package at itself as the Testbench skeleton so Boost reads its own .ai', function () {
    $dir = $this->project('package');

    isoSetup($dir, ['--yes' => true]);

    $yaml = Yaml::parse($this->read($dir, 'testbench.yaml'));
    expect($yaml['laravel'])->toBe('./')
        ->and($yaml['providers'])->toBe([])
        ->and($yaml['env'])->toBe(['APP_DEBUG' => true]);
});

it('creates the directories Laravel needs under the package root, git-ignored', function () {
    $dir = $this->project('package');

    isoSetup($dir, ['--yes' => true]);

    foreach (['bootstrap/cache', 'storage/logs', 'storage/framework/cache', 'storage/framework/sessions', 'storage/framework/views'] as $path) {
        expect($this->read($dir, $path.'/.gitignore'))->toBe("*\n!.gitignore\n");
    }
});

it('keeps other testbench.yaml keys and env entries', function () {
    $dir = $this->project('package');
    isoPut($dir, 'testbench.yaml', "laravel: \"@testbench\"\nproviders:\n  - Example\\Package\\ServiceProvider\nenv:\n  APP_KEY: base64:abc\nworkbench:\n  install: true\n");

    isoSetup($dir, ['--yes' => true]);

    $yaml = Yaml::parse($this->read($dir, 'testbench.yaml'));
    expect($yaml['laravel'])->toBe('./')
        ->and($yaml['providers'])->toBe(['Example\\Package\\ServiceProvider'])
        ->and($yaml['env'])->toBe(['APP_KEY' => 'base64:abc', 'APP_DEBUG' => true])
        ->and($yaml['workbench'])->toBe(['install' => true]);
});

it('treats a custom laravel skeleton path as a hand edit', function () {
    $dir = $this->project('package');
    isoPut($dir, 'testbench.yaml', "laravel: ./skeleton\nproviders: []\n");
    $before = $this->read($dir, 'testbench.yaml');

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('edited by hand: testbench.yaml')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect($this->read($dir, 'testbench.yaml'))->toBe($before);
});

it('does not give an app a testbench skeleton', function () {
    $dir = $this->project('app');

    isoSetup($dir, ['--yes' => true]);

    expect(is_file($dir.'/testbench.yaml'))->toBeFalse()
        ->and(is_dir($dir.'/bootstrap/cache'))->toBeFalse();
});

// 7. Idempotence over every new file
// =========================================================================

it('is idempotent with the isolation files: second run no changes, check 0, no file touched', function (string $fixture, bool $ddev, bool $git) {
    $dir = $this->project($fixture, ddev: $ddev);
    isoPut($dir, '.env.example', "PAYMENTS_LIVE=false\nDB_CONNECTION=mysql\n");
    if ($git) {
        isoGit($dir, 'init -q');
    }
    isoSetup($dir, ['--yes' => true]);
    expect(is_file($dir.'/.githooks/commit-msg'))->toBeTrue('setup must have written the isolation files before idempotence means anything');
    $after = $this->snapshot($dir);

    $this->artisan('claude-skills:setup', ['--path' => $dir, '--yes' => true])
        ->expectsOutputToContain('No changes')
        ->assertExitCode(0);
    $this->artisan('claude-skills:setup', ['--path' => $dir, '--check' => true])
        ->expectsOutputToContain('No changes')
        ->assertExitCode(0);

    $now = array_filter($this->snapshot($dir), fn ($key) => ! str_starts_with($key, '.git/'), ARRAY_FILTER_USE_KEY);
    $after = array_filter($after, fn ($key) => ! str_starts_with($key, '.git/'), ARRAY_FILTER_USE_KEY);
    expect($now)->toBe($after);
})->with([
    'ddev app' => ['app', true, false],
    'host app' => ['app', false, false],
    'ddev app in git' => ['app', true, true],
    'ddev package' => ['package', true, false],
    'host package in git' => ['package', false, true],
]);

it('a changed live flag on rerun changes only phpunit.xml', function () {
    $dir = $this->project('app', ddev: true);
    isoSetup($dir, ['--yes' => true]);
    $before = $this->snapshot($dir);
    isoPut($dir, '.env', "NEWPROVIDER_LIVE=true\n");

    isoSetup($dir, ['--yes' => true]);

    $after = $this->snapshot($dir);
    $changed = array_keys(array_filter($after, fn ($sha, $path) => ($before[$path] ?? null) !== $sha, ARRAY_FILTER_USE_BOTH));
    sort($changed);
    expect($changed)->toBe(['.ai/claude-skills-setup.json', '.env', 'phpunit.xml']);
    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'NEWPROVIDER_LIVE', 'false');
});
