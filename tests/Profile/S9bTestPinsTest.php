<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer): `laravel.test_pins`.
 * Requirements R8, R23, R24. Skills-gaps row 7.
 * Contract: tests/S9b/CONTRACT.md section 2.
 *
 * Isolation stays the default: every pin is forced unless the profile names it. A named pin
 * takes the profile's value (still forced). Only the four pins that do not decide which
 * database or environment the suite reaches can be named.
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;

/**
 * Every `<env>` of the app's phpunit.xml as name => [value, force], and the `<server>` twins as name => value.
 *
 * @return array{env: array<string, array{0: string, 1: string|null}>, server: array<string, string>}
 */
function s9bPhpunit(string $dir): array
{
    $xml = simplexml_load_string((string) file_get_contents($dir.'/phpunit.xml'));
    $env = [];
    $server = [];

    foreach ($xml->php->env ?? [] as $element) {
        $env[(string) $element['name']] = [(string) $element['value'], isset($element['force']) ? (string) $element['force'] : null];
    }

    foreach ($xml->php->server ?? [] as $element) {
        $server[(string) $element['name']] = (string) $element['value'];
    }

    return ['env' => $env, 'server' => $server];
}

it('overrides a single pin with the profile value, still forced, and keeps every other isolation pin', function () {
    $dir = $this->project('app');
    file_put_contents($dir.'/.env.example', "PAYMENTS_LIVE=true\n");
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $pins = s9bPhpunit($dir);

    expect($code)->toBe(0)
        ->and($pins['env']['SESSION_DRIVER'])->toBe(['file', 'true'])
        ->and($pins['env']['CACHE_STORE'])->toBe(['array', 'true'])
        ->and($pins['env']['QUEUE_CONNECTION'])->toBe(['sync', 'true'])
        ->and($pins['env']['MAIL_MAILER'])->toBe(['array', 'true'])
        ->and($pins['env']['APP_ENV'])->toBe(['testing', 'true'])
        ->and($pins['env']['DB_URL'])->toBe(['', 'true'])
        ->and($pins['env']['DB_DATABASE'][1])->toBe('true')
        ->and($pins['env']['PAYMENTS_LIVE'])->toBe(['false', 'true'])
        ->and($pins['server']['DB_URL'])->toBe('');
});

it('writes the same pins as without test_pins for every name it does not list', function () {
    $plain = $this->project('app');
    $named = $this->project('app');
    $this->writeProfile($named, ['version' => 1, 'laravel' => ['test_pins' => ['CACHE_STORE' => 'file']]]);

    $this->setupRun($plain, ['--yes' => true]);
    $this->setupRun($named, ['--yes' => true]);

    $expected = s9bPhpunit($plain);
    $actual = s9bPhpunit($named);
    $expected['env']['CACHE_STORE'] = ['file', 'true'];

    expect($actual)->toBe($expected);
});

it('moves the server twin with the value for the pins that have one', function (string $name, string $value) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => [$name => $value]]]);

    $this->setupRun($dir, ['--yes' => true]);
    $pins = s9bPhpunit($dir);

    expect($pins['env'][$name])->toBe([$value, 'true'])
        ->and($pins['server'][$name])->toBe($value);
})->with([
    'queue' => ['QUEUE_CONNECTION', 'database'],
    'mail' => ['MAIL_MAILER', 'log'],
]);

it('overrides several pins at once, in a package too', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'database', 'CACHE_STORE' => 'redis']]]);

    $this->setupRun($dir, ['--yes' => true]);
    $xml = (string) file_get_contents($dir.'/phpunit.xml.dist');

    expect($xml)->toContain('<env name="SESSION_DRIVER" value="database" force="true"/>')
        ->toContain('<env name="CACHE_STORE" value="redis" force="true"/>')
        ->toContain('<env name="MAIL_MAILER" value="array" force="true"/>');
});

it('gives Profile::load the pins only when the profile sets them', function () {
    $dir = $this->project('app');

    expect(array_keys(Profile::load($dir)->laravel()))->toBe(['runner', 'house_style', 'phpstan_level', 'monitoring', 'ci']);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);

    expect(Profile::load($dir)->laravel()['test_pins'])->toBe(['SESSION_DRIVER' => 'file']);
});

it('reports No changes on a rerun', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(s9bPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['file', 'true'])
        ->and($code)->toBe(0)
        ->and($output)->toContain('No changes');
});

