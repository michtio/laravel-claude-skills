<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Profile;

use stdClass;

/**
 * Validates a decoded `.ai/skills-profile.json` (JSON objects as stdClass, so an
 * empty object and an empty list stay apart).
 *
 * Shared keys follow the rules of `schema/skills-profile.schema.json` (the file
 * the Craft pack ships, byte for byte): `version` is the integer 1; `managed_by`,
 * `setup`, `craft` and its `answers` and `choices` are objects; `gate_tests` is
 * `locked` or `builder-written`; `builders` and `setup.steps` are lists of objects
 * with string `name` and `command`, and a builder `name` matches BUILDER_NAME in full. The schema leaves `laravel` and `verdicts` as
 * open objects, so their entries are checked here: the Laravel options (the five
 * of LARAVEL_DEFAULTS and the four of OPTIONAL_DEFAULTS) and the fields of each
 * verdict.
 *
 * Unknown keys are allowed at every level (the schema's "unknown keys are kept and
 * ignored"); unknownLaravelKeys() lists the ones under `laravel` so the setup can
 * say it ignores them. The first offending field, in document order of the checks,
 * is reported as a ProfileException with its dotted path.
 *
 * @author michtio
 */
final class ProfileValidator
{
    // Constants
    // =========================================================================

    /**
     * A builder name, matched in full (`\z`, so a trailing newline is refused): the
     * schema's `^[A-Za-z0-9._-]{1,64}$`. A gated build passes the name on a shell line,
     * so nothing else gets through (tests/Profile/BuilderNameValidationTest.php).
     */
    public const BUILDER_NAME = '/^[A-Za-z0-9._-]{1,64}\z/';

    /**
     * The Laravel options and their defaults, in the order they are stated.
     */
    public const LARAVEL_DEFAULTS = [
        'runner' => 'auto',
        'house_style' => true,
        'phpstan_level' => 8,
        'monitoring' => 'none',
        'ci' => false,
    ];

    /**
     * The Laravel options that are listed by Profile::laravel() only when the profile
     * sets them, with their defaults, in that order: `test_database` (auto or ddev),
     * `php_matrix` (auto or a list of X.Y versions), `test_pins` (name => value
     * or `env`; empty means no override) and `ci_services` (extra service containers
     * for the CI workflow's gate job; empty means none).
     */
    public const OPTIONAL_DEFAULTS = [
        'test_database' => 'auto',
        'php_matrix' => 'auto',
        'test_pins' => [],
        'ci_services' => [],
    ];

    /**
     * The services `laravel.ci_services` may name: the ones the CI workflow has an
     * image for. Refusing any other
     * name is proven by tests/Profile/CiServicesValidationTest.php.
     */
    public const CI_SERVICES = ['redis'];

    /**
     * Allowed values of `laravel.test_database`.
     */
    public const TEST_DATABASES = ['auto', 'ddev'];

    /**
     * The PHPUnit pins `laravel.test_pins` may name. The database, `APP_ENV` and
     * live-flag pins decide what the suite reaches, so they cannot be named.
     */
    public const PIN_NAMES = ['SESSION_DRIVER', 'CACHE_STORE', 'QUEUE_CONNECTION', 'MAIL_MAILER'];

    /**
     * The value of a `laravel.test_pins` entry that leaves the pin unforced, so the
     * shell's value wins and the standard value is only the default.
     */
    public const PIN_FROM_ENV = 'env';

    /**
     * Allowed values of `laravel.runner`.
     */
    public const RUNNERS = ['auto', 'ddev', 'host'];

    /**
     * Allowed values of `laravel.monitoring`.
     */
    public const MONITORING = ['none', 'sentry', 'nightwatch'];

    /**
     * Allowed values of `gate_tests`.
     */
    public const GATE_TESTS = ['locked', 'builder-written'];

    /**
     * Allowed values of a verdict's `use`.
     */
    public const USES = ['use', 'avoid', 'depends'];

    // Public Methods
    // =========================================================================

