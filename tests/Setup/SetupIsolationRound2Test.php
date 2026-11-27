<?php

declare(strict_types=1);

/**
 * Gate tests for slice S6b, round 2 (review findings). Locked gate file.
 * Uses the helpers of SetupIsolationTest.php (iso*) and the S6a TestCase.
 *
 * ---------------------------------------------------------------------------
 * PINNED CONTRACT (round 2)
 * ---------------------------------------------------------------------------
 *
 * 1. COMMENTED PINS. XML comments in phpunit.xml are never edited: a pinned
 *    element name that appears only inside a comment (`<!-- <env name="X" .../> -->`)
 *    does not count as present. The comment stays byte-identical and the real
 *    forced element is appended (or replaces the real element in place).
 *
 * 2. EXISTING HOOKS. In a git repo with core.hooksPath unset and an executable
 *    non-`.sample` file in .git/hooks, the setup does not plan or run
 *    `git config core.hooksPath .githooks` (--yes does not override), and prints
 *    a notice containing each such hook's file name, "core.hooksPath", and the
 *    manual command `git config core.hooksPath .githooks`. `.sample` files and
 *    non-executable files do not count. --check does not count the unset
 *    hooksPath as a change in this case.
 *
 * 3. TEST DATABASE IDENTIFIER. <slug>_test is always a valid identifier for
 *    MySQL and PostgreSQL: matches /^[a-z][a-z0-9_]*_test$/ and is at most 63
 *    characters. When the slug starts with a digit (or is empty) it gets the
 *    prefix "t_" ("acme/9shop" -> t_9shop_test). A slug that is too long is cut
 *    so that the whole name, "_test" included, is 63 characters, keeping the
 *    "_test" suffix and with no trailing underscore before it. A name that
 *    needs no change is unchanged (the S6b rule for "laravel/laravel" holds).
 *    DdevDatabasePlanner::shell() returns null or throws for a database name
 *    that is not such an identifier, for every connection, so nothing
 *    unquoted and unvalidated reaches a shell or SQL.
 *
 * 4. HOST NOTICE. A host (non-DDEV) app whose connection is mysql, mariadb or
 *    pgsql prints a notice containing "<name>_test must exist" and the command
 *    `CREATE DATABASE <name>_test`. A DDEV app (the hook creates it), a package
 *    and an sqlite app print no such notice.
 *
 * 5. COMMIT-MSG. Blocks AI attribution only (see the cases below). Human
 *    collaboration trailers pass.
 *
 * 6. GITLEAKS. .gitleaks.toml uses `[[allowlists]]` (gitleaks >= 8.25; the
 *    single `[allowlist]` table is replaced, README config schema) with `paths`
 *    regexes that escape their dots.
 */

use Symfony\Component\Yaml\Yaml;

const ISO2_COMMENTS = [
    '<!-- <env name="DB_DATABASE" value="old"/> -->',
    '<!-- <env name="APP_ENV" value="x"/> -->',
];

/**
 * Stock Laravel 12 phpunit.xml, with the given extra lines at the start of `<php>`.
 */
function iso2Stock(string $inPhp = ''): string
{
    return <<<XML
<?xml version="1.0" encoding="UTF-8"?>
<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"
         bootstrap="vendor/autoload.php"
         colors="true"
>
    <testsuites>
        <testsuite name="Unit">
            <directory>tests/Unit</directory>
        </testsuite>
        <testsuite name="Feature">
            <directory>tests/Feature</directory>
        </testsuite>
    </testsuites>
    <source>
        <include>
            <directory>app</directory>
        </include>
    </source>
    <php>
{$inPhp}        <env name="APP_ENV" value="testing"/>
        <env name="APP_MAINTENANCE_DRIVER" value="file"/>
        <env name="BCRYPT_ROUNDS" value="4"/>
        <env name="CACHE_STORE" value="array"/>
        <env name="DB_CONNECTION" value="sqlite"/>
        <env name="DB_DATABASE" value=":memory:"/>
        <env name="MAIL_MAILER" value="array"/>
        <env name="QUEUE_CONNECTION" value="sync"/>
        <env name="SESSION_DRIVER" value="array"/>
        <env name="PULSE_ENABLED" value="false"/>
        <env name="TELESCOPE_ENABLED" value="false"/>
        <env name="NIGHTWATCH_ENABLED" value="false"/>
    </php>
</phpunit>

XML;
}

/**
 * Names of the real (non-comment) env elements, name => count.
 *
 * @return array<string, int>
 */
