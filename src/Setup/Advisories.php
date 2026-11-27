<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use Michtio\LaravelClaudeSkills\Setup\Planners\PhpunitPlanner;
use Michtio\LaravelClaudeSkills\Setup\Planners\WorkflowPlanner;
use Symfony\Component\Yaml\Exception\ParseException;
use Symfony\Component\Yaml\Yaml;

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
 *   every workflow the setup does not own with a job that runs the tests and has no
 *   database service (a mysql, mariadb, postgres, postgis or percona image, or one
 *   set from an expression) is named, judged per job. None is changed.
 *
 * Proven by tests/Profile/S9d1OutputTest.php: "warns when Boost wrote into the
 * @testbench skeleton", "prints the runner-form boost:update", "warns when
 * test_database ddev moves a package suite", "names every workflow it does not
 * own", each with its negative case; and by tests/Profile/WorkflowAdvisoryTest.php:
 * "does not take a composer test:<name> script for the test suite", "ignores a
 * test command that only appears in a comment line", "reads a single-quoted
 * in-memory DB_DATABASE pin as not yet moved", "names a workflow whose database
 * service is on another job than its tests", "names a workflow whose test job has
 * only a redis service", "does not name a workflow whose test job has a
 * mysql/mysql-server service", "does not name a workflow whose database image comes
 * from the matrix".
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

    /**
     * A service image that is a database server the suite can run on (an image
     * set from an expression, such as a matrix value, counts as one too).
     */
    public const DATABASE_IMAGE = '/(^|\/)(mysql|mariadb|postgres|postgis|percona)[\w.-]*(:|$)/i';

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

            if (self::testsWithoutDatabase((string) file_get_contents($file))) {
                $named[] = $relative;
            }
        }

        if ($named === []) {
            return null;
        }

        return 'The suite runs on a database server, but these workflows run the tests without a database service: '.implode(', ', $named).'. Add one to each before the next push; the setup does not change them.';
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether a workflow has a job that runs the tests without a database service:
     * a step whose `run` matches TEST_COMMAND, in a job with no service whose
     * `image` is mysql, mariadb or postgres (a redis-only job counts as missing
     * one). A file that does not parse falls back to a text check over the whole
     * file, comment lines left out.
     *
     * @author michtio
     */
    private static function testsWithoutDatabase(string $content): bool
    {
        try {
            $workflow = Yaml::parse($content);
        } catch (ParseException) {
            $text = (string) preg_replace('/^\s*#.*$/m', '', $content);

            return preg_match(self::TEST_COMMAND, $text) === 1 && preg_match('/^\s+services\s*:/m', $text) !== 1;
        }

        $jobs = is_array($workflow) && is_array($workflow['jobs'] ?? null) ? $workflow['jobs'] : [];

        foreach ($jobs as $job) {
            if (is_array($job) && self::runsTests($job) && ! self::hasDatabaseService($job)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Whether one of the job's steps runs the test suite.
     *
     * @param array<mixed> $job
     * @author michtio
     */
    private static function runsTests(array $job): bool
    {
        foreach (is_array($job['steps'] ?? null) ? $job['steps'] : [] as $step) {
            if (is_array($step) && is_string($step['run'] ?? null) && preg_match(self::TEST_COMMAND, $step['run']) === 1) {
                return true;
            }
        }

        return false;
    }

    /**
     * Whether the job has a service whose image is a database server.
     *
     * @param array<mixed> $job
     * @author michtio
     */
    private static function hasDatabaseService(array $job): bool
    {
        foreach (is_array($job['services'] ?? null) ? $job['services'] : [] as $service) {
            $image = is_array($service) ? ($service['image'] ?? null) : $service;

            if (is_string($image) && (str_contains($image, '${{') || preg_match(self::DATABASE_IMAGE, $image) === 1)) {
                return true;
            }
        }

        return false;
    }

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
