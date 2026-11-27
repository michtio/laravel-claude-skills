<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer), round 4: the database engine comes from the DDEV that is installed.
 * Contract: tests/S9b/CONTRACT.md section 14.
 *
 * DDEV's default database changes between versions (v1.25.6 prints mariadb:11.8), so no fixed number is right.
 * With `laravel.test_database: ddev` on a package the setup reads type and version through the injectable
 * Michtio\LaravelClaudeSkills\Setup\DdevDatabaseSource (bound in the container; the real one tries
 * `ddev describe -j`, then the default `ddev config --help` prints). These tests feed it values.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Symfony\Component\Yaml\Yaml;

/**
 * A DDEV package on test_database ddev with a ddev config body.
 */
function s9bR4Package($test, string $configBody, bool $ci = true): string
{
    $dir = $test->project('package', ddev: true);
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\n".$configBody);
    $test->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev', 'ci' => $ci]]);

    return $dir;
}

/**
 * The gate job of the written workflow.
 *
 * @return array<string, mixed>
 */
function s9bR4Job(string $dir): array
{
    return array_values(Yaml::parse((string) file_get_contents($dir.'/.github/workflows/claude-skills-gate.yml'))['jobs'])[0];
}

// 1. No database block: the reader decides
// =========================================================================

it('takes the engine from the reader: pins, hook, CI service', function (array $read, string $connection, string $image, string $nameKey, string $port) {
    $this->fakeDdevDatabase($read);
    $dir = s9bR4Package($this, '');

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $job = s9bR4Job($dir);
    $phpunit = (string) file_get_contents($dir.'/phpunit.xml.dist');
    $override = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.claude-skills.yaml'));

    expect($code)->toBe(0)
        ->and($job['services']['database']['image'])->toBe($image)
        ->and($job['services']['database']['env'][$nameKey])->toBe('package_test')
        ->and($phpunit)->toContain('<env name="DB_CONNECTION" value="'.$connection.'" force="true"/>')
        ->toContain('<server name="DB_CONNECTION" value="'.$connection.'"/>')
        ->and($override['web_environment'])->toContain('DB_PORT='.$port);
})->with([
    'mariadb 11.8' => [['type' => 'mariadb', 'version' => '11.8'], 'mariadb', 'mariadb:11.8', 'MARIADB_DATABASE', '3306'],
    'mariadb 10.11, an older DDEV' => [['type' => 'mariadb', 'version' => '10.11'], 'mariadb', 'mariadb:10.11', 'MARIADB_DATABASE', '3306'],
    'mysql 8.0' => [['type' => 'mysql', 'version' => '8.0'], 'mysql', 'mysql:8.0', 'MYSQL_DATABASE', '3306'],
    'postgres 17' => [['type' => 'postgres', 'version' => '17'], 'pgsql', 'postgres:17', 'POSTGRES_DB', '5432'],
]);

it('writes the hook for the engine it read', function () {
    $this->fakeDdevDatabase(['type' => 'postgres', 'version' => '17']);
    $dir = s9bR4Package($this, '');

    $this->setupRun($dir, ['--yes' => true]);
    $entry = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.claude-skills.yaml'))['hooks']['post-start'][0];

    expect($entry['service'])->toBe('db')
        ->and($entry['exec'])->toContain('psql')->toContain('package_test');
});

it('exits 1 asking for an explicit database block when nothing can be read, and writes nothing', function (bool $ci) {
    $this->fakeDdevDatabase(null);
    $dir = s9bR4Package($this, '', ci: $ci);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('database:')->toContain('.ddev/config.yaml')
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with(['ci on' => [true], 'ci off' => [false]]);

it('does not read anything when test_database is not ddev, so a missing ddev cannot break the default', function () {
    $this->fakeDdevDatabase(false);
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0);
});

it('plans only the difference when the installed DDEV later reports another version, never a hand edit', function () {
    $this->fakeDdevDatabase(['type' => 'mariadb', 'version' => '11.8']);
    $dir = s9bR4Package($this, '');
    $this->setupRun($dir, ['--yes' => true]);

    expect($this->setupRun($dir, ['--check' => true]))->toMatchArray([0 => 0]);

    $this->fakeDdevDatabase(['type' => 'mariadb', 'version' => '12.0']);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and($this->diffPaths($output))->toContain('.github/workflows/claude-skills-gate.yml');

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bR4Job($dir)['services']['database']['image'])->toBe('mariadb:12.0');
});

// 2. A block names the engine; the reader fills only a missing version
// =========================================================================

it('does not consult the reader for a block with type and version', function (string $type, string $version, string $connection, string $image) {
    $this->fakeDdevDatabase(false);
    $dir = s9bR4Package($this, "database:\n    type: {$type}\n    version: \"{$version}\"\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(s9bR4Job($dir)['services']['database']['image'])->toBe($image)
        ->and((string) file_get_contents($dir.'/phpunit.xml.dist'))->toContain('<env name="DB_CONNECTION" value="'.$connection.'" force="true"/>');
})->with([
    'mysql 8.0' => ['mysql', '8.0', 'mysql', 'mysql:8.0'],
    'mariadb 11.8' => ['mariadb', '11.8', 'mariadb', 'mariadb:11.8'],
    'postgres 16' => ['postgres', '16', 'pgsql', 'postgres:16'],
]);

it('reads the version of a version-less block when the reader reports the same type', function (string $type, string $read, string $image) {
    $this->fakeDdevDatabase(['type' => $type, 'version' => $read]);
    $dir = s9bR4Package($this, "database:\n    type: {$type}\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(s9bR4Job($dir)['services']['database']['image'])->toBe($image);
})->with([
    'mysql' => ['mysql', '8.0', 'mysql:8.0'],
    'mariadb' => ['mariadb', '11.8', 'mariadb:11.8'],
]);

it('exits 1 asking for an explicit version when a version-less block names another type than the reader reports, or nothing is read', function (?array $read) {
    $this->fakeDdevDatabase($read);
    $dir = s9bR4Package($this, "database:\n    type: mysql\n");
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('version')->toContain('.ddev/config.yaml')
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with([
    'the default is another engine' => [['type' => 'mariadb', 'version' => '11.8']],
    'unreadable' => [null],
]);

it('keeps the postgres default for a version-less postgres block, never consulting the reader', function () {
    $this->fakeDdevDatabase(false);
    $dir = s9bR4Package($this, "database:\n    type: postgres\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(s9bR4Job($dir)['services']['database']['image'])->toBe('postgres:17')
        ->and((string) file_get_contents($dir.'/phpunit.xml.dist'))->toContain('<env name="DB_CONNECTION" value="pgsql" force="true"/>');
});

// 3. "laravel": [] stays accepted
// =========================================================================

it('accepts an empty laravel list (PHP encodes an empty array that way) as no options', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => []]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('Invalid profile')
        ->and(array_keys(Profile::load($dir)->laravel()))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci'])
        ->and($code)->toBe(1);
});

it('accepts an empty laravel object too', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, '{"version": 1, "laravel": {}}'."\n");

    expect($this->setupRun($dir, ['--check' => true])[1])->not->toContain('Invalid profile');
});

it('refuses a non-empty laravel list, naming laravel, and writes nothing', function (array $list) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => $list]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: laravel')
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with([
    'one item' => [['ci']],
    'two items' => [[true, false]],
]);
