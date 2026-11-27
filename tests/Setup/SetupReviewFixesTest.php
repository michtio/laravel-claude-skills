<?php

declare(strict_types=1);

/**
 * Gate tests for the S6a review-fix round (laravel-layer), one block per finding.
 *
 * Seams relied on (no new production API except where stated):
 * - Symlinks, MCP, CRLF, deleted file, invalid JSON: the artisan command only.
 * - Recheck before write: the command's output stream. A BufferedOutput subclass
 *   changes a file the moment the diff of that file is printed, which is after the
 *   plan is built and before apply, so no hook is needed in the command.
 * - Core override safety and version header: BoostCore reads
 *   <root>/vendor/laravel/boost/.ai/boost/core.blade.php first, so each test puts
 *   its own core guideline (and installed.json / composer.lock) in the temp project.
 *
 * Pinned phrases (lowercase, substring): "symlink", "changed since the plan",
 * "edited by hand: .mcp.json", "deleted since the last run: <path>", "Syntax error"
 * (json_last_error_msg), "laravel/boost <version>" in the override header.
 */

use Illuminate\Support\Facades\Artisan;
use Symfony\Component\Console\Output\BufferedOutput;

defined('RUNNER_GUIDELINE') || define('RUNNER_GUIDELINE', '.ai/guidelines/claude-skills-runner.md');
defined('CORE_OVERRIDE') || define('CORE_OVERRIDE', '.ai/guidelines/boost/core.blade.php');

if (! function_exists('runSetup')) {
    /**
     * Run the command non-interactively and return the exit code.
     */
    function runSetup(string $dir, array $options = []): int
    {
        return Artisan::call('claude-skills:setup', ['--path' => $dir] + $options);
    }
}

/**
 * Run the command and return [exit code, output].
 *
 * @return array{0: int, 1: string}
 */
function runSetupOutput(string $dir, array $options = []): array
{
    $code = Artisan::call('claude-skills:setup', ['--path' => $dir] + $options);

    return [$code, Artisan::output()];
}

/**
 * Put a Boost core guideline (and optional installed.json / composer.lock) into the project.
 */
function installBoostCore(string $dir, ?string $core = null, ?string $installed = null, ?string $lock = null): void
{
    $path = $dir.'/vendor/laravel/boost/.ai/boost';
    mkdir($path, 0777, true);
    file_put_contents($path.'/core.blade.php', $core ?? file_get_contents(dirname(__DIR__, 2).'/vendor/laravel/boost/.ai/boost/core.blade.php'));
    if ($installed !== null) {
        mkdir($dir.'/vendor/composer', 0777, true);
        file_put_contents($dir.'/vendor/composer/installed.json', $installed);
    }
    if ($lock !== null) {
        file_put_contents($dir.'/composer.lock', $lock);
    }
}

/**
 * A fresh temp directory outside any project.
 */
function outsideDir(): string
{
    $dir = sys_get_temp_dir().'/lcs-outside-'.bin2hex(random_bytes(6));
    mkdir($dir, 0777, true);

    return $dir;
}

function rmTree(string $path): void
{
    if (is_link($path) || is_file($path)) {
        unlink($path);

        return;
    }
    if (! is_dir($path)) {
        return;
    }
    foreach (scandir($path) ?: [] as $entry) {
        if ($entry !== '.' && $entry !== '..') {
            rmTree($path.'/'.$entry);
        }
    }
    rmdir($path);
}

// Finding: symlinks pointing outside the project
// =========================================================================

