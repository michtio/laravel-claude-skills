<?php

declare(strict_types=1);

/**
 * Gate tests for slice S9b (laravel-layer), round 1b: the `env` value of `laravel.test_pins`.
 * Requirements R8, R23, R24. Skills-gaps row 7.
 * Contract: tests/S9b/CONTRACT.md section 2.
 *
 * `env` means the pin is written without force, so a value the shell or `ddev exec env X=y` sets
 * wins, and the phpunit default applies when nothing is set. AK-S4's gate runs the Session tests
 * with SESSION_DRIVER=file, then database, then redis in one gate: a fixed value cannot serve it.
 * The real run is tests/gate/test_s9b_ddev.py (test_6).
 */

use Michtio\LaravelClaudeSkills\Profile\Profile;
use Michtio\LaravelClaudeSkills\Profile\ProfileException;

/**
 * The `<env>` elements of phpunit.xml as name => [value, force], and the `<server>` names.
 *
 * @return array{env: array<string, array{0: string, 1: string|null}>, server: list<string>}
 */
function s9bPassPhpunit(string $dir): array
{
    $xml = simplexml_load_string((string) file_get_contents($dir.'/phpunit.xml'));
    $env = [];
    $server = [];

    foreach ($xml->php->env ?? [] as $element) {
        $env[(string) $element['name']] = [(string) $element['value'], isset($element['force']) ? (string) $element['force'] : null];
    }

    foreach ($xml->php->server ?? [] as $element) {
        $server[] = (string) $element['name'];
    }

    return ['env' => $env, 'server' => $server];
}

it('writes an env pin without force and with the phpunit default as its value', function (string $name, string $default) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => [$name => 'env']]]);

    [$code] = $this->setupRun($dir, ['--yes' => true]);
    $pins = s9bPassPhpunit($dir);
    $xml = (string) file_get_contents($dir.'/phpunit.xml');

    expect($code)->toBe(0)
        ->and($pins['env'][$name])->toBe([$default, null])
        ->and($xml)->toContain('<env name="'.$name.'" value="'.$default.'"/>')
        ->not->toContain('<env name="'.$name.'" value="'.$default.'" force=');
})->with([
    'session' => ['SESSION_DRIVER', 'array'],
    'cache' => ['CACHE_STORE', 'array'],
    'queue' => ['QUEUE_CONNECTION', 'sync'],
    'mail' => ['MAIL_MAILER', 'array'],
]);

it('writes no server twin for an env pin, which would beat the shell value', function (string $name) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => [$name => 'env']]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPassPhpunit($dir)['server'])->not->toContain($name);
})->with(['QUEUE_CONNECTION', 'MAIL_MAILER']);

it('keeps every other pin forced, and mixes a value pin with an env pin', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env', 'CACHE_STORE' => 'redis']]]);

    $this->setupRun($dir, ['--yes' => true]);
    $pins = s9bPassPhpunit($dir)['env'];

    expect($pins['SESSION_DRIVER'])->toBe(['array', null])
        ->and($pins['CACHE_STORE'])->toBe(['redis', 'true'])
        ->and($pins['QUEUE_CONNECTION'])->toBe(['sync', 'true'])
        ->and($pins['MAIL_MAILER'])->toBe(['array', 'true'])
        ->and($pins['APP_ENV'])->toBe(['testing', 'true'])
        ->and($pins['DB_URL'])->toBe(['', 'true'])
        ->and($pins['DB_DATABASE'][1])->toBe('true');
});

it('works in a package: the .dist file carries the unforced element', function () {
    $dir = $this->project('package');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env']]]);

    $this->setupRun($dir, ['--yes' => true]);

    expect((string) file_get_contents($dir.'/phpunit.xml.dist'))->toContain('<env name="SESSION_DRIVER" value="array"/>');
});

it('gives Profile::load the env value as written', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env']]]);

    expect(Profile::load($dir)->laravel()['test_pins'])->toBe(['SESSION_DRIVER' => 'env']);
});

it('reports No changes on a rerun, an env pin is not a hand edit', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env']]]);
    $this->setupRun($dir, ['--yes' => true]);

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect(s9bPassPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['array', null])
        ->and($code)->toBe(0)
        ->and($output)->toContain('No changes')
        ->not->toContain('edited by hand');
});

it('plans only that line when a value pin becomes env and back, never a hand edit', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'file']]]);
    $this->setupRun($dir, ['--yes' => true]);

    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env']]]);
    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->not->toContain('edited by hand')
        ->and(array_values(array_diff($this->diffPaths($output), ['.ai/claude-skills-setup.json'])))->toBe(['phpunit.xml'])
        ->and($output)->toContain('-        <env name="SESSION_DRIVER" value="file" force="true"/>')
        ->toContain('+        <env name="SESSION_DRIVER" value="array"/>');

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPassPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['array', null]);

    $this->writeProfile($dir, ['version' => 1]);
    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->not->toContain('edited by hand')
        ->toContain('+        <env name="SESSION_DRIVER" value="array" force="true"/>');

    $this->setupRun($dir, ['--yes' => true]);

    expect(s9bPassPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['array', 'true'])
        ->and($this->setupRun($dir, ['--check' => true])[0])->toBe(0);
});

it('still reports a hand-forced pin that the profile marks env', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env']]]);
    $this->setupRun($dir, ['--yes' => true]);
    expect(s9bPassPhpunit($dir)['env']['SESSION_DRIVER'])->toBe(['array', null]);
    $path = $dir.'/phpunit.xml';
    file_put_contents($path, str_replace('<env name="SESSION_DRIVER" value="array"/>', '<env name="SESSION_DRIVER" value="array" force="true"/>', (string) file_get_contents($path)));

    [$code, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('edited by hand: phpunit.xml');
});

it('prints an env pin as NAME=env with its source', function () {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => 'env', 'CACHE_STORE' => 'file']]]);

    [, $output] = $this->setupRun($dir, ['--check' => true]);

    expect($output)->toMatch('/^  test_pins: SESSION_DRIVER=env, CACHE_STORE=file \(profile\)$/m');
});

it('refuses env for a pin that cannot be named, naming the dotted path, writing nothing', function (string $name) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => [$name => 'env']]]);
    $before = $this->snapshot($dir);

    foreach ([['--check' => true], ['--yes' => true]] as $options) {
        [$code, $output] = $this->setupRun($dir, $options);

        expect($code)->toBe(1)
            ->and($output)->toContain('Invalid profile .ai/skills-profile.json: laravel.test_pins.'.$name)
            ->and($this->snapshot($dir))->toBe($before);
    }

    expect(fn () => Profile::load($dir))->toThrow(ProfileException::class);
})->with(['DB_DATABASE', 'DB_CONNECTION', 'DB_URL', 'APP_ENV', 'PAYMENTS_LIVE', 'TELESCOPE_ENABLED']);

it('refuses an unknown or malformed value for an allowed name', function (mixed $value) {
    $dir = $this->project('app');
    $this->writeProfile($dir, ['version' => 1, 'laravel' => ['test_pins' => ['SESSION_DRIVER' => $value]]]);
    $before = $this->snapshot($dir);

    [$code, $output] = $this->setupRun($dir, ['--yes' => true]);

    expect($code)->toBe(1)
        ->and($output)->toContain('Invalid profile .ai/skills-profile.json: laravel.test_pins.SESSION_DRIVER')
        ->and($this->snapshot($dir))->toBe($before);
})->with([
    'env in an array' => [['env']],
    'a boolean' => [true],
    'a space' => ['en v'],
    'markup' => ['<env>'],
    'null' => [null],
]);