    /**
     * Check the whole profile.
     *
     * @throws ProfileException On the first invalid field.
     * @author michtio
     */
    public static function validate(mixed $profile): void
    {
        if (! $profile instanceof stdClass) {
            throw ProfileException::field(Profile::PATH, 'the file must hold a JSON object');
        }

        if (! property_exists($profile, 'version')) {
            throw ProfileException::field('version', 'is required and must be the integer 1');
        }

        if (self::integer($profile->version) !== 1) {
            throw ProfileException::field('version', 'must be the integer 1');
        }

        if (property_exists($profile, 'managed_by')) {
            self::object($profile->managed_by, 'managed_by');

            foreach (['tool', 'version'] as $key) {
                if (property_exists($profile->managed_by, $key) && ! is_string($profile->managed_by->{$key})) {
                    throw ProfileException::field('managed_by.'.$key, 'must be a string');
                }
            }
        }

        if (property_exists($profile, 'gate_tests') && ! in_array($profile->gate_tests, self::GATE_TESTS, true)) {
            throw ProfileException::field('gate_tests', 'must be one of '.implode(', ', self::GATE_TESTS));
        }

        if (property_exists($profile, 'builders')) {
            self::namedCommands($profile->builders, 'builders', true);
        }

        if (property_exists($profile, 'setup')) {
            self::object($profile->setup, 'setup');

            if (property_exists($profile->setup, 'steps')) {
                self::namedCommands($profile->setup->steps, 'setup.steps', false);
            }
        }

        if (property_exists($profile, 'verdicts')) {
            self::verdicts($profile->verdicts);
        }

        if (property_exists($profile, 'craft')) {
            self::craft($profile->craft);
        }

        if (property_exists($profile, 'laravel')) {
            self::laravel($profile->laravel);
        }
    }

    /**
     * The keys under `laravel` that are not one of the nine options, in file order.
     *
     * @return list<string>
     * @author michtio
     */
    public static function unknownLaravelKeys(stdClass $profile): array
    {
        if (! property_exists($profile, 'laravel') || ! $profile->laravel instanceof stdClass) {
            return [];
        }

        return array_values(array_filter(
            array_map('strval', array_keys(get_object_vars($profile->laravel))),
            static fn (string $key): bool => ! array_key_exists($key, self::LARAVEL_DEFAULTS) && ! array_key_exists($key, self::OPTIONAL_DEFAULTS),
        ));
    }

    /**
     * A JSON integer as PHP int (a number with no fractional part counts, as in the
     * schema's dialect), or null for anything else, booleans included.
     *
     * @author michtio
     */
    public static function integer(mixed $value): ?int
    {
        if (is_int($value)) {
            return $value;
        }

        if (is_float($value) && is_finite($value) && floor($value) === $value && abs($value) < PHP_INT_MAX) {
            return (int) $value;
        }

        return null;
    }

    /**
     * Why a step name or command is refused for the hidden characters it holds, or
     * null when it holds none. Refused: every Unicode control, format, surrogate,
     * private-use or unassigned character (category C*: C0 and C1 controls, ESC,
     * a right-to-left override, a zero-width space) and every line or paragraph
     * separator (Zl, Zp), as scripts/builders_check.py refuses for builder
     * commands, since they could rewrite or reorder the plan on a terminal (a
     * carriage return or a cursor escape can hide a command behind a harmless
     * line). A command may hold tabs and newlines (a multi-line command is shown
     * as one block); a name may not. The reason never repeats the characters it
     * refuses. Proved by tests/Profile/StepHiddenCharactersTest.php.
     *
     * @author michtio
     */
    public static function controlCharacters(string $value, bool $command): ?string
    {
        $pattern = $command ? '/(?![\t\n])[\p{C}\p{Zl}\p{Zp}]/u' : '/[\p{C}\p{Zl}\p{Zp}]/u';
        $found = preg_match($pattern, $value);

        if ($found === 0) {
            return null;
        }

        if ($found === false) {
            return 'must be valid UTF-8 text';
        }

        return $command
            ? 'must not hold control, format or separator characters (a carriage return, an escape sequence, a right-to-left override, a zero-width space and the like); only tabs and newlines are allowed'
            : 'must not hold control, format or separator characters (a newline, a tab, an escape sequence, a right-to-left override, a zero-width space and the like)';
    }

    // Private Methods
    // =========================================================================

    /**
     * Require a JSON object.
     *
     * @phpstan-assert stdClass $value
     * @throws ProfileException When it is not one.
     * @author michtio
     */
    private static function object(mixed $value, string $field): void
    {
        if (! $value instanceof stdClass) {
            throw ProfileException::field($field, 'must be a JSON object');
        }
    }