it('refuses a symlinked owned path, writes nothing and leaves the outside target alone', function (string $link) {
    $dir = $this->project('app', ddev: true);
    $outside = outsideDir();
    $secret = '{"mcpServers":{"other":{"command":"SECRET-OUTSIDE"}}}';

    if ($link === '.ai') {
        mkdir($outside.'/guidelines', 0777, true);
        file_put_contents($outside.'/guidelines/claude-skills-runner.md', 'SECRET-OUTSIDE');
        symlink($outside, $dir.'/.ai');
    } else {
        mkdir($dir.'/.ai/guidelines', 0777, true);
        file_put_contents($outside.'/target', $secret);
        symlink($outside.'/target', $dir.'/'.$link);
    }

    $projectBefore = $this->snapshot($dir);
    $outsideBefore = $this->snapshot($outside);

    [$code, $output] = runSetupOutput($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain($link)->toContain('symlink')
        ->and($this->snapshot($outside))->toBe($outsideBefore)
        ->and($this->snapshot($dir))->toBe($projectBefore);

    rmTree($outside);
})->with([
    'runner guideline' => ['.ai/guidelines/claude-skills-runner.md'],
    '.mcp.json' => ['.mcp.json'],
    'state file' => ['.ai/claude-skills-setup.json'],
    '.ai directory' => ['.ai'],
]);

it('--check refuses a symlinked owned path with exit 1 and does not print the outside content', function (string $link) {
    $dir = $this->project('app', ddev: true);
    $outside = outsideDir();

    if ($link === '.ai') {
        mkdir($outside.'/guidelines', 0777, true);
        file_put_contents($outside.'/guidelines/claude-skills-runner.md', 'SECRET-OUTSIDE');
        symlink($outside, $dir.'/.ai');
    } else {
        mkdir($dir.'/.ai/guidelines', 0777, true);
        file_put_contents($outside.'/target', '{"mcpServers":{"other":{"command":"SECRET-OUTSIDE"}}}');
        symlink($outside.'/target', $dir.'/'.$link);
    }

    [$code, $output] = runSetupOutput($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('symlink')
        ->and($output)->not->toContain('SECRET-OUTSIDE');

    rmTree($outside);
})->with([
    'runner guideline' => ['.ai/guidelines/claude-skills-runner.md'],
    '.mcp.json' => ['.mcp.json'],
    'state file' => ['.ai/claude-skills-setup.json'],
    '.ai directory' => ['.ai'],
]);

// Finding: recheck before write
// =========================================================================

it('refuses to write a file that changed since the plan was built', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    $file = $dir.'/'.RUNNER_GUIDELINE;
    file_put_contents($file, $this->read($dir, RUNNER_GUIDELINE)."\n- first hand edit\n");
    $racer = "changed by someone else after the plan\n";

    $output = new class($file, $racer) extends BufferedOutput {
        private bool $fired = false;

        public function __construct(private string $file, private string $racer)
        {
            parent::__construct();
        }

        protected function doWrite(string $message, bool $newline): void
        {
            parent::doWrite($message, $newline);
            if (! $this->fired && str_contains($message, '+++ b/'.RUNNER_GUIDELINE)) {
                $this->fired = true;
                file_put_contents($this->file, $this->racer);
            }
        }
    };

    $code = Artisan::call('claude-skills:setup', ['--path' => $dir, '--yes' => true], $output);

    expect($code)->toBe(1)
        ->and($output->fetch())->toContain('changed since the plan')
        ->and($this->read($dir, RUNNER_GUIDELINE))->toBe($racer);
});

// Finding: .mcp.json merge
// =========================================================================

it('keeps extra keys of the laravel-boost entry and only rewrites command and args', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', json_encode(['mcpServers' => ['laravel-boost' => [
        'command' => 'php', 'args' => ['artisan', 'boost:mcp'], 'env' => ['APP_ENV' => 'local'], 'timeout' => 30,
    ]]], JSON_PRETTY_PRINT));

    runSetup($dir, ['--yes' => true]);

    expect($this->boostServer($dir))->toBe([
        'command' => 'ddev', 'args' => ['exec', 'php', 'artisan', 'boost:mcp'], 'env' => ['APP_ENV' => 'local'], 'timeout' => 30,
    ]);
});

it('reports a Boost-default entry with extra keys and differing recorded state as edited by hand', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    file_put_contents($dir.'/.mcp.json', json_encode(['mcpServers' => ['laravel-boost' => [
        'command' => 'php', 'args' => ['artisan', 'boost:mcp'], 'env' => ['APP_ENV' => 'local'],
    ]]], JSON_PRETTY_PRINT));

    [, $output] = runSetupOutput($dir, ['--check' => true]);

    expect($output)->toContain('edited by hand: .mcp.json')
        ->not->toContain('boost:install reset');
});

it('reports a custom laravel-boost entry with no state file as edited by hand', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', json_encode(['mcpServers' => ['laravel-boost' => [
        'command' => 'my-wrapper', 'args' => ['boost'],
    ]]], JSON_PRETTY_PRINT));

    [, $output] = runSetupOutput($dir, ['--check' => true]);

    expect($output)->toContain('edited by hand: .mcp.json');
});

