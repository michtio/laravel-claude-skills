<?php

declare(strict_types=1);

/**
 * The DDEV test-database hook for PostgreSQL projects (beyond the S6b gate, which
 * pins the MySQL form): psql in the db container, an idempotent create through
 * \gexec, DDEV's default credentials, never exec-host.
 */

use Illuminate\Support\Facades\Artisan;
use Michtio\LaravelClaudeSkills\Setup\Planners\DdevDatabasePlanner;
use Symfony\Component\Yaml\Yaml;

it('builds an idempotent psql command for pgsql', function () {
    $shell = (new DdevDatabasePlanner())->shell('pgsql', 'shop_test');

    expect($shell)
        ->toContain('psql -v ON_ERROR_STOP=1 -U db -d postgres')
        ->toContain('PGPASSWORD=db')
        ->toContain("SELECT 'CREATE DATABASE shop_test' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'shop_test')\\gexec")
        ->toContain('GRANT ALL PRIVILEGES ON DATABASE shop_test TO db;')
        ->not->toContain('IF NOT EXISTS shop_test');
});

it('writes the pgsql hook for a DDEV app on pgsql, in the db service and never on the host', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.env', "DB_CONNECTION=pgsql\n");

    expect(Artisan::call('claude-skills:setup', ['--path' => $dir, '--yes' => true]))->toBe(0);

    $raw = (string) file_get_contents($dir.'/'.DdevDatabasePlanner::PATH);
    $entry = Yaml::parse($raw)['hooks']['post-start'][0];

    expect($raw)->not->toContain('exec-host')
        ->and($entry['service'])->toBe('db')
        ->and($entry['exec'])->toBe((new DdevDatabasePlanner())->shell('pgsql', 'app_test'));
});

it('keeps the MySQL form for mysql and mariadb and writes nothing for other connections', function () {
    $planner = new DdevDatabasePlanner();

    expect($planner->shell('mariadb', 'x_test'))->toContain('CREATE DATABASE IF NOT EXISTS x_test')->toContain('GRANT ALL')
        ->and($planner->shell('mysql', 'x_test'))->toContain('mysql -uroot -proot')
        ->and($planner->shell('sqlsrv', 'x_test'))->toBeNull();
});