    /**
     * Check a list of {name, command} objects (`builders`, `setup.steps`).
     *
     * @throws ProfileException On the first invalid item.
     * @author michtio
     */
    private static function namedCommands(mixed $value, string $field, bool $timeout): void
    {
        if (! is_array($value) || ! array_is_list($value)) {
            throw ProfileException::field($field, 'must be a list');
        }

        foreach ($value as $index => $item) {
            $path = $field.'.'.$index;
            self::object($item, $path);

            foreach (['name', 'command'] as $key) {
                if (! property_exists($item, $key)) {
                    throw ProfileException::field($path.'.'.$key, 'is required and must be a string');
                }

                if (! is_string($item->{$key})) {
                    throw ProfileException::field($path.'.'.$key, 'must be a string');
                }

                // Steps are printed in the plan and run by the setup; builders are read by agents.
                $reason = $timeout ? null : self::controlCharacters($item->{$key}, $key === 'command');

                if ($reason !== null) {
                    throw ProfileException::field($path.'.'.$key, $reason);
                }
            }

            // Builders only (the flag that allows a timeout): their name reaches a shell line.
            if ($timeout && preg_match(self::BUILDER_NAME, $item->name) !== 1) {
                throw ProfileException::field($path.'.name', 'must be 1 to 64 letters, digits, dots, underscores or hyphens');
            }

            if ($timeout && property_exists($item, 'timeout_minutes')) {
                $minutes = $item->timeout_minutes;

                if ((! is_int($minutes) && ! is_float($minutes)) || $minutes <= 0) {
                    throw ProfileException::field($path.'.timeout_minutes', 'must be a number above 0');
                }
            }
        }
    }

    /**
     * Check the verdict entries: package name => {use, reason, conditions?, checked?}.
     *
     * @throws ProfileException On the first invalid field.
     * @author michtio
     */
    private static function verdicts(mixed $verdicts): void
    {
        self::object($verdicts, 'verdicts');

        foreach (get_object_vars($verdicts) as $package => $verdict) {
            $path = 'verdicts.'.$package;
            self::object($verdict, $path);

            if (! property_exists($verdict, 'use') || ! in_array($verdict->use, self::USES, true)) {
                throw ProfileException::field($path.'.use', 'must be one of '.implode(', ', self::USES));
            }

            if (! property_exists($verdict, 'reason') || ! is_string($verdict->reason) || trim($verdict->reason) === '') {
                throw ProfileException::field($path.'.reason', 'is required and must be a non-empty string');
            }

            if (property_exists($verdict, 'conditions') && ! is_string($verdict->conditions)) {
                throw ProfileException::field($path.'.conditions', 'must be a string');
            }

            if (property_exists($verdict, 'checked') && ! self::isDate($verdict->checked)) {
                throw ProfileException::field($path.'.checked', 'must be a date written as YYYY-MM-DD');
            }
        }
    }

    /**
     * Check the `craft` section by the schema's rules.
     *
     * @throws ProfileException On the first invalid field.
     * @author michtio
     */
    private static function craft(mixed $craft): void
    {
        self::object($craft, 'craft');

        $sections = [
            'answers' => ['hosting' => 'string', 'passwordless' => 'boolean', 'dev_root' => 'string'],
            'choices' => ['chrome_devtools_mcp' => 'boolean', 'craft_mcp' => 'boolean'],
        ];

        foreach ($sections as $section => $keys) {
            if (! property_exists($craft, $section)) {
                continue;
            }

            self::object($craft->{$section}, 'craft.'.$section);

            foreach ($keys as $key => $type) {
                if (! property_exists($craft->{$section}, $key)) {
                    continue;
                }

                $value = $craft->{$section}->{$key};
                $valid = $type === 'string' ? is_string($value) : is_bool($value);

                if (! $valid) {
                    throw ProfileException::field('craft.'.$section.'.'.$key, $type === 'string' ? 'must be a string' : 'must be true or false');
                }
            }
        }
    }