it('plans only the changed line when a pin value changes, and never calls it a hand edit', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);
    $this->setupRun($dir, ['--yes' => true]);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'database']]]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and(array_values(array_diff($this->diffPaths($output), ['.ai/claude-skills-setup.json'])))->toBe(['phpunit.xml'])
        ->and($output)->toContain('-        <env name="SESSION_DRIVER" value="file" force="true"/>')
        ->toContain('+        <env name="SESSION_DRIVER" value="database" force="true"/>');

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['database', 'true'])
        ->and($this->setupRun($dir, ['--check' => true])[0])->toBe(0);
});

it('goes back to the isolation default when test_pins is removed', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file', 'QUEUE_CONNECTION' => 'database']]]);
    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPhpunit($dir)['env']['QUEUE_CONNECTION'])->toBe(['database', 'true']);

    $this->writeProfile($dir, ['version' => 1]);
    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('edited by hand');

    $this->setupRun($dir, ['--yes' => true]);
    $pins = s9bPhpunit($dir);

    expect($pins['env']['SESSION_DRIVER'])->toBe(['array', 'true'])
        ->and($pins['env']['QUEUE_CONNECTION'])->toBe(['sync', 'true'])
        ->and($pins['server']['QUEUE_CONNECTION'])->toBe('sync')
        ->and($this->setupRun($dir, ['--check' => true])[0])->toBe(0);
});

it('still reports a hand-edited pin the profile does not name', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);
    $this->setupRun($dir, ['--yes' => true]);
    expect(s9bPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['file', 'true']);
    $path = $dir.'/phpunit.xml';
    file_put_contents($path, str_replace('<env name="MAIL_MAILER" value="array" force="true"/>', '<env name="MAIL_MAILER" value="smtp" force="true"/>', (string) file_get_contents($path)));

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpunit.xml');
});

// Validation
// =========================================================================

it('refuses a test_pins that is not an object of allowed names and plain string values, naming the dotted path, writing nothing', function (mixed $pins, string $path) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => $pins]]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: '.$path)
            ->and($this->snapshot($dir))->toBe($before);
    }

    expect(fn () => Profile::load($dir))->toThrow(ProfileException::class);
})->with([
    'a string' => ['file', 'laravel.test_pins'],
    'a number' => [3, 'laravel.test_pins'],
    'the database pin' => [['DB_DATABASE' => 'db'], 'laravel.test_pins.DB_DATABASE'],
    'the connection pin' => [['DB_CONNECTION' => 'mysql'], 'laravel.test_pins.DB_CONNECTION'],
    'the url pin' => [['DB_URL' => 'mysql://x'], 'laravel.test_pins.DB_URL'],
    'the environment pin' => [['APP_ENV' => 'production'], 'laravel.test_pins.APP_ENV'],
    'a live flag' => [['PAYMENTS_LIVE' => 'true'], 'laravel.test_pins.PAYMENTS_LIVE'],
    'an unknown name' => [['TELESCOPE_ENABLED' => 'false'], 'laravel.test_pins.TELESCOPE_ENABLED'],
    'lowercase name' => [['session_driver' => 'file'], 'laravel.test_pins.session_driver'],
    'a number value' => [['SESSION_DRIVER' => 1], 'laravel.test_pins.SESSION_DRIVER'],
    'a boolean value' => [['SESSION_DRIVER' => true], 'laravel.test_pins.SESSION_DRIVER'],
    'a null value' => [['SESSION_DRIVER' => null], 'laravel.test_pins.SESSION_DRIVER'],
    'an empty value' => [['SESSION_DRIVER' => ''], 'laravel.test_pins.SESSION_DRIVER'],
    'a quote in the value' => [['SESSION_DRIVER' => 'a"b'], 'laravel.test_pins.SESSION_DRIVER'],
    'markup in the value' => [['CACHE_STORE' => '<file>'], 'laravel.test_pins.CACHE_STORE'],
    'a space in the value' => [['CACHE_STORE' => 'a b'], 'laravel.test_pins.CACHE_STORE'],
]);

it('accepts each of the four overridable names', function (string $name) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => [$name => 'file']]]);

    expect(Profile::load($dir)->laravel()['test_pins'])->toBe([$name => 'file'])
        ->and($this->setupRun($dir, ['--check' => true])[1])->not->toContain('Invalid profile');
})->with(['SESSION_DRIVER', 'CACHE_STORE', 'QUEUE_CONNECTION', 'MAIL_MAILER']);
