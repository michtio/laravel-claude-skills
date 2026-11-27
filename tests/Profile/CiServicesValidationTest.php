<?php

declare(strict_types=1);

/**
 * The `laravel.ci_services` option is checked like every other option: only the services the CI
 * workflow has an image for are accepted, so a typo never writes a workflow without the service.
 * Requirements R11, R23. Skills-gaps row 172 (builder test, beside the locked CiServicesTest).
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;

it('refuses a ci service the workflow has no image for and writes nothing', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['rediss']]]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('laravel.ci_services.0')
        ->and(file_exists($dir.'/'.ProfileTestCase::WORKFLOW))->toBeFalse();
})->group('R11', 'R23');

it('refuses ci_services that is not a list of names', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => 'redis']]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('laravel.ci_services');
})->group('R11', 'R23');

it('refuses a ci service listed twice', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['redis', 'redis']]]);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('laravel.ci_services.1: lists redis twice');
})->group('R11', 'R23');

it('prints the ci services among the settings', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['redis']]]);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->toContain('ci_services: redis (profile)');
})->group('R23');
