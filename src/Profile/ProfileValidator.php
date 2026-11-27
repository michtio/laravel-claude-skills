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
 * with string `name` and `command`. The schema leaves `laravel` and `verdicts` as
 * open objects, so their entries are checked here: the five Laravel options and
 * the fields of each verdict.
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
     * The keys under `laravel` that are not one of the five options, in file order.
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
            static fn (string $key): bool => ! array_key_exists($key, self::LARAVEL_DEFAULTS),
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
     * Why a step name or command is refused for the control characters it holds, or
     * null when it holds none. Refused: C0 controls (U+0000 to U+001F, ESC
     * included), U+007F and C1 controls (U+0080 to U+009F), which could rewrite the
     * plan on a terminal (a carriage return or a cursor escape can hide a command
     * behind a harmless line). A command may hold tabs and newlines (a multi-line
     * command is shown as one block); a name may not. The reason never repeats the
     * characters it refuses.
     *
     * @author michtio
     */
    public static function controlCharacters(string $value, bool $command): ?string
    {
        $pattern = $command ? '/[\x{00}-\x{08}\x{0B}-\x{1F}\x{7F}-\x{9F}]/u' : '/[\x{00}-\x{1F}\x{7F}-\x{9F}]/u';
        $found = preg_match($pattern, $value);

        if ($found === 0) {
            return null;
        }

        if ($found === false) {
            return 'must be valid UTF-8 text';
        }

        return $command
            ? 'must not hold control characters (a carriage return, an escape sequence, NUL and the like); only tabs and newlines are allowed'
            : 'must not hold control characters (a newline, a tab, a carriage return, an escape sequence and the like)';
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
     * Check the five Laravel options; other keys are left alone.
     *
     * @throws ProfileException On the first invalid option.
     * @author michtio
     */
    private static function laravel(mixed $laravel): void
    {
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
    }

    /**
     * Whether a value is a real calendar date written as YYYY-MM-DD.
     *
     * @author michtio
     */
    private static function isDate(mixed $value): bool
    {
        if (! is_string($value) || preg_match('/^(\d{4})-(\d{2})-(\d{2})$/', $value, $m) !== 1) {
            return false;
        }

        return checkdate((int) $m[2], (int) $m[3], (int) $m[1]);
    }
}
