<?php

declare(strict_types=1);

/**
 * Extra CI services from the profile: a suite that needs Redis gets it in the setup-owned workflow
 * without a hand edit. Requirements R11, R23 (Pest groups). Skills-gaps row 172.
 * Contract: tests/SkillContent/CONTRACT.md, section "Extra CI services".
 *
 * Pinned: the profile key `laravel.ci_services` (a list of service names, the row's example
 * `"ci_services": ["redis"]`), a `redis` service whose image is redis, `REDIS_HOST` in the gate job's env,
 * no "unknown key" notice, the database service kept beside it, and a docs/profile.md line. The image tag
 * and the env values are the builder's.
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Yaml\Yaml;

/**
 * The gate job of the written workflow.
 *
 * @return array<string, mixed>
 */
function ciServicesGateJob(string $dir): array
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));

    return $workflow['jobs']['gate'] ?? [];
}

it('adds a redis service and REDIS_HOST to the CI workflow when the profile lists redis', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['redis']]]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $job = ciServicesGateJob($dir);

    expect($job['services'] ?? [])->toHaveKey('redis')
        ->and((string) ($job['services']['redis']['image'] ?? ''))->toStartWith('redis')
        ->and($job['env'] ?? [])->toHaveKey('REDIS_HOST')
        ->and($code)->toBe(0);
})->group('R11', 'R23');

it('treats ci_services as a known option, not an unknown key', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['redis']]]);

    [, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect(ciServicesGateJob($dir)['services'] ?? [])->toHaveKey('redis')
        ->and($output)->not->toContain('Ignoring unknown profile key: laravel.ci_services');
})->group('R23');

it('reports No changes on the rerun with the redis service in place', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'ci_services' => ['redis']]]);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(ciServicesGateJob($dir)['services'] ?? [])->toHaveKey('redis')
        ->and($code)->toBe(0)
        ->and($output)->toContain('No changes');
})->group('R11', 'R23');

it('keeps the database service beside redis on the DDEV test database', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true, 'test_database' => 'ddev', 'ci_services' => ['redis']]]);

    $this->setupRun($dir, ['--yes' => true]);
    $services = ciServicesGateJob($dir)['services'] ?? [];

    expect($services)->toHaveKey('redis')
        ->and($services)->toHaveKey('database');
})->group('R11', 'R23');

it('adds no redis service when the profile lists no extra services', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);
    $job = ciServicesGateJob($dir);

    expect($job)->not->toBeEmpty()
        ->and($job['services'] ?? [])->not->toHaveKey('redis')
        ->and($job['env'] ?? [])->not->toHaveKey('REDIS_HOST');
})->group('R11');

it('documents ci_services in docs/profile.md', function () {
    $docs = (string) file_get_contents(dirname(__DIR__, 2).'/docs/profile.md');
    $lines = array_filter(preg_split('/\R/', $docs) ?: [], static fn (string $line): bool => str_contains($line, 'ci_services') && preg_match('/redis/i', $line) === 1);

    expect($lines)->not->toBeEmpty();
})->group('R23');
