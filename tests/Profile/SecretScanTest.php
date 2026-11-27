<?php

declare(strict_types=1);

/**
 * The secret scan inside DDEV fails without gitleaks only where the setup installs it in the web
 * image; a DDEV project set to the host runner skips like the host (S9d-1 review round 1).
 */

it('skips the scan inside DDEV when the setup wrote no gitleaks image addition', function () {
    exec('env -i PATH=/usr/bin:/bin sh -c "command -v gitleaks" 2>&1', $found, $present);
    expect($present)->not->toBe(0, 'gitleaks must not be in /usr/bin or /bin for this case');
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['runner' => 'host']]);
    $this->setupRun($dir, ['--yes' => true]);
    expect(file_exists($dir.'/.ddev/web-build/Dockerfile.gitleaks'))->toBeFalse();

    exec('cd '.escapeshellarg($dir).' && env -i PATH=/usr/bin:/bin IS_DDEV_PROJECT=true sh .githooks/gitleaks-check 2>&1', $out, $code);

    expect($code)->toBe(0)->and(implode("\n", $out))->toContain('gitleaks not found, skipping the secret scan');
});
