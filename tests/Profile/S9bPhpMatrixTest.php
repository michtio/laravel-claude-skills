<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): `laravel.php_matrix` in the CI workflow.
 * Requirements R11, R23. Skills-gaps row 8.
 * Contract: tests/S9b/CONTRACT.md section 3.
 *
 * A package defaults to every PHP minor from the composer floor (require.php) to the latest the
 * setup knows; an app keeps its single version. A list in the profile wins for both.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

/**
 * Put a PHP constraint into require.php of the project.
 */
function s9bRequirePhp(string $dir, string $constraint): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer['require']['php'] = $constraint;
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * The gate job of the written workflow.
 *
 * @return array<string, mixed>
 */
function s9bMatrixJob(string $dir): array
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));

    return array_values($workflow['jobs'])[0];
}

/**
 * The php-version value of the setup-php step.
 */
function s9bSetupPhp(array $job): mixed
{
    foreach ($job['steps'] as $step) {
        if (str_starts_with((string) ($step['uses'] ?? ''), 'shivammathur/setup-php@')) {
            return $step['with']['php-version'] ?? null;
        }
    }

    return null;
}

it('defaults a package to every minor from the require.php floor up, as strings, one matrix job', function () {
    $dir = $this->project('package');
    s9bRequirePhp($dir, '^8.3');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);
    $job = s9bMatrixJob($dir);
    $versions = $job['strategy']['matrix']['php'];

    expect($versions)->toBeArray()
        ->and($versions[0])->toBe('8.3')
        ->and($versions)->toContain('8.4', '8.5')
        ->and(array_values(array_unique($versions)))->toBe($versions);

    foreach ($versions as $position => $version) {
        expect($version)->toBeString()->toMatch('/^8\.\d+$/')
            ->and((int) substr($version, 2))->toBe(3 + $position);
    }

    expect($job['strategy']['fail-fast'])->toBeFalse()
        ->and(s9bSetupPhp($job))->toBe('${{ matrix.php }}');
});

it('starts a package matrix at the floor: ^8.4 has no 8.3', function () {
    $dir = $this->project('package');
    s9bRequirePhp($dir, '^8.4');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);
    $versions = s9bMatrixJob($dir)['strategy']['matrix']['php'];

    expect($versions[0])->toBe('8.4')
        ->and($versions)->not->toContain('8.3')
        ->and($versions)->toContain('8.5');
});

it('does not let the DDEV php_version decide a package matrix', function () {
    $dir = $this->project('package', ddev: true);
    file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: php\nphp_version: \"8.4\"\n");
    s9bRequirePhp($dir, '^8.3');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bMatrixJob($dir)['strategy']['matrix']['php'][0])->toBe('8.3');
});

it('uses the profile list as written for a package', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => ['8.4', '8.5']]]);

    $this->setupRun($dir, ['--yes' => true]);
    $job = s9bMatrixJob($dir);

    expect($job['strategy']['matrix']['php'])->toBe(['8.4', '8.5'])
        ->and(s9bSetupPhp($job))->toBe('${{ matrix.php }}');
});

it('uses the profile list for an app too, and keeps the single version for an app on auto', function () {
    $listed = $this->project('app');
    $this->writeProfile($listed, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => ['8.3', '8.4']]]);
    $this->setupRun($listed, ['--yes' => true]);

    expect(s9bMatrixJob($listed)['strategy']['matrix']['php'])->toBe(['8.3', '8.4']);

    $auto = $this->project('app');
    $this->writeProfile($auto, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => 'auto']]);
    $this->setupRun($auto, ['--yes' => true]);
    $job = s9bMatrixJob($auto);

    expect($job)->not->toHaveKey('strategy')
        ->and((string) s9bSetupPhp($job))->toMatch('/^\d+\.\d+$/');
});

it('keeps the one gate command in a matrix workflow, after the install, once', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);
    $this->setupRun($dir, ['--yes' => true]);
    $commands = [];

    foreach (s9bMatrixJob($dir)['steps'] as $step) {
        foreach (preg_split('/\R/', trim((string) ($step['run'] ?? ''))) ?: [] as $line) {
            $commands[] = trim($line);
        }
    }

    expect(array_count_values($commands)['composer test'])->toBe(1);
});

it('plans only the workflow when the matrix changes, never a hand edit, and reports No changes after', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => ['8.3']]]);
    $this->setupRun($dir, ['--yes' => true]);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => ['8.3', '8.4']]]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and(array_values(array_diff($this->diffPaths($output), [ProfileTestCase::STATE])))->toBe([ProfileTestCase::WORKFLOW]);

    $this->setupRun($dir, ['--yes' => true]);

    expect($this->setupRun($dir, ['--check' => true])[1])->toContain('No changes');
});

it('gives Profile::load the matrix only when the profile sets it', function () {
    $dir = $this->project('package');

    expect(array_keys(Profile::load($dir)->laravel()))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci']);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['php_matrix' => ['8.3', '8.4']]]);

    expect(Profile::load($dir)->laravel()['php_matrix'])->toBe(['8.3', '8.4']);
});

it('refuses a php_matrix that is not auto or a list of unique X.Y strings, naming the dotted path', function (mixed $value, string $path) {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'php_matrix' => $value]]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: '.$path)
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with([
    'a word' => ['all', 'laravel.php_matrix'],
    'a number' => [8.3, 'laravel.php_matrix'],
    'an empty list' => [[], 'laravel.php_matrix'],
    'a major only' => [['8'], 'laravel.php_matrix.0'],
    'a float item' => [['8.3', 8.4], 'laravel.php_matrix.1'],
    'a patch version' => [['8.3.1'], 'laravel.php_matrix.0'],
    'text' => [['8.3', 'latest'], 'laravel.php_matrix.1'],
    'a duplicate' => [['8.3', '8.3'], 'laravel.php_matrix.1'],
]);
