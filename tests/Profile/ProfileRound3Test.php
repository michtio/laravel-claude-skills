<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer), round 3: the final review's findings.
 * Contract: tests/Profile/CONTRACT.md, section "13. Round 3".
 *
 *   1. phpstan/extension-installer present: the written phpstan.neon has no includes block;
 *   2. a recorded phpstan.neon that the user replaced: the plan says applying replaces it;
 *   3. a Testbench project without the S6 package markers still gets src as its path.
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

/**
 * Put packages into require or require-dev of a temp project.
 *
 * @param array<string, string> $dev
 * @param array<string, string> $require
 */
function r3Composer(string $dir, array $dev = [], array $require = []): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);

    foreach ($dev as $package => $version) {
        $composer['require-dev'][$package] = $version;
    }

    foreach ($require as $package => $version) {
        $composer['require'][$package] = $version;
    }

    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

// 1. phpstan/extension-installer
// =========================================================================

it('writes phpstan.neon without the includes block when phpstan/extension-installer is required', function (string $section) {
    $dir = $this->project('app');
    r3Composer($dir, $section === 'require-dev' ? ['larastan/larastan' => '^3.0', 'phpstan/extension-installer' => '^1.4'] : ['larastan/larastan' => '^3.0'], $section === 'require' ? ['phpstan/extension-installer' => '^1.4'] : []);
    mkdir($dir.'/app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 6]]);

    $this->setupRun($dir, ['--yes' => true]);
    $raw = (string) file_get_contents($dir.'/phpstan.neon');
    $config = Yaml::parse($raw);

    expect($config)->not->toHaveKey('includes')
        ->and($raw)->not->toContain('includes:')
        ->not->toContain('extension.neon')
        ->and($config['parameters']['level'])->toBe(6)
        ->and($config['parameters']['paths'])->toBe(['app']);
})->with(['require-dev', 'require']);

it('keeps the pinned includes when the extension installer is not required', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);
    $this->writeProfile($dir, ['version' => 1]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['includes'])->toBe([
        'vendor/larastan/larastan/extension.neon',
        'vendor/michtio/laravel-claude-skills/extension.neon',
    ]);
});

it('also omits the includes for a package, and when Larastan is missing and planned', function () {
    $package = $this->project('package');
    r3Composer($package, ['larastan/larastan' => '^3.0', 'phpstan/extension-installer' => '^1.4']);
    $this->writeProfile($package, ['version' => 1]);
    $this->setupRun($package, ['--yes' => true]);

    expect(Yaml::parse((string) file_get_contents($package.'/phpstan.neon')))->not->toHaveKey('includes');

    $planned = $this->project('app');
    r3Composer($planned, ['phpstan/extension-installer' => '^1.4']);
    $this->writeProfile($planned, ['version' => 1, 'laravel' => ['phpstan_level' => 8]]);

    [, $output] = $this->setupRun($planned, ['--check' => true]);

    expect($output)->toContain('+++ b/phpstan.neon')
        ->not->toContain('+    - vendor/larastan/larastan/extension.neon')
        ->not->toContain('+includes:');
});

it('plans the file again when the installer is added or removed after the setup wrote it', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);
    $this->setupRun($dir, ['--yes' => true]);
    expect(file_get_contents($dir.'/phpstan.neon'))->toContain('includes:');

    r3Composer($dir, ['phpstan/extension-installer' => '^1.4']);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain('phpstan.neon')
        ->and($output)->not->toContain('edited by hand');

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_get_contents($dir.'/phpstan.neon'))->not->toContain('includes:');
    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

// 2. A recorded phpstan.neon replaced by the user
// =========================================================================

it('says explicitly that applying replaces a phpstan.neon the user rewrote after the setup wrote it', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);
    $this->setupRun($dir, ['--yes' => true]);
    $own = "parameters:\n    level: 3\n    paths:\n        - app\n        - modules\n";
    file_put_contents($dir.'/phpstan.neon', $own);
    $before = $this->snapshot($dir);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpstan.neon')
        ->toContain('phpstan.neon: applying replaces your changes with level 8')
        ->toContain('--- a/phpstan.neon')
        ->toContain('+++ b/phpstan.neon')
        ->and($this->snapshot($dir))->toBe($before);
});

it('replaces the rewritten phpstan.neon only after the confirmation, and not when declined', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);
    $this->setupRun($dir, ['--yes' => true]);
    $own = "parameters:\n    level: 3\n";
    file_put_contents($dir.'/phpstan.neon', $own);

    $this->artisan('claude-skills:setup', ['--path' => $dir])
        ->expectsOutputToContain('phpstan.neon: applying replaces your changes')
        ->expectsConfirmation('Apply these changes?', 'no')
        ->assertExitCode(0);

    expect(file_get_contents($dir.'/phpstan.neon'))->toBe($own);

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_get_contents($dir.'/phpstan.neon'))->toContain('level: 8')
        ->not->toContain('level: 3');
});

it('names the level the apply will write in that line', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['phpstan_level' => 5]]);
    $this->setupRun($dir, ['--yes' => true]);
    file_put_contents($dir.'/phpstan.neon', "parameters:\n    level: 1\n");

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('phpstan.neon: applying replaces your changes with level 5');
});

// 3. A Testbench project without the S6 package markers
// =========================================================================

it('analyses src when testbench is in require-dev, there is no artisan, no bootstrap/app.php, no workbench and a src folder', function () {
    $dir = $this->project('package');
    unlink($dir.'/workbench/.gitkeep');
    rmdir($dir.'/workbench');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);

    expect(file_exists($dir.'/artisan'))->toBeFalse()
        ->and(file_exists($dir.'/bootstrap/app.php'))->toBeFalse()
        ->and(is_dir($dir.'/src'))->toBeTrue();

    $this->writeProfile($dir, ['version' => 1]);
    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    // The S6 rule stands (package = testbench plus workbench/): this project is still an app.
    expect($output)->toContain('Detected: app')
        ->and(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'])->toBe(['src']);
});

it('analyses src for a plain project that has src and none of app, config, database, routes', function () {
    $dir = $this->project('app');
    mkdir($dir.'/src');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);

    $this->setupRun($dir, ['--yes' => true]);

    expect(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'])->toBe(['src']);
});

it('prefers the app directories over src when both exist', function () {
    $dir = $this->project('app');
    mkdir($dir.'/src');
    mkdir($dir.'/app');
    mkdir($dir.'/routes');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);

    $this->setupRun($dir, ['--yes' => true]);

    expect(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'])->toBe(['app', 'routes']);
});

it('still analyses app when nothing exists at all', function () {
    $dir = $this->project('app');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);

    $this->setupRun($dir, ['--yes' => true]);

    expect(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'])->toBe(['app']);
});

it('keeps the workbench package rule: a package with workbench analyses src', function () {
    $dir = $this->project('package');
    r3Composer($dir, ['larastan/larastan' => '^3.0']);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->toContain('Detected: package')
        ->and(Yaml::parse((string) file_get_contents($dir.'/phpstan.neon'))['parameters']['paths'])->toBe(['src']);
});
