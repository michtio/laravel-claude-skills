<?php

declare(strict_types=1);

/**
 * Builder test for S7 round 3 (laravel-layer): the documented way to keep a hand-made
 * PHPStan config is to rename the setup's phpstan.neon to phpstan.neon.dist.
 */

it('leaves a renamed config alone and plans nothing more for it', function () {
    $dir = $this->project('app');
    $composer = json_decode((string) file_get_contents($dir.'/composer.json'), true);
    $composer['require-dev']['larastan/larastan'] = '^3.0';
    file_put_contents($dir.'/composer.json', json_encode($composer, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
    $this->setupRun($dir, ['--yes' => true]);

    $own = "parameters:\n    level: 3\n";
    unlink($dir.'/phpstan.neon');
    file_put_contents($dir.'/phpstan.neon.dist', $own);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->toContain('Left alone: phpstan.neon.dist')
        ->and(file_exists($dir.'/phpstan.neon'))->toBeFalse()
        ->and(file_get_contents($dir.'/phpstan.neon.dist'))->toBe($own);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});
