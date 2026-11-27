<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\Profile;

use Illuminate\Support\Facades\Artisan;
use Michtio\LaravelClaudeSkills\Tests\Setup\TestCase;

/**
 * Base class for the S7 gate (laravel-layer): the profile and the CI workflow.
 *
 * The contract is tests/Profile/CONTRACT.md. It builds on the S6 contract (see
 * tests/Setup/TestCase.php): the same command, the same temporary copies of the
 * committed fixtures, the same --path option. Every project here has no git
 * repository, so the hooks-path action is skipped and the only "Run:" lines are
 * the ones the profile causes.
 */
abstract class ProfileTestCase extends TestCase
{
    public const PROFILE = '.ai/skills-profile.json';

    public const WORKFLOW = '.github/workflows/claude-skills-gate.yml';

    public const STATE = '.ai/claude-skills-setup.json';

    /**
     * The reader of DDEV's database (S9b round 4). The setup resolves it from the container; tests feed it values.
     */
    public const DDEV_SOURCE = 'Michtio\\LaravelClaudeSkills\\Setup\\DdevDatabaseSource';

    /**
     * Write the profile file (an array is encoded as pretty JSON; a string is written as is).
     *
     * @param array<string, mixed>|string $profile
     */
    public function writeProfile(string $dir, array|string $profile): void
    {
        $content = is_string($profile) ? $profile : json_encode($profile, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES)."\n";

        if (! is_dir($dir.'/.ai')) {
            mkdir($dir.'/.ai', 0777, true);
        }

        file_put_contents($dir.'/'.self::PROFILE, $content);
    }

    /**
     * Run the command and return the exit code and the whole output.
     *
     * @param array<string, mixed> $options
     * @return array{int, string}
     */
    protected function setupRun(string $dir, array $options = []): array
    {
        $code = Artisan::call('claude-skills:setup', ['--path' => $dir] + $options);

        return [$code, Artisan::output()];
    }

    /**
     * The paths shown as changed files in a plan: the "+++ b/<path>" lines, in order.
     * A deleted file is shown as "--- a/<path>" and "+++ /dev/null", so it is listed from its "---" line.
     *
     * @return list<string>
     */
    protected function diffPaths(string $output): array
    {
        $paths = [];

        foreach (preg_split('/\R/', $output) ?: [] as $line) {
            if (preg_match('#^\+\+\+ b/(.+)$#', $line, $m) === 1) {
                $paths[] = $m[1];
            } elseif (preg_match('#^--- a/(.+)$#', $line, $m) === 1 && ! in_array($m[1], $paths, true)) {
                $paths[] = $m[1];
            }
        }

        return array_values(array_unique($paths));
    }

    /**
     * Every "Run: <line>" of a plan, without the prefix, in order.
     *
     * @return list<string>
     */
    protected function runLines(string $output): array
    {
        $lines = [];

        foreach (preg_split('/\R/', $output) ?: [] as $line) {
            if (str_starts_with($line, 'Run: ')) {
                $lines[] = substr($line, 5);
            }
        }

        return $lines;
    }

    /**
     * The profile for a project that is fully set up already (profile written, setup applied).
     *
     * @param array<string, mixed> $profile
     * @param string|null $prepare Name of a function called with the project dir before the profile is written.
     */
    protected function applied(string $fixture, array $profile, bool $ddev = false, ?string $prepare = null): string
    {
        $dir = $this->project($fixture, ddev: $ddev);

        if ($prepare !== null) {
            $prepare($dir);
        }

        $this->writeProfile($dir, $profile);
        [$code] = $this->setupRun($dir, ['--yes' => true]);
        expect($code)->toBe(0);

        return $dir;
    }

    /**
     * Run every test with a reader that reports DDEV's default database (mariadb 11.8), so a package on
     * test_database ddev with no database block never shells out. Skipped while the interface does not exist.
     */
    protected function setUp(): void
    {
        parent::setUp();

        if (interface_exists(self::DDEV_SOURCE)) {
            $this->fakeDdevDatabase(['type' => 'mariadb', 'version' => '11.8']);
        }
    }

    /**
     * Bind a DdevDatabaseSource that returns $database (type and version, or null for unreadable), or throws when
     * $database is false: the reader must then never be consulted.
     *
     * @param array{type: string, version: string}|null|false $database
     */
    public function fakeDdevDatabase(array|null|false $database): void
    {
        $this->app->instance(self::DDEV_SOURCE, $this->ddevSource($database));
    }

    /**
     * A fresh anonymous implementation of the reader (declared lazily: the interface may not exist yet).
     *
     * @param array{type: string, version: string}|null|false $database
     */
    private function ddevSource(array|null|false $database): object
    {
        $interface = self::DDEV_SOURCE;

        return eval('return new class($database) implements \\'.$interface.' {
            public function __construct(private readonly array|null|false $database) {}

            public function read(string $root): ?array
            {
                if ($this->database === false) {
                    throw new \\RuntimeException("The DDEV database reader must not be consulted here.");
                }

                return $this->database;
            }
        };');
    }
}
