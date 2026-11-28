<?php

declare(strict_types=1);

/**
 * Gate tests for the setup's extra steps (laravel-layer R18; skills-gaps row 240, item 3).
 *
 * The setup prints each extra step for the user's confirmation, so a step name or command must not hold a
 * character that hides or reorders what the plan shows: any Unicode control, format, surrogate, private-use
 * or unassigned character (category C*) and any line or paragraph separator (Zl, Zp), as
 * scripts/builders_check.py refuses for builder commands. A command keeps its tabs and newlines (a
 * multi-line command is shown as one block), as before. A refused step exits 1 with
 * `Invalid profile .ai/skills-profile.json: setup.steps.<i>.<field>: <reason>`, plans and writes nothing,
 * and the output never repeats the refused character; steps replayed from .ai/claude-skills-setup.json are
 * checked the same way.
 */

use Michtio\LaravelClaudeSkills\Tests\Profile\ProfileTestCase;

/**
 * A profile with one extra step.
 *
 * @return array<string, mixed>
 */
function hiddenCharactersStep(string $name, string $command): array
{
    return ['version' => 1, 'setup' => ['steps' => [['name' => $name, 'command' => $command]]]];
}

dataset('hidden characters', [
    'U+202E right-to-left override' => ["\u{202E}"],
    'U+200B zero-width space' => ["\u{200B}"],
    'U+2028 line separator' => ["\u{2028}"],
    'U+2029 paragraph separator' => ["\u{2029}"],
    'U+FEFF zero-width no-break space' => ["\u{FEFF}"],
    'U+E000 private use' => ["\u{E000}"],
]);

it('refuses a hidden character in a step name or command, plans and writes nothing', function (string $char) {
    foreach (['name', 'command'] as $field) {
        $dir = $this->project('app', ddev: true);
        $name = $field === 'name' ? "check {$char}machine" : 'check';
        $command = $field === 'command' ? "echo ok >> steps.log #{$char} harmless" : 'echo ok >> steps.log';
        $this->writeProfile($dir, hiddenCharactersStep($name, $command));
        $before = $this->snapshot($dir);

        foreach ([['--check' => true], ['--yes' => true]] as $options) {
            [$code, $output] = $this->setupRun($dir, $options);

            expect($output)->toContain('Invalid profile .ai/skills-profile.json: setup.steps.0.'.$field.': ')
                ->and($code)->toBe(1)
                ->and($output)->not->toContain('Extra step')
                ->not->toContain('Run:')
                ->not->toContain('Applied')
                ->not->toContain($char)
                ->and($this->snapshot($dir))->toBe($before);
        }

        expect(file_exists($dir.'/steps.log'))->toBeFalse();
    }
})->with('hidden characters')->group('R18');

it('refuses a hidden character in a step replayed from the state file', function (string $char) {
    foreach (['name', 'command'] as $field) {
        $dir = $this->applied('app', hiddenCharactersStep('check', 'echo ok >> steps.log'), ddev: true);
        $statePath = $dir.'/'.ProfileTestCase::STATE;
        $state = json_decode((string) file_get_contents($statePath), true);
        $state['steps'][0][$field] .= $char;
        file_put_contents($statePath, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n");
        $before = $this->snapshot($dir);

        [$code, $output] = $this->setupRun($dir, ['--check' => true]);

        expect($output)->toContain('.ai/claude-skills-setup.json')
            ->toContain('steps.0.'.$field)
            ->not->toContain($char)
            ->and($code)->toBe(1)
            ->and($this->snapshot($dir))->toBe($before);
    }
})->with('hidden characters')->group('R18');

it('still runs a multi-line command with tabs and a non-ASCII name', function () {
    $dir = $this->project('app', ddev: true);
    $this->writeProfile($dir, hiddenCharactersStep('Vérifier, étape #2', "printf 'a\\tb\\n' >> steps.log\nprintf 'c\\n' >> steps.log"));

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($output)->not->toContain('Invalid profile')
        ->and($code)->toBe(0)
        ->and($this->read($dir, 'steps.log'))->toBe("a\tb\nc\n");
})->group('R18');
