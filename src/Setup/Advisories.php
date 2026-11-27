<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Michtio\LaravelClaudeSkills\Setup\Planners\PhpunitPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\WorkflowPlanner;

/**
 * Lines the setup prints about the project that change nothing on disk: what it
 * cannot or must not fix itself, with the command or the docs that do.
 *
 * - Boost output under the Testbench skeleton: a package whose
 *   `vendor/orchestra/testbench-core/laravel/` holds CLAUDE.md, AGENTS.md or
 *   `.claude/skills/` ran `boost:install` before testbench.yaml pointed
 *   `laravel` at the package root; nothing reads those files.
 * - A PHP version change: on DDEV, when CLAUDE.md says Boost's "running on PHP
 *   X.Y" and DDEV's `php_version` is another version, `boost:update` in the
 *   runner's form refreshes the guidelines.
 * - An existing suite moved to the DDEV database: a package on
 *   `laravel.test_database: ddev` with test files whose PHPUnit file still pins
 *   in-memory sqlite (the move is not applied yet) is told about tables a test
 *   creates (MySQL keeps them) and the connections per-test apps leave open.
 * - Workflows without a database: when the suite runs on a database server,
 *   every workflow the setup does not own that runs the tests and has no
 *   `services:` is named. None is changed. A heuristic: `services:` anywhere in
 *   the file counts, so a workflow with a service on one job and tests on
 *   another is not named (a documented false negative).
 *
 * Proven by tests/Profile/S9d1OutputTest.php: "warns when Boost wrote into the
 * @testbench skeleton", "prints the runner-form boost:update", "warns when
 * test_database ddev moves a package suite", "names every workflow it does not
 * own", each with its negative case.
 *
 * @author michtio
 */
final class Advisories
{
    // Constants
    // =========================================================================

    /**
     * The Laravel skeleton Testbench boots with `laravel: '@testbench'`.
     */
    public const SKELETON = 'vendor/orchestra/testbench-core/laravel';

    /**
     * What Boost writes under base_path(), checked inside the skeleton.
     */
    public const BOOST_OUTPUT = ['CLAUDE.md', 'AGENTS.md', '.claude/skills'];

    /**
     * A workflow command that runs the test suite.
     */
    public const TEST_COMMAND = '/\bvendor\/bin\/(pest|phpunit|paratest)(?![\w:-])|\bartisan test(?![\w:-])|\bcomposer( run(-script)?)? test(?![\w:-])|\btestbench package:test(?![\w:-])/';

    // Public Methods
    // =========================================================================

    /**
     * Every advisory line for the project, in the order they are printed.
     *
     * @return list<string>
     * @author michtio
     */
    public static function lines(Project $project): array
    {
        return array_values(array_filter([
            self::skeleton($project),
            self::boostUpdate($project),
            self::movedSuite($project),
            self::workflowsWithoutDatabase($project),
        ]));
    }

    /**
     * The warning for Boost output inside the Testbench skeleton, or null.
     *
     * @author michtio
     */
    public static function skeleton(Project $project): ?string
    {
        if (! $project->isPackage()) {
            return null;
        }

        $found = array_values(array_filter(
            self::BOOST_OUTPUT,
            static fn (string $path): bool => file_exists($project->root.'/'.self::SKELETON.'/'.$path),
        ));

        if ($found === []) {
            return null;
        }

        return sprintf(
            'Boost wrote into the Testbench skeleton (%s: %s): boost:install ran before testbench.yaml pointed laravel at the package root, and nothing reads those files. Once this setup is applied, run `%s boost:install` again.',
            self::SKELETON,
            implode(', ', $found),
            $project->artisan(),
        );
    }

    /**
     * The boost:update hint after the DDEV PHP version changed, or null.
     *
     * @author michtio
     */
    public static function boostUpdate(Project $project): ?string
    {
        if (! $project->usesDdev()) {
            return null;
        }

        $claude = PlannedFile::read($project->root, 'CLAUDE.md');
        $ddev = $project->ddevConfig()['php_version'] ?? null;

        if ($claude === null || ! is_scalar($ddev) || preg_match('/running on PHP (\d+\.\d+)/', $claude, $match) !== 1) {
            return null;
        }

        $runs = (string) $ddev;

        if ($runs === '' || $runs === $match[1]) {
            return null;
        }

        return sprintf(
            "CLAUDE.md says PHP %s, but DDEV runs PHP %s: run `%s boost:update` so Boost's guidelines name the version the project runs.",
            $match[1],
            $runs,
            $project->artisan(),
        );
    }

    /**
     * The warning for an existing package suite moving to the DDEV database, or null.
     *
     * @author michtio
     */
    public static function movedSuite(Project $project): ?string
    {
        if (! $project->ddevTestDatabase || ! self::hasTests($project->root.'/tests')) {
            return null;
        }

        $phpunit = PlannedFile::read($project->root, (new PhpunitPlanner())->path($project));

        if ($phpunit === null || preg_match('/<env\b(?=[^>]*\bname=["\']DB_DATABASE["\'])(?=[^>]*\bvalue=["\']:memory:["\'])[^>]*>/', $phpunit) !== 1) {
            return null;
        }

        return 'laravel.test_database is ddev: the existing tests move from in-memory sqlite to the DDEV database, which keeps the tables a test creates (DDL commits implicitly, so the next test fails with "already exists"), while the app Testbench builds per test leaves its connections open ("Too many connections"). See docs/profile.md, Test database, for the base TestCase that handles both.';
    }

    /**
     * The line naming workflows that run the tests without a database service, or null.
     *
     * @author michtio
     */
    public static function workflowsWithoutDatabase(Project $project): ?string
    {
        if ($project->usesMemoryDatabase()) {
            return null;
        }

        $files = array_merge(
            glob($project->root.'/.github/workflows/*.yml') ?: [],
            glob($project->root.'/.github/workflows/*.yaml') ?: [],
        );
        sort($files);
        $named = [];

        foreach ($files as $file) {
            $relative = substr($file, strlen($project->root) + 1);

            if ($relative === WorkflowPlanner::PATH || ! is_file($file) || is_link($file)) {
                continue;
            }

            // Comment lines run nothing.
            $content = (string) preg_replace('/^\s*#.*$/m', '', (string) file_get_contents($file));

            if (preg_match(self::TEST_COMMAND, $content) === 1 && preg_match('/^\s+services\s*:/m', $content) !== 1) {
                $named[] = $relative;
            }
        }

        if ($named === []) {
            return null;
        }

        return 'The suite now runs on a database server, but these workflows run the tests without a database service: '.implode(', ', $named).'. Add one to each before the next push; the setup does not change them.';
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether the folder holds a test file (a `*Test.php`), symlinks not followed.
     *
     * @author michtio
     */
    private static function hasTests(string $directory): bool
    {
        if (! is_dir($directory) || is_link($directory)) {
            return false;
        }

        // An unreadable subfolder is skipped: an advisory never stops the setup.
        $files = new \RecursiveIteratorIterator(
            new \RecursiveDirectoryIterator($directory, \FilesystemIterator::SKIP_DOTS),
            \RecursiveIteratorIterator::LEAVES_ONLY,
            \RecursiveIteratorIterator::CATCH_GET_CHILD,
        );

        foreach ($files as $file) {
            if ($file instanceof \SplFileInfo && $file->isFile() && ! $file->isLink() && str_ends_with($file->getFilename(), 'Test.php')) {
                return true;
            }
        }

        return false;
    }
}