function iso2EnvCounts(string $xml): array
{
    $counts = [];
    foreach (simplexml_load_string($xml)->php->env ?? [] as $env) {
        $name = (string) $env['name'];
        $counts[$name] = ($counts[$name] ?? 0) + 1;
    }

    return $counts;
}

// 1. Commented pins
// =========================================================================

it('leaves commented-out env elements byte-identical and pins the real ones (comments only in <php>)', function () {
    $dir = $this->project('app', ddev: true);
    $xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<phpunit bootstrap=\"vendor/autoload.php\">\n    <php>\n"
        .'        '.ISO2_COMMENTS[0]."\n        ".ISO2_COMMENTS[1]."\n    </php>\n</phpunit>\n";
    isoPut($dir, 'phpunit.xml', $xml);

    isoSetup($dir, ['--yes' => true]);

    $out = $this->read($dir, 'phpunit.xml');
    foreach (ISO_STANDARD_PINS as $name => $value) {
        isoPinned(isoEnv($out), $name, $value);
    }
    isoPinned(isoEnv($out), 'DB_DATABASE', 'app_test');
    isoPinned(isoEnv($out), 'DB_CONNECTION', 'mysql');
    foreach (ISO_COMMENTS as $comment) {
        expect($out)->toContain($comment);
    }
    expect(iso2EnvCounts($out)['DB_DATABASE'])->toBe(1)->and(iso2EnvCounts($out)['APP_ENV'])->toBe(1);
});

it('replaces the real stock element in place, not the commented one before it (Laravel 12 shape)', function () {
    $dir = $this->project('app', ddev: true);
    isoPut($dir, 'phpunit.xml', iso2Stock('        '.ISO2_COMMENTS[0]."\n        ".ISO2_COMMENTS[1]."\n"));

    isoSetup($dir, ['--yes' => true]);

    $out = $this->read($dir, 'phpunit.xml');
    foreach (ISO2_COMMENTS as $comment) {
        expect($out)->toContain($comment);
    }
    $env = isoEnv($out);
    foreach (ISO_STANDARD_PINS as $name => $value) {
        isoPinned($env, $name, $value);
    }
    isoPinned($env, 'DB_CONNECTION', 'mysql');
    isoPinned($env, 'DB_DATABASE', 'app_test');
    expect(iso2EnvCounts($out)['APP_ENV'])->toBe(1)
        ->and(iso2EnvCounts($out)['DB_DATABASE'])->toBe(1)
        ->and($env['BCRYPT_ROUNDS'])->toBe(['4', null]);
    isoTwin($out, 'DB_DATABASE', 'app_test');

    expect(isoSetup($dir, ['--check' => true])[0])->toBe(0);
});

// 2. Existing git hooks
// =========================================================================

/**
 * Put a hook in .git/hooks of a git repo.
 */
function iso2Hook(string $dir, string $name, bool $executable = true): void
{
    isoPut($dir, '.git/hooks/'.$name, "#!/bin/sh\nexit 0\n");
    chmod($dir.'/.git/hooks/'.$name, $executable ? 0755 : 0644);
}

it('does not switch off an existing executable hook, and names it and the manual command', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    iso2Hook($dir, 'pre-commit');

    [$code, $output] = isoSetup($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and(isoGit($dir, 'config --get core.hooksPath')[1])->toBe('')
        ->and($output)->toContain('pre-commit')
        ->and($output)->toContain('core.hooksPath')
        ->and($output)->toContain('git config core.hooksPath .githooks');
    // the plan never offers the action either
    expect($output)->not->toContain('Apply these changes?');
});

it('names every existing hook', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    iso2Hook($dir, 'pre-commit');
    iso2Hook($dir, 'pre-push');

    [, $output] = isoSetup($dir, ['--yes' => true]);

    expect($output)->toContain('pre-commit')->toContain('pre-push');
});

it('still sets hooksPath when only .sample or non-executable hooks exist', function () {
    $dir = $this->project('app');
    isoGit($dir, 'init -q');
    iso2Hook($dir, 'pre-commit.sample');
    iso2Hook($dir, 'post-merge', executable: false);

    isoSetup($dir, ['--yes' => true]);

    expect(isoGit($dir, 'config --get core.hooksPath'))->toBe([0, '.githooks']);
});

it('--check does not count the unset hooksPath as a change when a hook exists', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    isoGit($dir, 'init -q');
    iso2Hook($dir, 'pre-commit');

    expect(isoSetup($dir, ['--check' => true])[0])->toBe(0);
});

