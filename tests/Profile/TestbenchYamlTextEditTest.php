<?php

declare(strict_types=1);

/**
 * The testbench.yaml text edit falls back to a full rewrite whenever the line edit would change
 * anything it does not own (S9d-1 review round 1).
 */

use Symfony\Component\Yaml\Yaml;

it('keeps an env key that only starts with APP_DEBUG when it sets APP_DEBUG', function () {
    $dir = $this->project('package');
    file_put_contents($dir.'/testbench.yaml', "laravel: '@testbench'\n# keep this note\nenv:\n  APP_DEBUG-LOCAL: 'on'\n  APP_NAME: Example\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $after = (string) file_get_contents($dir.'/testbench.yaml');
    $data = Yaml::parse($after);

    expect($code)->toBe(0)
        ->and($after)->toContain("# keep this note\n")
        ->toContain("  APP_DEBUG-LOCAL: 'on'\n")
        ->and($data['laravel'])->toBe('./')
        ->and($data['env'])->toMatchArray(['APP_DEBUG-LOCAL' => 'on', 'APP_NAME' => 'Example', 'APP_DEBUG' => true]);
});

it('keeps the comments when it fills an empty env key', function () {
    $dir = $this->project('package');
    file_put_contents($dir.'/testbench.yaml', "laravel: '@testbench'\n# local settings\nenv:\n\nproviders: []\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $after = (string) file_get_contents($dir.'/testbench.yaml');

    expect($code)->toBe(0)
        ->and($after)->toContain("# local settings\n")
        ->and(Yaml::parse($after)['env'])->toBe(['APP_DEBUG' => true]);
});
