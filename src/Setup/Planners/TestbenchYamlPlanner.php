<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\JsonFile;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;
use Symfony\Component\Yaml\Exception\ParseException;
use Symfony\Component\Yaml\Yaml;

/**
 * Makes a Testbench package its own Laravel skeleton: testbench.yaml
 * `laravel: ./` and `env: {APP_DEBUG: true}`.
 *
 * Boost reads `.ai/guidelines` and boost.json and writes CLAUDE.md under
 * base_path(), which Testbench sets from `laravel:` ("@testbench" being the
 * skeleton inside vendor/). Pointed at the package root, Boost works on the
 * package's own files, the runner guideline and core override included. Boost
 * registers its commands only with debug on, hence APP_DEBUG.
 *
 * Owned: the `laravel` value and `env.APP_DEBUG`; other keys and env entries are
 * kept (an env list of KEY=value strings gets an `APP_DEBUG=true` item). A
 * `laravel` value other than absent, "@testbench" or "./" is a hand edit. The file
 * is rewritten through symfony/yaml (it comes with Boost's laravel/mcp and with
 * Testbench), so comments in it are not kept; the diff shows that before it is
 * applied.
 *
 * @author michtio
 */
final class TestbenchYamlPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the Testbench configuration.
     */
    public const PATH = 'testbench.yaml';

    // Public Methods
    // =========================================================================

    /**
     * Plan testbench.yaml for a package, nothing for an app.
     *
     * @throws SetupException When testbench.yaml is not a YAML map.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        $current = PlannedFile::read($project->root, self::PATH);

        if (! $project->isPackage()) {
            return new PlannedFile(self::PATH, $current, null, null, null);
        }

        $data = $this->parse($current);
        $owned = $this->owned($data);
        $wanted = ['laravel' => './', 'APP_DEBUG' => true];

        if ($current !== null && $owned === $wanted) {
            $desired = $current;
        } else {
            $data['laravel'] = './';
            $data['env'] = $this->withDebug($data['env'] ?? null);
            $desired = Yaml::dump($data, 4, 2, Yaml::DUMP_EMPTY_ARRAY_AS_SEQUENCE);
        }

        return new PlannedFile(
            self::PATH,
            $current,
            $desired,
            $current === null ? null : JsonFile::fingerprint($owned),
            JsonFile::fingerprint($wanted),
            unrecordedEdit: ! in_array($owned['laravel'], [null, '@testbench', './'], true),
        );
    }

    // Private Methods
    // =========================================================================

    /**
     * Parse testbench.yaml into a map (empty when absent).
     *
     * @return array<mixed>
     * @throws SetupException When the content is not a YAML map.
     * @author michtio
     */
    private function parse(?string $content): array
    {
        if ($content === null || trim($content) === '') {
            return [];
        }

        try {
            $data = Yaml::parse($content);
        } catch (ParseException $exception) {
            throw new SetupException(self::PATH.' is not valid YAML ('.$exception->getMessage().'). Fix it by hand and run the setup again; nothing was written.');
        }

        if (! is_array($data)) {
            throw new SetupException(self::PATH.' is not a YAML map. Fix it by hand and run the setup again; nothing was written.');
        }

        return $data;
    }

    /**
     * The owned values as they are now: the laravel path and env APP_DEBUG.
     *
     * @param array<mixed> $data
     * @return array{laravel: mixed, APP_DEBUG: mixed}
     * @author michtio
     */
    private function owned(array $data): array
    {
        $env = $data['env'] ?? null;
        $debug = null;

        if (is_array($env)) {
            if (array_is_list($env)) {
                foreach ($env as $item) {
                    if (is_string($item) && str_starts_with($item, 'APP_DEBUG=')) {
                        $debug = in_array(strtolower(trim(substr($item, 10), '"\'')), ['true', '1'], true) ? true : substr($item, 10);
                    }
                }
            } else {
                $debug = $env['APP_DEBUG'] ?? null;
            }
        }

        return ['laravel' => $data['laravel'] ?? null, 'APP_DEBUG' => $debug];
    }

    /**
     * The env value with APP_DEBUG on, other entries kept.
     *
     * @return array<mixed>
     * @author michtio
     */
    private function withDebug(mixed $env): array
    {
        if (! is_array($env) || $env === []) {
            return ['APP_DEBUG' => true];
        }

        if (array_is_list($env)) {
            $env = array_values(array_filter($env, static fn (mixed $item): bool => ! (is_string($item) && str_starts_with($item, 'APP_DEBUG='))));
            $env[] = 'APP_DEBUG=true';

            return $env;
        }

        $env['APP_DEBUG'] = true;

        return $env;
    }
}
