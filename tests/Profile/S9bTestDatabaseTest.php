<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): `laravel.test_database`.
 * Requirements R8, R10, R11, R23. Skills-gaps row 6.
 * Contract: tests/S9b/CONTRACT.md section 1.
 *
 * `ddev` gives a Testbench package what a DDEV app already gets: a `<slug>_test` database on
 * DDEV's db service (created by the post-start hook), forced pins for it, and a database
 * service in the CI workflow. The real run against MySQL is tests/gate/test_s9b_ddev.py.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

const S9B_HOOK = '.ddev/config.claude-skills.yaml';

/**
 * Write a DDEV database block into the project's .ddev/config.yaml.
 */
function s9bDdevDatabase(string $dir, string $type, string $version): void
{
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\ndatabase:\n    type: {$type}\n    version: \"{$version}\"\n");
}

/**
 * A package on DDEV with `laravel.test_database: ddev` written, not yet applied.
 *
 * @param array<string, mixed> $laravel
 */
function s9bPackage($test, array $laravel = [], ?string $dbType = null, string $dbVersion = '8.0'): string
{
    $dir = $test->project('package', ddev: true);

    if ($dbType !== null) {
        s9bDdevDatabase($dir, $dbType, $dbVersion);
    }

    $test->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev'] + $laravel]);

    return $dir;
}

/**
 * The forced `<env>` and the `<server>` twin for a name: [env value, env force, server value].
 *
 * @return array{0: string|null, 1: string|null, 2: string|null}
 */
function s9bPin(string $dir, string $name): array
{
    $xml = simplexml_load_string((string) file_get_contents($dir.'/phpunit.xml.dist'));
    $env = [null, null];
    $server = null;

    foreach ($xml->php->env ?? [] as $element) {
        if ((string) $element['name'] === $name) {
            $env = [(string) $element['value'], isset($element['force']) ? (string) $element['force'] : null];
        }
    }

    foreach ($xml->php->server ?? [] as $element) {
        if ((string) $element['name'] === $name) {
            $server = (string) $element['value'];
        }
    }

    return [$env[0], $env[1], $server];
}

// 1. The profile key
// =========================================================================

it('accepts auto and ddev and keeps the S7 defaults array of five keys when the key is not set', function () {
    $dir = $this->project('package');

    expect(array_keys(Profile::load($dir)->laravel()))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci']);

    foreach (['auto', 'ddev'] as $value) {
        $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => $value]]);

        expect(Profile::load($dir)->laravel()['test_database'])->toBe($value);
    }
});

it('refuses a test_database that is not auto or ddev, naming the dotted path, and writes nothing', function (mixed $value) {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => $value]]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: laravel.test_database')
            ->and($this->snapshot($dir))->toBe($before);
    }

    expect(fn () => Profile::load($dir))->toThrow(ProfileException::class);
})->with([
    'mysql' => ['mysql'],
    'memory' => ['memory'],
    'true' => [true],
    'a number' => [1],
    'null' => [null],
    'empty string' => [''],
]);

it('does not call the key unknown', function () {
    $dir = s9bPackage($this);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('Ignoring unknown profile key: laravel.test_database');
});

// 2. A package gets the DDEV test database
// =========================================================================

it('writes the DDEV hook for a package on mysql, in the db service, for <slug>_test', function () {
    $dir = s9bPackage($this, dbType: 'mysql');

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0);

    $raw = (string) file_get_contents($dir.'/'.S9B_HOOK);
    $config = Yaml::parse($raw);
    $entry = $config['hooks']['post-start'][0];

    expect($raw)->not->toContain('exec-host')
        ->and($entry['service'])->toBe('db')
        ->and($entry['exec'])->toContain('CREATE DATABASE IF NOT EXISTS package_test')
        ->toContain('GRANT ALL')
        ->and($output)->not->toContain('must exist');
});

it('lets the package suite reach the db service with DDEV credentials, from the override only', function () {
    $dir = s9bPackage($this, dbType: 'mysql');
    $this->setupRun($dir, ['--yes' => true]);

    $environment = Yaml::parse((string) file_get_contents($dir.'/'.S9B_HOOK))['web_environment'] ?? [];

    expect($environment)->toContain('DB_HOST=db')
        ->toContain('DB_PORT=3306')
        ->toContain('DB_USERNAME=db')
        ->toContain('DB_PASSWORD=db');

    // Host, port and credentials are never forced in phpunit: CI sets its own (127.0.0.1) in the job.
    foreach (['DB_HOST', 'DB_PORT', 'DB_USERNAME', 'DB_PASSWORD'] as $name) {
        expect((string) file_get_contents($dir.'/phpunit.xml.dist'))->not->toContain('name="'.$name.'"');
    }
});

it('pins the package suite to <slug>_test on the DDEV connection, forced, with server twins', function (string $type, string $version, string $connection, string $port) {
    $dir = s9bPackage($this, dbType: $type, dbVersion: $version);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPin($dir, 'DB_CONNECTION'))->toBe([$connection, 'true', $connection])
        ->and(s9bPin($dir, 'DB_DATABASE'))->toBe(['package_test', 'true', 'package_test'])
        ->and(s9bPin($dir, 'DB_URL'))->toBe(['', 'true', ''])
        ->and(Yaml::parse((string) file_get_contents($dir.'/'.S9B_HOOK))['web_environment'])->toContain('DB_PORT='.$port);
})->with([
    'mysql' => ['mysql', '8.0', 'mysql', '3306'],
    'mariadb' => ['mariadb', '11.8', 'mariadb', '3306'],
    'postgres' => ['postgres', '16', 'pgsql', '5432'],
]);

