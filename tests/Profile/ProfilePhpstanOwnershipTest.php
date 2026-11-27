<?php

declare(strict_types=1);

/**
 * Builder tests for the S7 scope addition (laravel-layer): the phpstan.neon the setup
 * wrote gives way to a config of the project's own, and stops being managed when the
 * project leaves Larastan and the profile sets no level.
 */

/**
 * Put larastan/larastan into require-dev of a temp project, or take it out.
 */
function setLarastan(string $dir, bool $required): void
{
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    unset($composer['require-dev']['larastan/larastan']);

    if ($required) {
        $composer['require-dev']['larastan/larastan'] = '^3.0';
    }

    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
}

it('removes its own phpstan.neon once the project adds phpstan.neon.dist, and leaves that alone', function () {
    $dir = $this->project('app');
    setLarastan($dir, true);
    $this->setupRun($dir, ['--yes' => true]);
    expect(file_exists($dir.'/phpstan.neon'))->toBeTrue();

    $own = "parameters:\n    level: 2\n";
    file_put_contents($dir.'/phpstan.neon.dist', $own);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Left alone: phpstan.neon.dist')
        ->toContain('--- a/phpstan.neon');

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/phpstan.neon'))->toBeFalse()
        ->and(file_get_contents($dir.'/phpstan.neon.dist'))->toBe($own);

    [$code] = $this->setupRun($dir, ['--check' => true]);
    expect($code)->toBe(0);
});

it('keeps a hand-edited phpstan.neon when a config of the project appears next to it', function () {
    $dir = $this->project('app');
    setLarastan($dir, true);
    $this->setupRun($dir, ['--yes' => true]);
    file_put_contents($dir.'/phpstan.neon', file_get_contents($dir.'/phpstan.neon')."# team note\n");
    file_put_contents($dir.'/phpstan.dist.neon', "parameters:\n    level: 2\n");

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->toContain('edited by hand: phpstan.neon')
        ->and(file_get_contents($dir.'/phpstan.neon'))->toContain('# team note');
});

it('removes its own phpstan.neon when the project leaves Larastan and the profile sets no level', function () {
    $dir = $this->project('app');
    setLarastan($dir, true);
    $this->setupRun($dir, ['--yes' => true]);
    setLarastan($dir, false);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/phpstan.neon'))->toBeFalse()
        ->and($this->runLines($output))->toBe([]);
});
