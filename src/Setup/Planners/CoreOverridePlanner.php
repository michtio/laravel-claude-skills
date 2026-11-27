<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\BoostCore;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;

/**
 * Writes `.ai/guidelines/boost/core.blade.php`, Boost's override path for its own
 * core guideline, for projects that run through DDEV.
 *
 * Boost's GuidelineComposer resolves the `boost/core` guideline to this file when
 * it exists, so the host `php artisan` lines in Boost's core guideline are
 * replaced in the generated CLAUDE.md without editing anything Boost writes.
 *
 * The override is derived on every run from the core guideline of the Boost the
 * project has installed: only the command helpers (`$assist->artisanCommand()`
 * and its siblings) and any literal host artisan command are swapped for the
 * runner's form; every other line, condition and section of Boost's guidance is
 * kept as Boost ships it. A Blade comment records the Boost version and the
 * source's hash. When Boost's core guideline changes, the derived content changes,
 * the plan shows the refresh as a normal diff (no hand-edit warning, since the
 * old file matches what the setup recorded), and `--check` exits 1 until it runs.
 *
 * Without DDEV the file is not written, and one the setup wrote earlier is removed.
 *
 * @author michtio
 */
final class CoreOverridePlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the override, relative to the project root.
     */
    public const PATH = '.ai/guidelines/boost/core.blade.php';

    /**
     * GuidelineAssist helpers kept as Boost ships them: conditions and values that
     * never render a command. Any other helper left in the override fails the run.
     */
    public const KEPT_HELPERS = [
        'hasMcpEnabled', 'hasSkillsEnabled', 'hasCloudEnabled', 'hasPackage', 'hasComposerScript',
        'supportsPintAgentFormatter', 'appPath', 'inertia', 'enums', 'enumContents', 'project', 'config',
    ];

    /**
     * Host-form command text that must not survive the derivation.
     */
    public const HOST_FORMS = [
        '/\bphp artisan\b/',
        '/\bvendor\/bin\/[A-Za-z0-9._-]*/',
        '/\bcomposer [a-z][a-z-]*/',
        '/\bnpm [a-z][a-z-]*/',
        '/\bnpx [a-z@][A-Za-z0-9@\/._-]*/',
    ];

    // Public Methods
    // =========================================================================

    /**
     * Plan the core override, or its absence without DDEV.
     *
     * @throws SetupException When the project uses DDEV and laravel/boost is not installed, or the
     *                        derived override would still carry a host command or an unknown helper.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        if (! $project->usesDdev()) {
            return PlannedFile::whole($project->root, self::PATH, null);
        }

        $core = BoostCore::locate($project->root);
        $desired = $this->derive($core, $project);
        $leftovers = $this->leftovers($desired, $project);

        if ($leftovers !== []) {
            throw new SetupException(sprintf(
                "Boost's core guideline (%s) has text the setup cannot put in the %s runner's form: %s. No override was written; nothing was written. Update this package, or report the new Boost text.",
                $core->label(),
                $project->runner->value,
                implode(', ', $leftovers),
            ));
        }
        $current = PlannedFile::read($project->root, self::PATH);

        // A Boost release that leaves the core guideline unchanged is not a change:
        // keep the existing file (and the version it names) when only that differs.
        if ($current !== null && $this->body($current) === $this->body($desired)
            && str_contains(strtok($current, "\n") ?: '', 'sha256 '.hash('sha256', $core->content))) {
            $desired = $current;
        }

        return PlannedFile::whole($project->root, self::PATH, $desired);
    }

    /**
     * Derive the override from Boost's core guideline for the project's runner.
     *
     * @author michtio
     */
    public function derive(BoostCore $core, Project $project): string
    {
        $artisan = $project->artisan();

        // Literal host commands first, so the runner forms inserted below are not rewritten again.
        $content = str_replace(['`php artisan ', '`php artisan`'], ['`'.$artisan.' ', '`'.$artisan.'`'], $core->content);

        // A helper echo with a plain string literal becomes the literal command text:
        // {{ $assist->artisanCommand('route:list') }} becomes "<runner> route:list".
        $helpers = [
            'artisanCommand' => $artisan.' ',
            'composerCommand' => $project->composer().' ',
            'nodePackageManagerCommand' => $project->npm().' ',
            'binCommand' => $project->vendorBin(),
        ];
        $content = (string) preg_replace_callback(
            '/\{\{\s*\$assist->(artisanCommand|composerCommand|nodePackageManagerCommand|binCommand)\((?:\'([^\'\\\\]*)\'|"((?:[^"\\\\$]|\\\\")*)")\)\s*\}\}/',
            static function (array $match) use ($helpers): string {
                $argument = ($match[3] ?? '') !== '' ? str_replace('\\"', '"', $match[3]) : ($match[2] ?? '');

                // Text Blade would read as an echo or a directive stays an expression (handled below).
                if (str_contains($argument, '{{') || str_contains($argument, '{!!') || str_contains($argument, '@')) {
                    return $match[0];
                }

                return $helpers[$match[1]].$argument;
            },
            $content,
        );

        // Any other helper call becomes a string concatenation inside the same Blade echo.
        $content = str_replace(
            [
                '$assist->artisanCommand(',
                '$assist->composerCommand(',
                '$assist->nodePackageManagerCommand(',
                '$assist->binCommand(',
                '$assist->artisan()',
            ],
            [
                "('".$artisan." '.",
                "('".$project->composer()." '.",
                "('".$project->npm()." '.",
                "('".$project->vendorBin()."'.",
                "'".$artisan."'",
            ],
            $content,
        );

        $header = sprintf(
            "{{-- Written by claude-skills:setup from %s (%s, %s). Boost's core guideline with its commands in the %s runner's form; everything else as Boost ships it. The setup refreshes this file when Boost's core guideline changes: edit it by hand only if you accept that. --}}\n",
            $core->label(),
            BoostCore::SOURCE,
            'sha256 '.hash('sha256', $core->content),
            $project->runner->value,
        );

        return $header.$content;
    }

    /**
     * What the derived override still carries that the runner cannot run: helper calls
     * outside the allowlist, and host-form commands outside the runner forms the
     * derivation inserted. Empty when the override is safe to write.
     *
     * @return list<string>
     * @author michtio
     */
    public function leftovers(string $override, Project $project): array
    {
        $body = $this->body($override);
        $found = [];

        if (preg_match_all('/\$assist->([A-Za-z_]+)/', $body, $calls) > 0) {
            foreach (array_unique($calls[1]) as $method) {
                if (! in_array($method, self::KEPT_HELPERS, true)) {
                    $found[] = '$assist->'.$method;
                }
            }
        }

        // Remove the runner forms first; what is left must hold no host command.
        $text = str_replace(
            array_unique([$project->artisan(), $project->composer().' ', $project->npm().' ', $project->vendorBin(), 'ddev npx ', 'ddev exec php ']),
            ' ',
            $body,
        );

        foreach (self::HOST_FORMS as $pattern) {
            if (preg_match_all($pattern, $text, $matches) > 0) {
                array_push($found, ...array_unique($matches[0]));
            }
        }

        return array_values(array_unique($found));
    }

    // Private Methods
    // =========================================================================

    /**
     * The override without its first line (the header comment), line endings normalised.
     *
     * @author michtio
     */
    private function body(string $content): string
    {
        $content = str_replace("\r\n", "\n", $content);
        $newline = strpos($content, "\n");

        return $newline === false ? '' : substr($content, $newline + 1);
    }
}