it('uses the psql hook for a package on postgres, never exec-host', function () {
    $dir = s9bPackage($this, dbType: 'postgres', dbVersion: '16');

    $this->setupRun($dir, ['--yes' => true]);

    $raw = (string) file_get_contents($dir.'/'.S9B_HOOK);
    $entry = Yaml::parse($raw)['hooks']['post-start'][0];

    expect($raw)->not->toContain('exec-host')
        ->and($entry['service'])->toBe('db')
        ->and($entry['exec'])->toContain('PGPASSWORD=db psql')
        ->toContain('package_test');
});

it('keeps the other pins and the live flags forced as before', function () {
    $dir = $this->project('package', ddev: true);
    file_put_contents($dir.'/.env.example', "PAYMENTS_LIVE=true\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPin($dir, 'APP_ENV')[0])->toBe('testing')
        ->and(s9bPin($dir, 'SESSION_DRIVER'))->toBe(['array', 'true', null])
        ->and(s9bPin($dir, 'PAYMENTS_LIVE'))->toBe(['false', 'true', 'false']);
});

it('reports No changes on a rerun and exits 0 with --check', function () {
    $dir = s9bPackage($this);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('plans nothing about the database for a package without the key, as in S6', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'auto']]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/'.S9B_HOOK))->toBeFalse()
        ->and(s9bPin($dir, 'DB_CONNECTION'))->toBe(['sqlite', 'true', 'sqlite'])
        ->and(s9bPin($dir, 'DB_DATABASE'))->toBe([':memory:', 'true', ':memory:']);
});

it('is a no-op for an app on DDEV: the plan is the one auto gives', function () {
    $auto = $this->project('app', ddev: true);
    $ddev = $this->project('app', ddev: true);
    $this->writeProfile($ddev, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    $this->writeProfile($auto, ['version' => 1, 'laravel' => ['test_database' => 'auto']]);

    $this->setupRun($auto, ['--yes' => true]);
    $this->setupRun($ddev, ['--yes' => true]);

    foreach ([S9B_HOOK, 'phpunit.xml', 'composer.json'] as $file) {
        expect($this->read($ddev, $file))->toBe($this->read($auto, $file), $file);
    }
});

// 3. Without DDEV there is nothing to create the database in
// =========================================================================

it('stops with exit 1 naming laravel.test_database when the project does not run on DDEV, and writes nothing', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('laravel.test_database')
            ->toContain('DDEV')
            ->and($this->snapshot($dir))->toBe($before);
    }
});

it('stops the same way when the profile runner is host on a project that has .ddev', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev', 'runner' => 'host']]);
    $before = $this->snapshot($dir);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('laravel.test_database')
        ->and($this->snapshot($dir))->toBe($before);
});

// 4. Rerun applies only the difference
// =========================================================================

it('removes the hook and goes back to sqlite when the key is removed, without calling it a hand edit', function () {
    $dir = s9bPackage($this, dbType: 'mysql');
    $this->setupRun($dir, ['--yes' => true]);

    $this->writeProfile($dir, ['version' => 1]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and($this->diffPaths($output))->toContain(S9B_HOOK, 'phpunit.xml.dist');

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/'.S9B_HOOK))->toBeFalse()
        ->and(s9bPin($dir, 'DB_CONNECTION'))->toBe(['sqlite', 'true', 'sqlite'])
        ->and($this->setupRun($dir, ['--check' => true])[0])->toBe(0);
});

it('adds the hook to a package that was set up before the key existed', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1]);
    $this->setupRun($dir, ['--yes' => true]);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and($this->diffPaths($output))->toContain(S9B_HOOK);
});

// 5. The CI workflow gets the database service, as for an app
// =========================================================================

/**
 * The workflow's gate job.
 *
 * @return array<string, mixed>
 */
function s9bGateJob(string $dir): array
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));

    return array_values($workflow['jobs'])[0];
}

it('adds the database service and its job environment to the package workflow, the name quoted', function (string $type, string $version, string $image, string $nameKey, string $port) {
    $dir = s9bPackage($this, ['ci' => true], dbType: $type, dbVersion: $version);

    $this->setupRun($dir, ['--yes' => true]);
    $job = s9bGateJob($dir);
    $raw = (string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW);

    expect($job['services']['database']['image'])->toBe($image)
        ->and($job['services']['database']['env'][$nameKey])->toBe('package_test')
        ->and($raw)->toMatch('/'.$nameKey.': [\'"]package_test[\'"]/')
        ->and((string) $job['env']['DB_HOST'])->toBe('127.0.0.1')
        ->and((string) $job['env']['DB_PORT'])->toBe($port);
})->with([
    'mysql' => ['mysql', '8.0', 'mysql:8.0', 'MYSQL_DATABASE', '3306'],
    'postgres' => ['postgres', '16', 'postgres:16', 'POSTGRES_DB', '5432'],
]);

it('keeps a package workflow without a database service when test_database is not ddev', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bGateJob($dir))->not->toHaveKey('services');
});
