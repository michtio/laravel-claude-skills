<?php

declare(strict_types=1);

/**
 * The CI database image of an app on DDEV follows the database DDEV really runs: with no `database:`
 * block in `.ddev/config.yaml`, the setup asks the installed DDEV (the S9b reader) instead of assuming
 * an old default. Requirement R11. Skills-gaps row 181 (builder test).
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

/**
 * The database service image of the written workflow's gate job, or '' when there is none.
 */
function appDdevImage(string $dir): string
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));

    return (string) ($workflow['jobs']['gate']['services']['database']['image'] ?? '');
}

/**
 * An app on DDEV with no database block in .ddev/config.yaml and a MySQL-family connection.
 */
function appDdevProject(ProfileTestCase $test): string
{
    $dir = $test->project('app', ddev: true);
    $config = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.yaml')) ?: [];
    unset($config['database']);
    file_put_contents($dir.'/.ddev/config.yaml', Yaml::dump($config));
    $test->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    return $dir;
}

it('takes the CI database image from the installed DDEV when the app names no database', function () {
    $dir = appDdevProject($this);
    $this->fakeDdevDatabase(['type' => 'mariadb', 'version' => '11.8']);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(appDdevImage($dir))->toBe('mariadb:11.8');
})->group('R11');

it('follows the engine the installed DDEV reports for an app with no database block', function () {
    $dir = appDdevProject($this);
    $this->fakeDdevDatabase(['type' => 'mysql', 'version' => '8.4']);

    $this->setupRun($dir, ['--yes' => true]);

    expect(appDdevImage($dir))->toBe('mysql:8.4');
})->group('R11');

it('never assumes MariaDB 10.11 when the installed DDEV cannot be asked, and says so', function () {
    $dir = appDdevProject($this);
    $this->fakeDdevDatabase(null);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(appDdevImage($dir))->not->toBe('mariadb:10.11')
        ->and($output)->toContain('database: block');
})->group('R11');

it('does not ask DDEV when the app names its database in full', function () {
    $dir = appDdevProject($this);
    $config = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.yaml')) ?: [];
    $config['database'] = ['type' => 'mysql', 'version' => '8.0'];
    file_put_contents($dir.'/.ddev/config.yaml', Yaml::dump($config));
    $this->fakeDdevDatabase(false);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(appDdevImage($dir))->toBe('mysql:8.0');
})->group('R11');
