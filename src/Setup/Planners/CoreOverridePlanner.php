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

    // Public Methods
    // =========================================================================

    /**
     * Plan the core override, or its absence without DDEV.
     *
     * @throws SetupException When the project uses DDEV and laravel/boost is not installed.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        if (! $project->usesDdev()) {
            return PlannedFile::whole($project->root, self::PATH, null);
        }

        $core = BoostCore::locate($project->root);
        $desired = $this->derive($core, $project);
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
            "{{-- Written by claude-skills:setup from laravel/boost %s (%s, %s). Boost's core guideline with its commands in the %s runner's form; everything else as Boost ships it. The setup refreshes this file when Boost's core guideline changes: edit it by hand only if you accept that. --}}\n",
            $core->version,
            BoostCore::SOURCE,
            'sha256 '.hash('sha256', $core->content),
            $project->runner->value,
        );

        return $header.$content;
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
