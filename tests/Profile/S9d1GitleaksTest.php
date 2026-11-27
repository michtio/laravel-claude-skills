<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9d-1 (laravel-layer): gitleaks inside DDEV, so a local run equals CI.
 * Requirements R9, R11. Skills-gaps rows 12, 124 (setup part).
 * Contract: tests/S9d1/CONTRACT.md section 4.
 *
 * The checksums are gitleaks' own (gitleaks_8.30.1_checksums.txt on the v8.30.1 release); the
 * x64 one is the value the CI workflow already pins (WorkflowPlanner::GITLEAKS_SHA256).
 */

const S9D1_DOCKERFILE = '.ddev/web-build/Dockerfile.gitleaks';

const S9D1_GITLEAKS_VERSION = '8.30.1';

const S9D1_GITLEAKS_X64 = '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb';

const S9D1_GITLEAKS_ARM64 = 'e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080';

/**
 * Run a project script with a clean environment plus $env; [exit code, output].
 *
 * @param array<string, string> $env
 * @return array{int, string}
 */
function s9d1Run(string $dir, string $script, array $env = []): array
{
    $vars = '';
    foreach ($env + ['PATH' => '/usr/bin:/bin'] as $key => $value) {
        $vars .= ' '.$key.'='.escapeshellarg($value);
    }
    exec('cd '.escapeshellarg($dir).' && env -i'.$vars.' sh '.escapeshellarg($script).' 2>&1', $out, $code);

    return [$code, implode("\n", $out)];
}

it('plans a pinned gitleaks install into the DDEV web image', function (string $fixture) {
    $dir = $this->project($fixture, ddev: true);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);
    $dockerfile = (string) $this->read($dir, S9D1_DOCKERFILE);

    expect($code)->toBe(0)
        ->and($output)->toContain(S9D1_DOCKERFILE)
        ->and($dockerfile)->toContain(S9D1_GITLEAKS_VERSION)
        ->toContain(S9D1_GITLEAKS_X64)
        ->toContain(S9D1_GITLEAKS_ARM64)
        ->toContain('TARGETARCH')
        ->toContain('sha256sum -c');
})->with(['app' => ['app'], 'package' => ['package']]);

it('pins the same gitleaks release and x64 checksum as the CI workflow', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);
    $workflow = (string) $this->read($dir, '.github/workflows/claude-skills-gate.yml');
    $dockerfile = (string) $this->read($dir, S9D1_DOCKERFILE);

    expect($workflow)->toContain('GITLEAKS_VERSION: '.S9D1_GITLEAKS_VERSION)
        ->toContain(S9D1_GITLEAKS_X64)
        ->and($dockerfile)->toContain(S9D1_GITLEAKS_VERSION)
        ->toContain(S9D1_GITLEAKS_X64);
});

it('reports No changes on the rerun with the gitleaks Dockerfile in place', function () {
    $dir = $this->project('package', ddev: true);
    $this->setupRun($dir, ['--yes' => true]);
    expect(file_exists($dir.'/'.S9D1_DOCKERFILE))->toBeTrue();

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)->and($output)->toContain('No changes');
});

it('plans no gitleaks Dockerfile for a project on the host runner', function () {
    $dir = $this->project('app');

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/'.S9D1_DOCKERFILE))->toBeFalse()
        ->and($this->diffPaths($output))->not->toContain(S9D1_DOCKERFILE);
});

it('fails the secret scan inside DDEV when gitleaks is missing, naming ddev restart', function () {
    exec('env -i PATH=/usr/bin:/bin sh -c "command -v gitleaks" 2>&1', $found, $present);
    expect($present)->not->toBe(0, 'gitleaks must not be in /usr/bin or /bin for this case');
    $dir = $this->project('app', ddev: true);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = s9d1Run($dir, '.githooks/gitleaks-check', ['IS_DDEV_PROJECT' => 'true']);

    expect($code)->not->toBe(0)
        ->and($output)->toContain('ddev restart');
});

it('still skips the secret scan with a message on the host when gitleaks is missing', function () {
    exec('env -i PATH=/usr/bin:/bin sh -c "command -v gitleaks" 2>&1', $found, $present);
    expect($present)->not->toBe(0, 'gitleaks must not be in /usr/bin or /bin for this case');
    $dir = $this->project('app', ddev: true);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = s9d1Run($dir, '.githooks/gitleaks-check');

    expect($code)->toBe(0)->and($output)->toContain('gitleaks not found, skipping the secret scan');
});
