<?php

declare(strict_types=1);

/**
 * The suggested Claude Code permissions are the gate command as one exact rule, nothing wider:
 * `ddev exec` runs its arguments through the container's shell (S9d-1 review round 1).
 */

it('suggests exactly the gate command, with no wildcard rule', function (bool $ddev, string $rule) {
    $dir = $this->project('package', ddev: $ddev);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('"Bash('.substr($rule, 5))
        ->and(substr_count($output, '"Bash('))->toBe(1)
        ->and($output)->not->toContain(' *)"');
})->with([
    'host' => [false, 'Bash(composer test)'],
    'DDEV' => [true, 'Bash(ddev composer test)'],
]);
