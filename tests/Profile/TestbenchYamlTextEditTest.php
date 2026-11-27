<?php

declare(strict_types=1);

/**
 * The testbench.yaml text edit falls back to a full rewrite whenever the line edit would change
 * anything it does not own (S9d-1 review round 1).
 */

use Symfony\Component\Yaml\Yaml;

it('keeps an env key that only starts with APP_DEBUG when it sets APP_DEBUG', function () {
    $dir = $this->project('package');
    file_put_contents($dir.'/testbench.yaml', "laravel: '@testbench'\nenv:\n  APP_DEBUG-LOCAL: 'on'\n  APP_NAME: Example\n");

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $data = Yaml::parse((string) file_get_contents($dir.'/testbench.yaml'));

    expect($code)->toBe(0)
        ->and($data['laravel'])->toBe('./')
        ->and($data['env'])->toMatchArray(['APP_DEBUG-LOCAL' => 'on', 'APP_NAME' => 'Example', 'APP_DEBUG' => true]);
});
