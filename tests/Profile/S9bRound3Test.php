<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer), round 3: the PR review findings.
 * Contract: tests/S9b/CONTRACT.md section 13.
 *
 *   F2  tests/Pest.php only for a Pest package that picks no base case yet; PHPStan `tests` follows it
 *   F1  a trailing newline is not a valid pin value or PHP version
 *   3   the effective options print in one canonical order
 *   4   a symlinked tests folder or CLAUDE.md is refused at plan time
 *   5   a hand-written server twin is not dropped silently when a pin moves to env
 *   6   with test_database ddev the CI service and the pins follow the DDEV database type and version
 *   7   the person's own DB_* in .ddev/config.yaml web_environment is not silently replaced
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Symfony\Component\Yaml\Yaml;

/**
 * Add packages to require-dev of a temp project.
 *
 * @param array<string, string> $dev
 */
function s9bR3Composer(string $dir, array $dev): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);

    foreach ($dev as $package => $version) {
        $composer['require-dev'][$package] = $version;
    }

    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * The paths of the written phpstan.neon.
 *
 * @return list<string>
 */
function s9bR3Paths(string $dir): array
{
    return Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'];
}

/**
 * A fresh temp directory outside the project.
 */
function s9bR3Outside(): string
{
    $dir = sys_get_temp_dir().'/lcs-s9b-out-'.bin2hex(random_bytes(6));
    mkdir($dir, 0777, true);

    return $dir;
}

/**
 * Remove a directory tree.
 */
function s9bR3Remove(string $dir): void
{
    foreach (scandir($dir) ?: [] as $entry) {
        if ($entry === '.' || $entry === '..') {
            continue;
        }

        is_dir($dir.'/'.$entry) && ! is_link($dir.'/'.$entry) ? s9bR3Remove($dir.'/'.$entry) : unlink($dir.'/'.$entry);
    }

    rmdir($dir);
}

// F2. Pest.php only for a Pest package that has no base case yet
// =========================================================================

it('plans no Pest.php and lists only src for a PHPUnit-only package', function () {
    $dir = $this->project('package');
    s9bR3Composer($dir, ['larastan/larastan' => '^3.0']);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/tests/Pest.php'))->toBeFalse()
        ->and($output)->not->toContain('tests/Pest.php')
        ->and(s9bR3Paths($dir))->toBe(['src']);
});

it('plans no Pest.php for a Pest package whose tests already call uses()', function (string $file, string $content) {
    $dir = $this->project('package');
    s9bR3Composer($dir, ['pestphp/pest' => '^4.0', 'larastan/larastan' => '^3.0']);
    mkdir(dirname($dir.'/'.$file), 0777, true);
    file_put_contents($dir.'/'.$file, $content);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/tests/Pest.php'))->toBeFalse()
        ->and($output)->not->toContain('tests/Pest.php')
        ->and(s9bR3Paths($dir))->toBe(['src', 'tests']);
})->with([
    'a feature file' => ['tests/Feature/ExampleTest.php', "<?php\n\nuses(Tests\\TestCase::class);\n\nit('works', fn () => expect(true)->toBeTrue());\n"],
    'a nested folder' => ['tests/Unit/Deep/ExampleTest.php', "<?php\n\nuses(Tests\\TestCase::class)->in(__DIR__);\n"],
]);

it('plans no Pest.php for a Pest package that has tests/TestCase.php', function () {
    $dir = $this->project('package');
    s9bR3Composer($dir, ['pestphp/pest' => '^4.0']);
    mkdir($dir.'/tests');
    file_put_contents($dir.'/tests/TestCase.php', "<?php\n\nnamespace Tests;\n\nabstract class TestCase extends \\Orchestra\\Testbench\\TestCase\n{\n}\n");

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/tests/Pest.php'))->toBeFalse();
});

it('keeps today behavior for a plain Pest package: Pest.php planned, tests listed', function (bool $withTestsDir) {
    $dir = $this->project('package');
    s9bR3Composer($dir, ['pestphp/pest' => '^4.0', 'larastan/larastan' => '^3.0']);

    if ($withTestsDir) {
        mkdir($dir.'/tests');
        file_put_contents($dir.'/tests/ExampleTest.php', "<?php\n\nnamespace Tests;\n\nclass ExampleTest extends \\Orchestra\\Testbench\\TestCase\n{\n}\n");
    }

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->toContain('+++ b/tests/Pest.php')
        ->and(file_exists($dir.'/tests/Pest.php'))->toBeTrue()
        ->and(s9bR3Paths($dir))->toBe(['src', 'tests'])
        ->and($this->setupRun($dir, ['--check' => true])[0])->toBe(0);
})->with([
    'no tests folder' => [false],
    'a PHPUnit class in tests' => [true],
]);

