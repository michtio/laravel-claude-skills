<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): a fresh Testbench package passes its own gate.
 * Requirements R8, R10. Skills-gaps rows 9, 10, 25 (paths part).
 * Contract: tests/S9b/CONTRACT.md section 4.
 *
 * A new package has an empty src, no tests directory and no Pest file: PHPStan failed with
 * "Path src does not exist" or "No files found to analyse", and `vendor/bin/pest` with "The test
 * directory does not exist". The real run of `composer test` is tests/gate/test_s9b_ddev.py.
 */

use Symfony\Component\Yaml\Yaml;

/**
 * Put Larastan into composer.json so the setup manages phpstan.neon.
 */
function s9bWithLarastan(string $dir): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer['require-dev']['larastan/larastan'] = '^3.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * Put Pest into composer.json: a Pest package is the one that gets tests/Pest.php (round 3).
 */
function s9bWithPest(string $dir): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer['require-dev']['pestphp/pest'] = '^4.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * The paths of the written phpstan.neon.
 *
 * @return list<string>
 */
function s9bPhpstanPaths(string $dir): array
{
    return Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'];
}

// 1. tests/Pest.php
// =========================================================================

it('plans tests/Pest.php for a package that has none, as a created file in the plan', function () {
    $dir = $this->project('package');
    s9bWithPest($dir);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('--- /dev/null')
        ->toContain('+++ b/tests/Pest.php')
        ->and(file_exists($dir.'/tests/Pest.php'))->toBeFalse();
});

it('writes a Pest.php that extends Testbench, is house style and parses', function () {
    $dir = $this->project('package');
    s9bWithPest($dir);

    $this->setupRun($dir, ['--yes' => true]);
    $pest = (string) file_get_contents($dir.'/tests/Pest.php');

    expect($pest)->toStartWith('<?php')
        ->toContain('declare(strict_types=1);')
        ->toContain('Orchestra\Testbench\TestCase')
        ->toContain('extend(')
        // Pint (fully_qualified_strict_types) wants the class imported, not written out inline.
        ->toMatch('/^use Orchestra\\\\Testbench\\\\TestCase;$/m');

    $lint = proc_open([PHP_BINARY, '-l', $dir.'/tests/Pest.php'], [1 => ['pipe', 'w'], 2 => ['pipe', 'w']], $pipes);
    $stdout = stream_get_contents($pipes[1]);
    expect(proc_close($lint))->toBe(0, $stdout);
});

it('never replaces or changes an existing tests/Pest.php, and never calls it a hand edit', function () {
    $dir = $this->project('package');
    s9bWithPest($dir);
    mkdir($dir.'/tests');
    file_put_contents($dir.'/tests/Pest.php', "<?php\n\n// mine\n");

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($this->read($dir, 'tests/Pest.php'))->toBe("<?php\n\n// mine\n")
        ->and($output)->not->toContain('tests/Pest.php');
});

it('leaves a Pest.php the person edited after the first run alone: No changes, exit 0', function () {
    $dir = $this->project('package');
    s9bWithPest($dir);
    $this->setupRun($dir, ['--yes' => true]);
    file_put_contents($dir.'/tests/Pest.php', (string) file_get_contents($dir.'/tests/Pest.php')."\n// team note\n");

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($output)->not->toContain('edited by hand');
});

it('gives an app no tests/Pest.php', function () {
    $dir = $this->project('app');

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/tests/Pest.php'))->toBeFalse();
});

// 2. phpstan.neon paths
// =========================================================================

it('lists src and tests for a Pest package, whose Pest.php is created in the same run', function () {
    $dir = $this->project('package');
    s9bWithLarastan($dir);
    s9bWithPest($dir);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpstanPaths($dir))->toBe(['src', 'tests']);
});

it('never lists a directory that does not exist, so an empty or missing src cannot fail the gate on its path', function () {
    $dir = $this->project('package');
    unlink($dir.'/src/.gitkeep');
    rmdir($dir.'/src');
    s9bWithLarastan($dir);
    s9bWithPest($dir);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpstanPaths($dir))->toBe(['tests']);

    foreach (s9bPhpstanPaths($dir) as $path) {
        expect(is_dir($dir.'/'.$path))->toBeTrue($path);
    }
});

it('adds workbench/app when it exists, after src and tests', function () {
    $dir = $this->project('package');
    mkdir($dir.'/workbench/app', 0777, true);
    s9bWithLarastan($dir);
    s9bWithPest($dir);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpstanPaths($dir))->toBe(['src', 'tests', 'workbench/app']);
});

it('lists the tests directory of a package that already has one, without planning Pest.php twice', function () {
    $dir = $this->project('package');
    mkdir($dir.'/tests');
    file_put_contents($dir.'/tests/Pest.php', "<?php\n");
    s9bWithLarastan($dir);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpstanPaths($dir))->toBe(['src', 'tests']);
});

it('keeps the paths stable on a rerun: --check exits 0, No changes', function () {
    $dir = $this->project('package');
    s9bWithLarastan($dir);
    s9bWithPest($dir);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('does not change the paths of an app', function () {
    $dir = $this->project('app');
    mkdir($dir.'/app');
    s9bWithLarastan($dir);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpstanPaths($dir))->toBe(['app']);
});
