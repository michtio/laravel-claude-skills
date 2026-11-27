<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\Setup;

use FilesystemIterator;
use Orchestra\Testbench\TestCase as Orchestra;
use RecursiveDirectoryIterator;
use RecursiveIteratorIterator;

/**
 * Base class for the S6a gate (laravel-layer): the claude-skills:setup command.
 *
 * Contract the builder implements, pinned by these tests:
 *
 * - Provider: Michtio\LaravelClaudeSkills\LaravelClaudeSkillsServiceProvider
 *   registers the artisan command `claude-skills:setup`
 *   (src/Console/SetupCommand.php). The test app only registers the provider
 *   when the class exists, so a missing implementation fails as "command not
 *   defined", not as a class-loading error.
 * - Signature: `claude-skills:setup {--check} {--yes} {--path=}`. `--path` is
 *   the project root and defaults to base_path(); tests pass it to point at a
 *   temporary copy of a committed fixture.
 * - Runner: DDEV when `<root>/.ddev` is a directory, otherwise host.
 * - Kind: package when composer.json lists orchestra/testbench (require or
 *   require-dev) and `<root>/workbench` is a directory; otherwise app.
 *
 * Each test works on a temp copy of tests/Fixtures/app or tests/Fixtures/package,
 * never on the committed fixture.
 */
abstract class TestCase extends Orchestra
{
    /**
     * @var list<string>
     */
    private array $tempDirs = [];

    /**
     * @param \Illuminate\Foundation\Application $app
     * @return list<class-string>
     */
    protected function getPackageProviders($app): array
    {
        $provider = 'Michtio\\LaravelClaudeSkills\\LaravelClaudeSkillsServiceProvider';

        return class_exists($provider) ? [$provider] : [];
    }

    /**
     * Copy a committed fixture ('app' or 'package') to a fresh temp dir.
     */
    public function project(string $fixture, bool $ddev = false): string
    {
        $dir = sys_get_temp_dir().'/lcs-setup-'.bin2hex(random_bytes(6));
        $this->copyDir(__DIR__.'/../Fixtures/'.$fixture, $dir);
        if ($ddev) {
            mkdir($dir.'/.ddev', 0777, true);
            file_put_contents($dir.'/.ddev/config.yaml', "name: fixture\ntype: laravel\n");
        }
        $this->tempDirs[] = $dir;

        return $dir;
    }

    /**
     * Return a project file's contents, or null when absent.
     */
    protected function read(string $dir, string $relative): ?string
    {
        $path = $dir.'/'.$relative;

        return is_file($path) ? file_get_contents($path) : null;
    }

    /**
     * Return the decoded .mcp.json Boost server entry, or null.
     *
     * @return array<string, mixed>|null
     */
    protected function boostServer(string $dir): ?array
    {
        $json = $this->read($dir, '.mcp.json');

        return $json === null ? null : (json_decode($json, true)['mcpServers']['laravel-boost'] ?? null);
    }

    /**
     * Snapshot every file under $dir as relative path => sha1.
     *
     * @return array<string, string>
     */
    protected function snapshot(string $dir): array
    {
        $out = [];
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS));
        foreach ($it as $file) {
            if ($file->isFile()) {
                $out[substr($file->getPathname(), strlen($dir) + 1)] = sha1_file($file->getPathname());
            }
        }
        ksort($out);

        return $out;
    }

    protected function tearDown(): void
    {
        foreach ($this->tempDirs as $dir) {
            $this->removeDir($dir);
        }
        $this->tempDirs = [];
        parent::tearDown();
    }

    private function copyDir(string $from, string $to): void
    {
        mkdir($to, 0777, true);
        foreach (new FilesystemIterator($from, FilesystemIterator::SKIP_DOTS) as $entry) {
            $target = $to.'/'.$entry->getFilename();
            $entry->isDir() ? $this->copyDir($entry->getPathname(), $target) : copy($entry->getPathname(), $target);
        }
    }

    private function removeDir(string $dir): void
    {
        if (! is_dir($dir)) {
            return;
        }
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS), RecursiveIteratorIterator::CHILD_FIRST);
        foreach ($it as $file) {
            $file->isDir() ? rmdir($file->getPathname()) : unlink($file->getPathname());
        }
        rmdir($dir);
    }
}
