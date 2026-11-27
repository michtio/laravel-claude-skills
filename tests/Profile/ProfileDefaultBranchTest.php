<?php

declare(strict_types=1);

/**
 * Builder tests for slice S7 round 2 (laravel-layer): the workflow's push branch
 * follows the repository's default branch, and a multi-line command reads as one
 * block in the plan.
 *
 * Default branch: origin's HEAD (without "origin/"), else git's init.defaultBranch,
 * else main (also main outside a git repository, pinned by ProfileRound2Test).
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;
use Symfony\Component\Process\Process;
use Symfony\Component\Yaml\Yaml;

/**
 * Run git in a directory and fail the test when it fails.
 *
 * @param list<string> $arguments
 */
function gitIn(string $dir, array $arguments): void
{
    $process = new Process(['git', '-C', $dir, ...$arguments]);
    $process->mustRun();
}

/**
 * The push branches of the written workflow.
 *
 * @return list<string>
 */
function pushBranches(string $dir): array
{
    $workflow = Yaml::parse((string) file_get_contents($dir.'/'.ProfileTestCase::WORKFLOW));
    $on = $workflow['on'] ?? $workflow[true];

    return $on['push']['branches'];
}

it('pushes on the branch origin HEAD points to', function () {
    $dir = $this->project('app');
    gitIn($dir, ['init', '-q', '-b', 'main']);
    gitIn($dir, ['symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/develop']);
    gitIn($dir, ['config', 'init.defaultBranch', 'trunk']);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(pushBranches($dir))->toBe(['develop']);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('falls back to init.defaultBranch when origin has no HEAD', function () {
    $dir = $this->project('app');
    gitIn($dir, ['init', '-q', '-b', 'main']);
    gitIn($dir, ['config', 'init.defaultBranch', 'develop']);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(pushBranches($dir))->toBe(['develop']);
});

it('plans the workflow again when the default branch changes', function () {
    $dir = $this->project('app');
    gitIn($dir, ['init', '-q', '-b', 'main']);
    gitIn($dir, ['config', 'init.defaultBranch', 'main']);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['ci' => true]]);
    $this->setupRun($dir, ['--yes' => true]);
    expect(pushBranches($dir))->toBe(['main']);

    gitIn($dir, ['symbolic-ref', 'refs/remotes/origin/HEAD', 'refs/remotes/origin/develop']);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($this->diffPaths($output))->toContain(ProfileTestCase::WORKFLOW)
        ->and($output)->not->toContain('edited by hand');
});

it('shows a multi-line command as one block under Run:, and runs it whole', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'setup' => ['steps' => [
        ['name' => 'two lines', 'command' => "echo one >> steps.log\necho two >> steps.log"],
    ]]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain("Run: echo one >> steps.log\n     echo two >> steps.log")
        ->and($this->runLines($output))->toBe(['echo one >> steps.log']);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain("Ran echo one >> steps.log\n    echo two >> steps.log")
        ->and($this->read($dir, 'steps.log'))->toBe("one\ntwo\n");
});