// 3. Test database identifier
// =========================================================================

it('produces a valid identifier for a digit-leading composer name', function () {
    $dir = $this->project('app', ddev: true);
    isoComposer($dir, ['name' => 'acme/9shop']);

    isoSetup($dir, ['--yes' => true]);

    $env = isoEnv($this->read($dir, 'phpunit.xml'));
    isoPinned($env, 'DB_DATABASE', 't_9shop_test');
    expect($this->read($dir, ISO_DDEV_HOOK))->toContain('t_9shop_test');
});

it('keeps a very long name within 63 characters, valid, ending in _test', function (string $name) {
    $dir = $this->project('app', ddev: true);
    isoComposer($dir, ['name' => 'acme/'.$name]);

    isoSetup($dir, ['--yes' => true]);

    $database = isoEnv($this->read($dir, 'phpunit.xml'))['DB_DATABASE'][0];
    expect(strlen($database))->toBeLessThanOrEqual(63)
        ->and($database)->toMatch('/^[a-z][a-z0-9_]*_test$/')
        ->and($database)->not->toContain('__test')
        ->and($this->read($dir, ISO_DDEV_HOOK))->toContain($database);
})->with([
    'long' => [str_repeat('shop-and-more-', 8)],
    'long, digit first' => ['9'.str_repeat('a', 90)],
    'exactly at the limit plus one' => [str_repeat('a', 59)],
]);

it('keeps a short valid name unchanged', function () {
    $dir = $this->project('app', ddev: true);
    isoComposer($dir, ['name' => 'Acme/My-Shop.v2']);

    isoSetup($dir, ['--yes' => true]);

    isoPinned(isoEnv($this->read($dir, 'phpunit.xml')), 'DB_DATABASE', 'my_shop_v2_test');
});

it('the pgsql hook for a digit-leading name uses the valid identifier only', function () {
    $dir = $this->project('app', ddev: true);
    isoComposer($dir, ['name' => 'acme/9shop']);
    isoPut($dir, '.env', "DB_CONNECTION=pgsql\n");

    isoSetup($dir, ['--yes' => true]);

    $exec = Yaml::parse($this->read($dir, ISO_DDEV_HOOK))['hooks']['post-start'][0]['exec'];
    expect($exec)->toContain('t_9shop_test')->not->toMatch('/(?<![a-z0-9_])9shop_test/');
});

it('the database hook refuses an identifier that is not safe', function (string $connection, string $name) {
    $planner = new \Michtio\LaravelClaudeSkills\Setup\Planners\DdevDatabasePlanner();

    try {
        $shell = $planner->shell($connection, $name);
    } catch (\Throwable) {
        $shell = null;
    }

    expect($shell)->toBeNull();
})->with([
    ['pgsql', '9shop_test'],
    ['pgsql', 'a"; DROP DATABASE db; --'],
    ['pgsql', "x' || (select 1) || '"],
    ['mysql', '9shop_test'],
    ['mysql', 'a`; DROP DATABASE db; --'],
    ['mariadb', 'my-shop_test'],
    ['pgsql', str_repeat('a', 60).'_test'],
]);

// 4. Host database notice
// =========================================================================

it('tells a host app on a server database that the test database must exist', function (string $connection) {
    $dir = $this->project('app');
    isoPut($dir, '.env', "DB_CONNECTION=$connection\n");

    [$code, $output] = isoSetup($dir, ['--yes' => true]);

    expect($code)->toBe(0)
        ->and($output)->toContain('app_test must exist')
        ->and($output)->toContain('CREATE DATABASE app_test');
})->with(['mysql', 'mariadb', 'pgsql']);

it('prints no such notice for a DDEV app, an sqlite app or a package', function () {
    $ddev = $this->project('app', ddev: true);
    isoPut($ddev, '.env', "DB_CONNECTION=mysql\n");
    $sqlite = $this->project('app');
    isoPut($sqlite, '.env', "DB_CONNECTION=sqlite\n");
    $package = $this->project('package');

    foreach ([$ddev, $sqlite, $package] as $dir) {
        expect(isoSetup($dir, ['--yes' => true])[1])->not->toContain('must exist');
    }
});

// 5. commit-msg: AI attribution only
// =========================================================================