it('lists tests for a PHPUnit-only package that already has a tests folder with a Pest.php', function () {
    $dir = $this->project('package');
    mkdir($dir.'/tests');
    file_put_contents($dir.'/tests/Pest.php', "<?php\n");
    s9bR3Composer($dir, ['larastan/larastan' => '^3.0']);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bR3Paths($dir))->toBe(['src', 'tests']);
});

// F1. A trailing newline is not a valid value
// =========================================================================

it('refuses a value with a trailing newline, naming the dotted path, writing nothing', function (array $laravel, string $path) {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => $laravel]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: '.$path)
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with([
    'php_matrix item' => [['php_matrix' => ["8.4\n"]], 'laravel.php_matrix.0'],
    'second php_matrix item' => [['php_matrix' => ['8.3', "8.4\n"]], 'laravel.php_matrix.1'],
    'pin value' => [['test_pins' => ['SESSION_DRIVER' => "file\n"]], 'laravel.test_pins.SESSION_DRIVER'],
    'env with a newline' => [['test_pins' => ['SESSION_DRIVER' => "env\n"]], 'laravel.test_pins.SESSION_DRIVER'],
]);

// 3. One canonical order for the printed options
// =========================================================================

it('prints the effective options in one canonical order, whatever the profile sets', function (array $laravel) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => $laravel]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    $order = ['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci', 'test_database', 'php_matrix', 'test_pins'];
    preg_match_all('/^  ([a-z_]+): /m', $output, $found);
    $seen = array_values(array_filter($found[1], static fn (string $key): bool => in_array($key, $order, true)));

    expect($seen)->toBe($order);
})->with([
    'only php_matrix and test_pins' => [['test_pins' => ['SESSION_DRIVER' => 'file'], 'php_matrix' => ['8.3', '8.4']]],
    'pins first, then ci' => [['test_pins' => ['CACHE_STORE' => 'env'], 'ci' => true]],
    'every key, scrambled' => [['test_pins' => ['MAIL_MAILER' => 'log'], 'ci' => true, 'php_matrix' => 'auto', 'runner' => 'host', 'test_database' => 'auto', 'monitoring' => 'none', 'house_style' => false, 'phpstan_level' => 6]],
    'none set' => [[]],
]);

it('gives Profile::effective the same order', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file'], 'php_matrix' => ['8.3']]]);

    $effective = Profile::load($dir)->effective();

    expect(array_keys($effective))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci', 'test_database', 'php_matrix', 'test_pins', 'ci_services'])
        ->and($effective['ci_services'])->toBe([]);
});

// 4. Symlinks are refused at plan time
// =========================================================================

it('refuses a symlinked tests folder, naming it, writing nothing and leaving the outside target alone', function () {
    $dir = $this->project('package');
    s9bR3Composer($dir, ['pestphp/pest' => '^4.0']);
    $outside = s9bR3Outside();
    symlink($outside, $dir.'/tests');
    $projectBefore = $this->snapshot($dir);
    $outsideBefore = $this->snapshot($outside);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('tests')->toContain('symlink')
            ->not->toContain('+++ b/tests/Pest.php')
            ->and($this->snapshot($outside))->toBe($outsideBefore)
            ->and($this->snapshot($dir))->toBe($projectBefore);
    }

    expect(file_exists($outside.'/Pest.php'))->toBeFalse();
    unlink($dir.'/tests');
    s9bR3Remove($outside);
});

it('refuses a symlinked CLAUDE.md, naming it, writing nothing', function (bool $dangling) {
    $dir = $this->project('app');
    unlink($dir.'/CLAUDE.md');
    $outside = s9bR3Outside();
    file_put_contents($outside.'/target.md', 'OUTSIDE');
    symlink($dangling ? $outside.'/missing.md' : $outside.'/target.md', $dir.'/CLAUDE.md');
    $projectBefore = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('CLAUDE.md')->toContain('symlink')
            ->not->toContain('OUTSIDE')
            ->and(file_get_contents($outside.'/target.md'))->toBe('OUTSIDE');
    }

    expect(is_link($dir.'/CLAUDE.md'))->toBeTrue();
    unlink($dir.'/CLAUDE.md');
    s9bR3Remove($outside);
})->with(['a file outside' => [false], 'a dangling link' => [true]]);

// 5. A hand-written server twin is not dropped silently
// =========================================================================

/**
 * Write a phpunit.xml with one hand-written server twin.
 */
function s9bR3Phpunit(string $dir, string $value): void
{
    file_put_contents($dir.'/phpunit.xml', <<<XML
        <?xml version="1.0" encoding="UTF-8"?>
        <phpunit bootstrap="vendor/autoload.php">
            <testsuites>
                <testsuite name="Unit">
                    <directory>tests/Unit</directory>
                </testsuite>
            </testsuites>
            <php>
                <server name="QUEUE_CONNECTION" value="{$value}"/>
            </php>
        </phpunit>

        XML);
}

it('reports a non-standard server twin as edited by hand when the pin is env', function () {
    $dir = $this->project('app');
    s9bR3Phpunit($dir, 'redis');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['QUEUE_CONNECTION' => 'env']]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpunit.xml');
});

