<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer), scope addition of 2026-11-27: `laravel.phpstan_level`
 * takes effect, `laravel.env_schema` is no longer a Laravel key.
 * Contract: tests/Profile/CONTRACT.md, section "12. phpstan_level and env_schema".
 *
 * The setup manages a PHPStan config only for a project that is on Larastan or that asks for a
 * level in its profile. Tests that apply (--yes) first put larastan/larastan into composer.json,
 * so no test ever runs composer; the "missing Larastan" cases are read with --check only.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

const PHPSTAN_FILE = 'phpstan.neon';
const LARASTAN_INCLUDE = 'vendor/larastan/larastan/extension.neon';
const PACK_INCLUDE = 'vendor/michtio/laravel-claude-skills/extension.neon';

/**
 * Put larastan/larastan into require-dev of a temp project.
 */
function withLarastan(string $dir): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer['require-dev']['larastan/larastan'] = '^3.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

/**
 * The parsed phpstan.neon of a project.
 *
 * @return array<string, mixed>
 */
function phpstanConfig(string $dir): array
{
    return Yaml::parse((string) file_get_contents($dir.'/'.PHPSTAN_FILE));
}

// phpstan_level takes effect
// =========================================================================

it('writes phpstan.neon at the profile level for an app, with Larastan, this pack and the app paths', function () {
    $dir = $this->project('app');
    withLarastan($dir);
    foreach (['app', 'config', 'database'] as $directory) {
        mkdir($dir.'/'.$directory);
    }
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 5]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('+++ b/phpstan.neon')
        ->and($this->runLines($output))->toBe([])
        ->and(file_exists($dir.'/'.PHPSTAN_FILE))->toBeFalse();

    $this->setupRun($dir, ['--yes' => true]);
    $config = phpstanConfig($dir);

    expect($config['includes'])->toBe([LARASTAN_INCLUDE, PACK_INCLUDE])
        ->and($config['parameters']['level'])->toBe(5)
        ->and($config['parameters']['paths'])->toBe(['app', 'config', 'database']);
});

it('lists only the app directories that exist, routes included, and app when none does', function (array $directories, array $expected) {
    $dir = $this->project('app');
    withLarastan($dir);
    foreach ($directories as $directory) {
        mkdir($dir.'/'.$directory);
    }
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 8]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(phpstanConfig($dir)['parameters']['paths'])->toBe($expected);
})->with([
    'all four' => [['routes', 'database', 'config', 'app'], ['app', 'config', 'database', 'routes']],
    'only app and routes' => [['app', 'routes'], ['app', 'routes']],
    'none exists' => [[], ['app']],
]);

it('lists src for a Testbench package', function () {
    $dir = $this->project('package');
    withLarastan($dir);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 6]]);

    $this->setupRun($dir, ['--yes' => true]);
    $config = phpstanConfig($dir);

    expect($config['parameters']['paths'])->toBe(['src'])
        ->and($config['parameters']['level'])->toBe(6)
        ->and($config['includes'])->toBe([LARASTAN_INCLUDE, PACK_INCLUDE]);
});

it('writes the default level 8 for a project on Larastan whose profile sets no level', function (array $profile) {
    $dir = $this->project('app');
    withLarastan($dir);
    if ($profile !== []) {
        $this->writeProfile($dir, $profile);
    }

    $this->setupRun($dir, ['--yes' => true]);

    expect(phpstanConfig($dir)['parameters']['level'])->toBe(8);
})->with([
    'no profile' => [[]],
    'profile without laravel keys' => [['version' => 1]],
    'profile with another option' => [['version' => 1, 'laravel' => ['ci' => false]]],
]);

it('writes the extreme levels 0 and 10', function (int $level) {
    $dir = $this->project('app');
    withLarastan($dir);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => $level]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(phpstanConfig($dir)['parameters']['level'])->toBe($level);
})->with([0, 10]);

it('plans nothing about PHPStan for a project that is not on Larastan and sets no level', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => false]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($this->diffPaths($output))->not->toContain(PHPSTAN_FILE)
        ->and($this->runLines($output))->toBe([])
        ->and($output)->not->toContain('larastan')
        ->not->toContain('Left alone');
});

