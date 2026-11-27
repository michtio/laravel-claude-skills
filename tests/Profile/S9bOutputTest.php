<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): what the setup prints.
 * Requirements R8, R9, R23. Skills-gaps rows 13, 16.
 * Contract: tests/S9b/CONTRACT.md section 6.
 */

const S9B_PLUGIN = 'laravel-claude-skills@laravel-claude-skills';

/**
 * The line of an output that holds an option, or null.
 */
function s9bOptionLine(string $output, string $key): ?string
{
    return preg_match('/^  '.preg_quote($key, '/').': (.*)$/m', $output, $match) === 1 ? $match[1] : null;
}

// 1. The effective options, with their source
// =========================================================================

it('lists every effective option with its source when a profile exists', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['runner' => 'host', 'ci' => true]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('Profile: .ai/skills-profile.json')
        ->not->toContain('No profile found')
        ->not->toContain('using the defaults')
        ->and(s9bOptionLine($output, 'runner'))->toBe('host (profile)')
        ->and(s9bOptionLine($output, 'ci'))->toBe('true (profile)')
        ->and(s9bOptionLine($output, 'house_style'))->toBe('true (default)')
        ->and(s9bOptionLine($output, 'phpstan_level'))->toBe('8 (default)')
        ->and(s9bOptionLine($output, 'monitoring'))->toBe('none (default)')
        ->and(s9bOptionLine($output, 'test_database'))->toBe('auto (default)')
        ->and(s9bOptionLine($output, 'php_matrix'))->toBe('auto (default)')
        ->and(s9bOptionLine($output, 'test_pins'))->toBe('none (default)');
});

it('shows the new options with their values and the profile as source', function () {
    $dir = $this->project('package', ddev: true);
    $this->writeProfile($dir, ['version' => 1, 'laravel' => [
        'test_database' => 'ddev',
        'php_matrix' => ['8.3', '8.4'],
        'test_pins' => ['SESSION_DRIVER' => 'file'],
    ]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(s9bOptionLine($output, 'test_database'))->toBe('ddev (profile)')
        ->and(s9bOptionLine($output, 'php_matrix'))->toBe('8.3, 8.4 (profile)')
        ->and(s9bOptionLine($output, 'test_pins'))->toBe('SESSION_DRIVER=file (profile)');
});

it('prints them on every run, No changes included', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['house_style' => false]]);
    $this->setupRun($dir, ['--yes' => true]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('No changes')
        ->and(s9bOptionLine($output, 'house_style'))->toBe('false (profile)')
        ->and(s9bOptionLine($output, 'runner'))->toBe('auto (default)');
});

it('lists the new options among the defaults when there is no profile', function () {
    $dir = $this->project('app');

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('No profile found at .ai/skills-profile.json')
        ->toContain('using the defaults')
        ->toContain('runner: auto')
        ->and(s9bOptionLine($output, 'test_database'))->toStartWith('auto')
        ->and(s9bOptionLine($output, 'php_matrix'))->toStartWith('auto')
        ->and(s9bOptionLine($output, 'test_pins'))->toStartWith('none');
});

// 2. Wording
// =========================================================================

it('says how many changes are planned, not that changes would change', function () {
    $dir = $this->project('app');

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toMatch('/\b\d+ changes planned\./')
        ->not->toContain('would change');
});

it('says 1 change planned for a single change', function () {
    $dir = $this->project('app');
    $this->setupRun($dir, ['--yes' => true]);
    $this->writeProfile($dir, ['version' => 1, 'setup' => ['steps' => [['name' => 'one', 'command' => 'true']]]]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('1 change planned.')
        ->not->toContain('would change');
});

// 3. The agent-install step
// =========================================================================

it('prints the two commands that install the agents plugin, on every run, No changes included', function () {
    $dir = $this->project('app');
    $this->setupRun($dir, ['--yes' => true]);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [, $output] = $this->setupRun($dir, $options);

        expect($output)->toContain('No changes')
            ->toContain('/plugin marketplace add michtio/laravel-claude-skills')
            ->toContain('/plugin install '.S9B_PLUGIN);
    }
});

it('prints them with a plan too, and they are not a Run: action the setup performs', function () {
    $dir = $this->project('app');

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('/plugin install '.S9B_PLUGIN)
        ->and($this->runLines($output))->toBe([]);
});

it('does not print them when the project settings already enable the plugin, and keeps the exit code', function () {
    $dir = $this->project('app');
    mkdir($dir.'/.claude');
    file_put_contents($dir.'/.claude/settings.json', json_encode(['enabledPlugins' => [S9B_PLUGIN => true]]));
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(0)
        ->and($output)->not->toContain('/plugin install')
        ->not->toContain('/plugin marketplace add');
});

it('still prints them when the plugin is listed but set to false', function () {
    $dir = $this->project('app');
    mkdir($dir.'/.claude');
    file_put_contents($dir.'/.claude/settings.json', json_encode(['enabledPlugins' => [S9B_PLUGIN => false]]));

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toContain('/plugin install '.S9B_PLUGIN);
});

it('writes no .claude/settings.json itself', function () {
    $dir = $this->project('app');

    $this->setupRun($dir, ['--yes' => true]);

    expect(file_exists($dir.'/.claude/settings.json'))->toBeFalse();
});