it('does not call the standard server twin a hand edit when the pin is env', function () {
    $dir = $this->project('app');
    s9bR3Phpunit($dir, 'sync');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['QUEUE_CONNECTION' => 'env']]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('edited by hand');
});

it('reports a twin changed by hand after the setup wrote it, when the pin then moves to env', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['QUEUE_CONNECTION' => 'database']]]);
    $this->setupRun($dir, ['--yes' => true]);
    $path = $dir.'/phpunit.xml';
    file_put_contents($path, str_replace('<server name="QUEUE_CONNECTION" value="database"/>', '<server name="QUEUE_CONNECTION" value="redis"/>', (string) file_get_contents($path)));
    expect((string) file_get_contents($path))->toContain('value="redis"');

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['QUEUE_CONNECTION' => 'env']]]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpunit.xml');
});

// 6. Local and CI test the same engine
// =========================================================================

/**
 * A DDEV package on test_database ddev with a ddev config body, CI on.
 */
function s9bR3DdevPackage($test, string $configBody): string
{
    $dir = $test->project('package', ddev: true);
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\n".$configBody);
    $test->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev', 'ci' => true]]);

    return $dir;
}

it('follows the database DDEV reports when .ddev/config.yaml has no database block: CI service and pins', function () {
    $dir = s9bR3DdevPackage($this, '');

    $this->setupRun($dir, ['--yes' => true]);
    $job = array_values(Yaml::parse((string) file_get_contents($dir.'/.github/workflows/claude-skills-gate.yml'))['jobs'])[0];
    $phpunit = (string) file_get_contents($dir.'/phpunit.xml.dist');

    // The default reader of ProfileTestCase reports mariadb 11.8 (DDEV v1.25.6's default); no fixed number is pinned here.
    expect($job['services']['database']['image'])->toBe('mariadb:11.8')
        ->and($job['services']['database']['env']['MARIADB_DATABASE'])->toBe('package_test')
        ->and($phpunit)->toContain('<env name="DB_CONNECTION" value="mariadb" force="true"/>')
        ->toContain('<server name="DB_CONNECTION" value="mariadb"/>');
});

it('keeps the local connection and the CI engine the same for every DDEV database block', function (string $body) {
    $dir = s9bR3DdevPackage($this, $body);

    $this->setupRun($dir, ['--yes' => true]);
    $job = array_values(Yaml::parse((string) file_get_contents($dir.'/.github/workflows/claude-skills-gate.yml'))['jobs'])[0];
    preg_match('/<env name="DB_CONNECTION" value="([a-z]+)" force="true"\/>/', (string) file_get_contents($dir.'/phpunit.xml.dist'), $match);
    $engine = explode(':', $job['services']['database']['image'])[0];

    expect(['mysql' => 'mysql', 'mariadb' => 'mariadb', 'pgsql' => 'postgres'][$match[1]] ?? null)->toBe($engine);
})->with([
    'no block' => [''],
    'mysql 8.0' => ["database:\n    type: mysql\n    version: \"8.0\"\n"],
    'mariadb 11.8' => ["database:\n    type: mariadb\n    version: \"11.8\"\n"],
    'postgres 16' => ["database:\n    type: postgres\n    version: \"16\"\n"],
]);

// 7. The person's own DB_* in web_environment
// =========================================================================

it('does not silently replace the person\'s own DB key in web_environment', function (string $name, string $value) {
    $dir = $this->project('package', ddev: true);
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\nweb_environment:\n    - {$name}={$value}\n");
    $config = $this->read($dir, '.ddev/config.yaml');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);
    $before = $this->snapshot($dir);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, '.ddev/config.yaml'))->toBe($config);

    if ($code !== 0) {
        // A reported conflict: it names the key, and nothing was written.
        expect($output)->toContain($name)->and($this->snapshot($dir))->toBe($before);

        return;
    }

    // Kept: the override leaves that key to the person's own entry.
    $override = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.claude-skills.yaml'))['web_environment'] ?? [];

    foreach ($override as $entry) {
        expect($entry)->not->toStartWith($name.'=');
    }
})->with([
    'host' => ['DB_HOST', 'my-database'],
    'username' => ['DB_USERNAME', 'someone'],
    'password' => ['DB_PASSWORD', 'secret'],
    'port' => ['DB_PORT', '3307'],
]);

it('still writes the DDEV credentials for the keys the person did not set', function () {
    $dir = $this->project('package', ddev: true);
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\nweb_environment:\n    - DB_HOST=my-database\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_database' => 'ddev']]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    if ($code !== 0) {
        expect(true)->toBeTrue();

        return;
    }

    $override = Yaml::parse((string) file_get_contents($dir.'/.ddev/config.claude-skills.yaml'))['web_environment'] ?? [];

    expect($override)->toContain('DB_USERNAME=db')->toContain('DB_PASSWORD=db');
});