// Finding: core override safety
// =========================================================================

it('fails without writing an override when Boost core has an unknown assist call or host-form text', function (string $extra, string $leftover) {
    $dir = $this->project('app', ddev: true);
    $core = file_get_contents(dirname(__DIR__, 2).'/vendor/laravel/boost/.ai/boost/core.blade.php');
    installBoostCore($dir, $core."\n".$extra."\n");
    $before = $this->snapshot($dir);

    [$code, $output] = runSetupOutput($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain($leftover)
        ->and($this->read($dir, CORE_OVERRIDE))->toBeNull()
        ->and($this->snapshot($dir))->toBe($before);
})->with([
    'unknown assist call' => ["- Use {{ \$assist->nodePackageManager() }} to install.", 'nodePackageManager'],
    'unbackticked vendor bin' => ['- Run vendor/bin/pint --dirty before finishing.', 'vendor/bin/pint'],
    'composer install' => ['- Then composer install the dependencies.', 'composer install'],
]);

// Finding: deleted generated file
// =========================================================================

it('notes a generated file deleted since the last run before recreating it', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    unlink($dir.'/'.CORE_OVERRIDE);

    [$code, $output] = runSetupOutput($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('deleted since the last run: '.CORE_OVERRIDE)
        ->and($this->read($dir, CORE_OVERRIDE))->not->toBeNull();
});

// Finding: CRLF
// =========================================================================

it('treats a CRLF runner guideline with the same content as no change', function () {
    $dir = $this->project('app', ddev: true);
    runSetup($dir, ['--yes' => true]);
    file_put_contents($dir.'/'.RUNNER_GUIDELINE, str_replace("\n", "\r\n", $this->read($dir, RUNNER_GUIDELINE)));

    [$code, $output] = runSetupOutput($dir, ['--check' => true]);

    expect($code)->toBe(0)->and($output)->toContain('No changes');
});

// Finding: .mcp.json formatting
// =========================================================================

it('keeps non-ASCII text in other servers unescaped', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', "{\n  \"mcpServers\": {\n    \"other\": {\n      \"command\": \"node\",\n      \"args\": [\"caf\u{e9}.js\"]\n    }\n  }\n}\n");

    runSetup($dir, ['--yes' => true]);

    $json = $this->read($dir, '.mcp.json');
    expect($json)->toContain("caf\u{e9}.js")->not->toContain('\\u00e9');
});

it('preserves the two-space indentation of the existing .mcp.json', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', "{\n  \"mcpServers\": {\n    \"other\": {\n      \"command\": \"node\"\n    }\n  }\n}\n");

    runSetup($dir, ['--yes' => true]);

    $json = (string) $this->read($dir, '.mcp.json');
    expect($json)->toContain("\n  \"mcpServers\"")->not->toContain("\n    \"mcpServers\"")
        ->and($json)->toContain("\n    \"other\"");
});

// Finding: invalid .mcp.json
// =========================================================================

it('includes the JSON error when .mcp.json is invalid', function () {
    $dir = $this->project('app', ddev: true);
    file_put_contents($dir.'/.mcp.json', '{"mcpServers": ');
    $before = $this->snapshot($dir);

    [$code, $output] = runSetupOutput($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Syntax error')
        ->and($this->snapshot($dir))->toBe($before);
});

// Finding: version header
// =========================================================================

it('does not say unknown in the override header when installed.json lacks laravel/boost', function (?string $lock) {
    $dir = $this->project('app', ddev: true);
    installBoostCore(
        $dir,
        null,
        '{"packages":[{"name":"other/package","version":"1.0.0"}]}',
        $lock,
    );

    runSetup($dir, ['--yes' => true]);

    $header = strtok((string) $this->read($dir, CORE_OVERRIDE), "\n");
    expect($header)->not->toContain('unknown')
        ->and($header)->toMatch('/laravel\/boost v?\d+\.\d+/');
})->with([
    'composer.lock has it' => ['{"packages":[],"packages-dev":[{"name":"laravel/boost","version":"v2.5.1"}]}'],
    'no lock' => [null],
]);
