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
}