    /**
     * Check the Laravel options; other keys are left alone.
     *
     * @throws ProfileException On the first invalid option.
     * @author michtio
     */
    private static function laravel(mixed $laravel): void
    {
        // PHP's json_encode writes an empty map as [], so a tool that writes the profile
        // with no Laravel options produces "laravel": []: read as no options set.
        if ($laravel === []) {
            return;
        }

        self::object($laravel, 'laravel');

        if (property_exists($laravel, 'runner') && ! in_array($laravel->runner, self::RUNNERS, true)) {
            throw ProfileException::field('laravel.runner', 'must be one of '.implode(', ', self::RUNNERS));
        }

        if (property_exists($laravel, 'house_style') && ! is_bool($laravel->house_style)) {
            throw ProfileException::field('laravel.house_style', 'must be true or false');
        }

        if (property_exists($laravel, 'phpstan_level')) {
            $level = self::integer($laravel->phpstan_level);

            if ($level === null || $level < 0 || $level > 10) {
                throw ProfileException::field('laravel.phpstan_level', 'must be an integer from 0 to 10');
            }
        }

        if (property_exists($laravel, 'monitoring') && ! in_array($laravel->monitoring, self::MONITORING, true)) {
            throw ProfileException::field('laravel.monitoring', 'must be one of '.implode(', ', self::MONITORING));
        }

        if (property_exists($laravel, 'ci') && ! is_bool($laravel->ci)) {
            throw ProfileException::field('laravel.ci', 'must be true or false');
        }

        if (property_exists($laravel, 'test_database') && ! in_array($laravel->test_database, self::TEST_DATABASES, true)) {
            throw ProfileException::field('laravel.test_database', 'must be one of '.implode(', ', self::TEST_DATABASES));
        }

        if (property_exists($laravel, 'php_matrix')) {
            self::phpMatrix($laravel->php_matrix);
        }

        if (property_exists($laravel, 'test_pins')) {
            self::testPins($laravel->test_pins);
        }

        if (property_exists($laravel, 'ci_services')) {
            self::ciServices($laravel->ci_services);
        }
    }

    /**
     * Check `laravel.ci_services`: a list of unique names from CI_SERVICES (an empty
     * list means none). Proven by tests/Profile/CiServicesValidationTest.php.
     *
     * @throws ProfileException On the first invalid value.
     * @author michtio
     */
    private static function ciServices(mixed $services): void
    {
        if (! is_array($services) || ! array_is_list($services)) {
            throw ProfileException::field('laravel.ci_services', 'must be a list of service names: '.implode(', ', self::CI_SERVICES));
        }

        $seen = [];

        foreach ($services as $index => $service) {
            if (! is_string($service) || ! in_array($service, self::CI_SERVICES, true)) {
                throw ProfileException::field('laravel.ci_services.'.$index, 'must be one of '.implode(', ', self::CI_SERVICES));
            }

            if (in_array($service, $seen, true)) {
                throw ProfileException::field('laravel.ci_services.'.$index, 'lists '.$service.' twice');
            }

            $seen[] = $service;
        }
    }

    /**
     * Check `laravel.php_matrix`: `auto`, or a non-empty list of unique X.Y strings.
     *
     * @throws ProfileException On the first invalid value.
     * @author michtio
     */
    private static function phpMatrix(mixed $matrix): void
    {
        if ($matrix === 'auto') {
            return;
        }

        if (! is_array($matrix) || ! array_is_list($matrix) || $matrix === []) {
            throw ProfileException::field('laravel.php_matrix', 'must be auto or a non-empty list of PHP versions written as "X.Y" strings');
        }

        $seen = [];

        foreach ($matrix as $index => $version) {
            if (! is_string($version) || preg_match('/^\d+\.\d+$/D', $version) !== 1) {
                throw ProfileException::field('laravel.php_matrix.'.$index, 'must be a PHP version written as an "X.Y" string, such as "8.4"');
            }

            if (in_array($version, $seen, true)) {
                throw ProfileException::field('laravel.php_matrix.'.$index, 'lists '.$version.' twice');
            }

            $seen[] = $version;
        }
    }

    /**
     * Check `laravel.test_pins`: an object of allowed pin names, each a plain value
     * (letters, digits, `_`, `.`, `-`) or `env`.
     *
     * @throws ProfileException On the first invalid entry.
     * @author michtio
     */
    private static function testPins(mixed $pins): void
    {
        self::object($pins, 'laravel.test_pins');

        foreach (get_object_vars($pins) as $name => $value) {
            $path = 'laravel.test_pins.'.$name;

            if (! in_array((string) $name, self::PIN_NAMES, true)) {
                throw ProfileException::field($path, 'cannot be named; only '.implode(', ', self::PIN_NAMES).' can (the database, APP_ENV and live-flag pins stay forced)');
            }

            if (! is_string($value) || preg_match('/^[A-Za-z0-9_.-]+$/D', $value) !== 1) {
                throw ProfileException::field($path, 'must be `env` or a value of letters, digits, _, . and -');
            }
        }
    }

    /**
     * Whether a value is a real calendar date written as YYYY-MM-DD.
     *
     * @author michtio
     */
    private static function isDate(mixed $value): bool
    {
        if (! is_string($value) || preg_match('/^(\d{4})-(\d{2})-(\d{2})$/D', $value, $m) !== 1) {
            return false;
        }

        return checkdate((int) $m[2], (int) $m[3], (int) $m[1]);
    }
}