it('commit-msg blocks AI attribution and passes human collaboration', function (string $message, int $expected) {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    isoPut($dir, 'MSG', $message);

    [$code, $output] = isoRun($dir, '.githooks/commit-msg', arg: 'MSG');

    expect($code)->toBe($expected);
    if ($expected !== 0) {
        expect($output)->not->toBe('');
    }
})->with([
    // rejected: trailer naming an AI tool or vendor address
    'claude trailer' => ["Add thing\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\n", 1],
    'anthropic address only' => ["Add thing\n\nCo-authored-by: Helper <noreply@anthropic.com>\n", 1],
    'lowercase, copilot' => ["Add thing\n\nco-authored-by: GitHub Copilot <copilot@github.com>\n", 1],
    'uppercase header, chatgpt' => ["Add thing\n\nCO-AUTHORED-BY: ChatGPT <bot@example.com>\n", 1],
    'leading spaces, openai' => ["Add thing\n\n   Co-authored-by: OpenAI Codex <x@openai.com>\n", 1],
    'leading tab, cursor' => ["Add thing\n\n\tCo-Authored-By: Cursor Agent <cursoragent@cursor.com>\n", 1],
    'gemini' => ["Add thing\n\nCo-authored-by: Gemini <gemini@google.com>\n", 1],
    'devin' => ["Add thing\n\nCo-authored-by: Devin AI <devin@cognition.ai>\n", 1],
    'aider' => ["Add thing\n\nCo-authored-by: aider (gpt-4) <noreply@aider.chat>\n", 1],
    // rejected: generated with/by an AI tool, anywhere, any case
    'generated with claude' => ["Add thing\n\nGenerated with Claude Code\n", 1],
    'generated by copilot, mid-line' => ["Add thing\n\nThis was generated by GitHub Copilot, then edited.\n", 1],
    'GENERATED WITH CHATGPT' => ["Add thing\n\nGENERATED WITH CHATGPT\n", 1],
    'generated with cursor mid-line' => ["Add thing\n\nthing (Generated With Cursor)\n", 1],
    'generated by gemini' => ["Add thing\n\nGenerated by Gemini\n", 1],
    // rejected: session line and robot footer
    'claude-session' => ["Add thing\n\nClaude-Session: https://example.com/s/1\n", 1],
    'robot footer' => ["Add thing\n\n\u{1F916} Generated with [Claude Code](https://claude.com/claude-code)\n", 1],
    'robot emoji footer alone' => ["Add thing\n\n\u{1F916} Generated with a helper\n", 1],
    // accepted: humans and ordinary prose
    'human trailer' => ["Add thing\n\nCo-authored-by: Jane Doe <jane@example.com>\n", 0],
    'human trailer, capitalised' => ["Add thing\n\nCo-Authored-By: John Smith <john@acme.dev>\n", 0],
    'fixture generated with faker' => ["Seed users\n\nThe fixture is generated with Faker.\n", 0],
    'generated by hand' => ["Add thing\n\nGenerated by hand from the export.\n", 0],
    'generated with the build script' => ["Add thing\n\nGenerated with the build script.\n", 0],
    'comment lines ignored' => ["Add thing\n\n# Co-Authored-By: Claude <noreply@anthropic.com>\n# Generated with Claude Code\n", 0],
]);

// 6. gitleaks config
// =========================================================================

/**
 * The path regexes of the gitleaks config: every '''...''' string.
 *
 * @return list<string>
 */
function iso2GitleaksPaths(string $toml): array
{
    preg_match_all("/'''(.*?)'''/", $toml, $matches);

    return $matches[1];
}

it('writes the current gitleaks allowlist schema', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    $toml = $this->read($dir, '.gitleaks.toml');

    expect($toml)->toMatch('/^\[\[allowlists\]\]\s*$/m')
        ->not->toMatch('/^\[allowlist\]\s*$/m')
        ->toContain('useDefault = true');
});

it('escapes every dot in the allowlist path regexes', function () {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    $paths = iso2GitleaksPaths($this->read($dir, '.gitleaks.toml'));

    expect($paths)->not->toBeEmpty();
    foreach ($paths as $regex) {
        // every dot is escaped, or is the start of .* / .+ / .?
        expect($regex)->not->toMatch('/(?<!\\\\)\.(?![*+?])/', "unescaped dot in $regex");
    }
    $matches = fn (string $subject): bool => count(array_filter($paths, fn (string $re): bool => preg_match('~'.$re.'~', $subject) === 1)) > 0;
    expect($matches('.env.example'))->toBeTrue()
        ->and($matches('app/.env.example'))->toBeTrue()
        ->and($matches('tests/Fixtures/a/b.php'))->toBeTrue()
        ->and($matches('xenvxexample'))->toBeFalse()
        ->and($matches('app/Aenv.example'))->toBeFalse();
});
