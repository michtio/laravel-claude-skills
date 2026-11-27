<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Profile;

use JsonException;
use stdClass;

/**
 * The project profile, `.ai/skills-profile.json`: optional, committed, written by
 * people or by a team tool, and only ever read here.
 *
 * It uses the schema shared with the Craft pack (`schema/skills-profile.schema.json`).
 * The setup reads `setup.steps`, `verdicts` and the Laravel options under `laravel`;
 * `gate_tests` and `builders` are read by the agents and only validated here.
 * Unknown keys are kept and ignored. With no file, every option has its documented
 * default (ProfileValidator::LARAVEL_DEFAULTS); profile values win over defaults.
 *
 * @author michtio
 */
final class Profile
{
    // Constants
    // =========================================================================

    /**
     * Path of the profile, relative to the project root.
     */
    public const PATH = '.ai/skills-profile.json';

    // Public Methods
    // =========================================================================

    /**
     * Hold a validated profile.
     *
     * @param bool $exists Whether the file exists.
     * @param array<string, mixed> $laravel The six options, profile values over defaults.
     * @param list<array{name: string, command: string}> $steps The extra setup steps, in order.
     * @param array<string, array<string, mixed>> $verdicts The profile's own verdicts, as written.
     * @param list<string> $unknownLaravelKeys Keys under `laravel` that are not options.
     * @author michtio
     */
    private function __construct(
        private readonly bool $exists,
        private readonly array $laravel,
        private readonly array $steps,
        private readonly array $verdicts,
        private readonly array $unknownLaravelKeys,
    ) {
    }

    /**
     * Load and validate the profile of the project at the given root.
     *
     * @throws ProfileException When the file exists but is not a valid profile.
     * @author michtio
     */
    public static function load(string $root): self
    {
        $file = rtrim($root, '/\\').'/'.self::PATH;

        if (! file_exists($file) && ! is_link($file)) {
            return new self(false, ProfileValidator::LARAVEL_DEFAULTS, [], [], []);
        }

        $content = is_file($file) && is_readable($file) ? file_get_contents($file) : false;

        if ($content === false) {
            throw ProfileException::field(self::PATH, 'the file cannot be read');
        }

        if (trim($content) === '') {
            throw ProfileException::field(self::PATH, 'the file is empty; it must hold a JSON object');
        }

        try {
            $decoded = json_decode($content, false, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $exception) {
            throw ProfileException::field(self::PATH, 'not valid JSON ('.$exception->getMessage().')');
        }

        ProfileValidator::validate($decoded);
        /** @var stdClass $decoded */

        return new self(
            true,
            self::options($decoded),
            self::readSteps($decoded),
            self::readVerdicts($decoded),
            ProfileValidator::unknownLaravelKeys($decoded),
        );
    }

    /**
     * Whether the project has a profile file.
     *
     * @author michtio
     */
    public function exists(): bool
    {
        return $this->exists;
    }

    /**
     * The Laravel options: runner, house_style, phpstan_level, env_schema,
     * monitoring, ci; profile values merged over the defaults, in that order.
     *
     * @return array<string, mixed>
     * @author michtio
     */
    public function laravel(): array
    {
        return $this->laravel;
    }

    /**
     * The extra setup steps, in profile order.
     *
     * @return list<array{name: string, command: string}>
     * @author michtio
     */
    public function steps(): array
    {
        return $this->steps;
    }

    /**
     * The profile's own verdicts, as written; empty when it has none.
     *
     * @return array<string, array<string, mixed>>
     * @author michtio
     */
    public function verdicts(): array
    {
        return $this->verdicts;
    }

    /**
     * Keys under `laravel` that are not options (kept and ignored).
     *
     * @return list<string>
     * @author michtio
     */
    public function unknownLaravelKeys(): array
    {
        return $this->unknownLaravelKeys;
    }

    // Private Methods
    // =========================================================================

    /**
     * The options: defaults, with each option the profile sets in its place.
     *
     * @return array<string, mixed>
     * @author michtio
     */
    private static function options(stdClass $profile): array
    {
        $options = ProfileValidator::LARAVEL_DEFAULTS;

        if (! property_exists($profile, 'laravel') || ! $profile->laravel instanceof stdClass) {
            return $options;
        }

        foreach (array_keys($options) as $key) {
            if (property_exists($profile->laravel, $key)) {
                $value = $profile->laravel->{$key};
                $options[$key] = $key === 'phpstan_level' ? ProfileValidator::integer($value) : $value;
            }
        }

        return $options;
    }

    /**
     * The extra steps as name/command pairs.
     *
     * @return list<array{name: string, command: string}>
     * @author michtio
     */
    private static function readSteps(stdClass $profile): array
    {
        $steps = [];

        if (property_exists($profile, 'setup') && $profile->setup instanceof stdClass && is_array($profile->setup->steps ?? null)) {
            foreach ($profile->setup->steps as $step) {
                $steps[] = ['name' => (string) $step->name, 'command' => (string) $step->command];
            }
        }

        return $steps;
    }

    /**
     * The verdicts as arrays.
     *
     * @return array<string, array<string, mixed>>
     * @author michtio
     */
    private static function readVerdicts(stdClass $profile): array
    {
        if (! property_exists($profile, 'verdicts') || ! $profile->verdicts instanceof stdClass) {
            return [];
        }

        $verdicts = [];

        foreach (get_object_vars($profile->verdicts) as $package => $verdict) {
            $verdicts[(string) $package] = (array) json_decode((string) json_encode($verdict), true);
        }

        return $verdicts;
    }
}
