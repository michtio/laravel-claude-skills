<?php

declare(strict_types=1);

/**
 * Event and listener naming hints are house style: the rendered core guideline carries them by default
 * and drops them with "house_style": false, so the team's own style (Spatie's, for example) governs naming.
 * Requirement R12 (Pest group). Owner ruling on the spatie/guidelines-skills learnings.
 * Contract: tests/SkillContent/CONTRACT.md, section "Spatie learnings".
 *
 * The guideline is rendered with Blade, as Boost composes it, against a project root holding the profile.
 */

use Illuminate\Support\Facades\Blade;

/**
 * Render resources/boost/guidelines/core.blade.php for a project root with the given profile (null: none).
 *
 * @param array<string, mixed>|null $profile
 */
function namingHintsRender(?array $profile): string
{
    $root = sys_get_temp_dir().'/naming-hints-'.bin2hex(random_bytes(4));
    mkdir($root.'/.ai', 0777, true);

    if ($profile !== null) {
        file_put_contents($root.'/.ai/skills-profile.json', (string) json_encode($profile));
    }

    app()->setBasePath($root);

    // As Boost 2.10's RendersBladeGuidelines::renderContent(): hide backticks and PHP open tags from Blade.
    $placeholders = ['`' => '___SINGLE_BACKTICK___', '<?php' => '___OPEN_PHP_TAG___'];
    $source = (string) file_get_contents(dirname(__DIR__, 2).'/resources/boost/guidelines/core.blade.php');
    $rendered = Blade::render(str_replace(array_keys($placeholders), array_values($placeholders), $source));

    return str_replace(array_values($placeholders), array_keys($placeholders), $rendered);
}

/**
 * The lines of the rendered text that name events by tense and listeners.
 *
 * @return list<string>
 */
function namingHintsLines(string $rendered): array
{
    return array_values(array_filter(
        preg_split('/\R/', $rendered) ?: [],
        static fn (string $line): bool => preg_match('/\bevents?\b/i', $line) === 1
            && preg_match('/tense/i', $line) === 1
            && preg_match('/\blisteners?\b/i', $line) === 1,
    ));
}

it('renders the event and listener naming hints with the default house style', function () {
    $rendered = namingHintsRender(null);

    expect($rendered)->toContain('House PHP style')
        ->and(namingHintsLines($rendered))->not->toBeEmpty();
})->group('R12');

it('drops the naming hints with the house style off', function () {
    $on = namingHintsRender(null);
    $off = namingHintsRender(['version' => 1, 'laravel' => ['house_style' => false]]);

    expect(namingHintsLines($on))->not->toBeEmpty()
        ->and($off)->not->toContain('House PHP style')
        ->and(namingHintsLines($off))->toBe([]);
})->group('R12');