it('never changes an existing phpstan config, whatever its level, and says it was left alone', function (string $file) {
    $dir = $this->project('app');
    withLarastan($dir);
    $own = "parameters:\n    level: 3\n    paths:\n        - app\n";
    file_put_contents($dir.'/'.$file, $own);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 9]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('Left alone: '.$file)
        ->and($this->diffPaths($output))->not->toContain($file)
        ->not->toContain(PHPSTAN_FILE);

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_get_contents($dir.'/'.$file))->toBe($own);

    foreach (['phpstan.neon', 'phpstan.neon.dist', 'phpstan.dist.neon'] as $other) {
        if ($other !== $file) {
            expect(file_exists($dir.'/'.$other))->toBeFalse();
        }
    }
})->with(['phpstan.neon', 'phpstan.neon.dist', 'phpstan.dist.neon']);

it('plans no Larastan install when the existing config is left alone', function () {
    $dir = $this->project('app');
    file_put_contents($dir.'/phpstan.neon', "parameters:\n    level: 3\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 9]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($this->runLines($output))->toBe([])
        ->and($output)->toContain('Left alone: phpstan.neon');
});

it('owns the file it wrote: a second run is quiet, a hand edit is flagged', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['phpstan_level' => 4]], ddev: false, prepare: 'withLarastan');
    expect(file_exists($dir.'/'.PHPSTAN_FILE))->toBeTrue();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->and($output)->not->toContain('Left alone');

    file_put_contents($dir.'/'.PHPSTAN_FILE, file_get_contents($dir.'/'.PHPSTAN_FILE)."# team note\n");

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpstan.neon');
});

it('plans a level change on the file it wrote, and only that (AC15)', function () {
    $dir = $this->applied('app', ['version' => 1, 'laravel' => ['phpstan_level' => 4]], ddev: false, prepare: 'withLarastan');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 6]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain(PHPSTAN_FILE)
        ->and(array_values(array_diff($this->diffPaths($output), [PHPSTAN_FILE, ProfileTestCase::STATE])))->toBe([])
        ->and($this->runLines($output))->toBe([])
        ->and($output)->not->toContain('Left alone');

    $this->setupRun($dir, ['--yes' => true]);

    expect(phpstanConfig($dir)['parameters']['level'])->toBe(6);
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

it('notes the Larastan dev dependency to add through the runner when it is missing, like monitoring', function (bool $ddev, string $expected) {
    $dir = $this->project('app', ddev: $ddev);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 8]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain(PHPSTAN_FILE)
        ->and($this->runLines($output))->toBe([$expected]);
})->with([
    'host' => [false, 'composer require --dev larastan/larastan'],
    'ddev' => [true, 'ddev composer require --dev larastan/larastan'],
]);

it('plans the Larastan install for a Testbench package too, and never for a project that has it', function () {
    $package = $this->project('package');
    $this->writeProfile($package, ['version' => 1, 'laravel' => ['phpstan_level' => 8]]);

    [, $output] = $this->setupRun($package, ['--check' => true]);

    expect($this->runLines($output))->toBe(['composer require --dev larastan/larastan']);

    $app = $this->project('app');
    $composer = json_decode((string) file_get_contents($app.'/composer.json'), true);
    $composer['require']['larastan/larastan'] = '^3.0';
    file_put_contents($app.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    $this->writeProfile($app, ['version' => 1, 'laravel' => ['phpstan_level' => 8]]);

    [, $output] = $this->setupRun($app, ['--check' => true]);

    expect($this->runLines($output))->toBe([]);
});

it('keeps the Larastan install before the extra steps and never plans to remove it', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 8], 'setup' => ['steps' => [['name' => 'team', 'command' => 'echo team >> steps.log']]]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($this->runLines($output))->toBe(['composer require --dev larastan/larastan', 'echo team >> steps.log'])
        ->and($output)->not->toContain('composer remove');
});

// env_schema is not a Laravel key any more
// =========================================================================

it('keeps env_schema in the file and ignores it, with the unknown-key notice, whatever its value', function (mixed $value) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['env_schema' => $value]]);
    $content = (string) file_get_contents($dir.'/'.ProfileTestCase::PROFILE);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('Invalid profile')
        ->toContain('Ignoring unknown profile key: laravel.env_schema')
        ->and(Profile::load($dir)->laravel())->not->toHaveKey('env_schema')
        ->and(file_get_contents($dir.'/'.ProfileTestCase::PROFILE))->toBe($content);
})->with([true, false, 'yes', 3]);

it('lists five Laravel options now, in this order', function () {
    $dir = $this->project('app');

    expect(array_keys(Profile::load($dir)->laravel()))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci']);
});

it('no longer documents env_schema as a Laravel option', function () {
    $docs = (string) file_get_contents(__DIR__.'/../../docs/profile.md');

    expect($docs)->not->toContain('env_schema');
});
