<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\JsonFile;
use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;

/**
 * Pins the test environment in the PHPUnit file: forced `<env>` elements so the
 * suite never reaches the dev database, a real mailer, queue or cache, or a live
 * payment provider, whatever .env says.
 *
 * File: phpunit.xml if it exists, else phpunit.xml.dist if it exists, else a new
 * phpunit.xml (app) or phpunit.xml.dist (package).
 *
 * Owned: only the pinned `<env>` elements inside `<php>`. Each is written exactly
 * as `<env name="X" value="v" force="true"/>`, replacing an element of that name
 * in place (a stock unforced element is not a hand edit) or appended to `<php>`
 * (created when absent). The file is edited as text, so everything else in it,
 * formatting included, stays as it is.
 *
 * Pins: APP_ENV=testing, CACHE_STORE=array, QUEUE_CONNECTION=sync,
 * MAIL_MAILER=array, SESSION_DRIVER=array, DB_URL="" (an empty URL cannot point
 * at the dev database), DB_CONNECTION and DB_DATABASE (in-memory sqlite for a
 * package or an sqlite connection, else <slug>_test on the project's connection),
 * and every live-provider flag forced false. A forced-false live flag already in
 * the file stays owned when its key leaves .env, so a removed flag is neither
 * dropped silently nor reported as a hand edit.
 *
 * The pins that reach outside the process (DB_URL, DB_CONNECTION, DB_DATABASE,
 * MAIL_MAILER, QUEUE_CONNECTION and the live flags) also get a
 * `<server name="X" value="v"/>` twin: Laravel reads $_SERVER first, and a forced
 * `<env>` cannot beat a variable the process already carries, such as one
 * `testbench package:test` passes on from a package's .env.
 *
 * Hand edits: the fingerprint covers the owned elements present in the file. An
 * unrecorded file is edited by hand when an owned element is already forced (or,
 * for a `<server>` twin, set) to another value.
 *
 * @author michtio
 */
final class PhpunitPlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Pins that do not depend on the project, in the order they are appended.
     */
    public const STANDARD_PINS = [
        'APP_ENV' => 'testing',
        'CACHE_STORE' => 'array',
        'QUEUE_CONNECTION' => 'sync',
        'MAIL_MAILER' => 'array',
        'SESSION_DRIVER' => 'array',
        'DB_URL' => '',
    ];

    /**
     * Pins also written as `<server>` elements. Laravel reads $_SERVER before $_ENV,
     * and a forced `<env>` does not override a variable the process already has
     * (an exported shell variable, or what `testbench package:test` passes on from
     * the package's .env), so the pins that reach outside the process (database,
     * mail, queue, live providers) are set in $_SERVER too.
     */
    public const SERVER_TWINS = ['DB_URL', 'DB_CONNECTION', 'DB_DATABASE', 'MAIL_MAILER', 'QUEUE_CONNECTION'];

    // Public Methods
    // =========================================================================

    /**
     * Plan the PHPUnit file with the pins for the project.
     *
     * @throws SetupException When the existing PHPUnit file is not well-formed XML.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        $path = $this->path($project);
        $current = PlannedFile::read($project->root, $path);
        $present = $current === null ? [] : $this->presentElements($path, $current);
        $elements = $this->elements($this->pins($project, $present));

        $desired = $current === null
            ? $this->newFile($project, $elements)
            : $this->merge($current, $elements);

        // Both maps in element order, so the fingerprint never depends on the file's element order.
        $owned = [];

        foreach (array_keys($elements) as $key) {
            if (isset($present[$key])) {
                $owned[$key] = $present[$key];
            }
        }

        $wanted = [];
        $forcedElsewhere = false;

        foreach ($elements as $key => [$tag, , $value]) {
            $wanted[$key] = [$value, $tag === 'env' ? 'true' : null];
        }

        foreach ($owned as $key => [$value, $force]) {
            $forced = $elements[$key][0] === 'server' || ($force !== null && strtolower($force) === 'true');

            if ($forced && $value !== $elements[$key][2]) {
                $forcedElsewhere = true;
            }
        }

        return new PlannedFile(
            $path,
            $current,
            $desired,
            $current === null ? null : JsonFile::fingerprint($owned),
            JsonFile::fingerprint($wanted),
            unrecordedEdit: $forcedElsewhere,
        );
    }

    /**
     * The PHPUnit file the setup edits, relative to the root.
     *
     * @author michtio
     */
    public function path(Project $project): string
    {
        foreach (['phpunit.xml', 'phpunit.xml.dist'] as $candidate) {
            if (is_file($project->root.'/'.$candidate)) {
                return $candidate;
            }
        }

        return $project->isPackage() ? 'phpunit.xml.dist' : 'phpunit.xml';
    }

    /**
     * The pins for the project, name => value, in append order.
     *
     * @param array<string, array{0: string, 1: string|null}> $present Elements in the file now, "env:NAME" or "server:NAME" => [value, force].
     * @return array<string, string>
     * @author michtio
     */
    public function pins(Project $project, array $present = []): array
    {
        $pins = self::STANDARD_PINS;

        if ($project->usesMemoryDatabase()) {
            $pins['DB_CONNECTION'] = 'sqlite';
            $pins['DB_DATABASE'] = ':memory:';
        } else {
            $pins['DB_CONNECTION'] = $project->dbConnection();
            $pins['DB_DATABASE'] = $project->testDatabase();
        }

        $flags = $project->liveFlags();

        foreach ($present as $key => [$value, $force]) {
            $name = substr($key, 4);

            if (str_starts_with($key, 'env:') && self::isLiveFlag($name) && $value === 'false' && $force !== null && strtolower($force) === 'true') {
                $flags[] = $name;
            }
        }

        $flags = array_unique($flags);
        sort($flags);

        foreach ($flags as $flag) {
            $pins[$flag] = 'false';
        }

        return $pins;
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether a key is a live-provider flag.
     *
     * @author michtio
     */
    private static function isLiveFlag(string $name): bool
    {
        return preg_match('/^[A-Z][A-Z0-9_]*_LIVE(_MODE)?$/', $name) === 1;
    }

    /**
     * The `<env>` and `<server>` elements inside `<php>`, "tag:NAME" => [value, force]; the first of a name wins.
     *
     * @return array<string, array{0: string, 1: string|null}>
     * @throws SetupException When the content is not well-formed XML.
     * @author michtio
     */
    private function presentElements(string $path, string $content): array
    {
        $previous = libxml_use_internal_errors(true);
        $document = simplexml_load_string($content);
        $errors = libxml_get_errors();
        libxml_clear_errors();
        libxml_use_internal_errors($previous);

        if ($document === false) {
            $message = $errors === [] ? 'not well-formed' : trim($errors[0]->message);

            throw new SetupException($path.' is not valid XML ('.$message.'). Fix it by hand and run the setup again; nothing was written.');
        }

        $present = [];

        foreach (['env', 'server'] as $tag) {
            foreach ($document->php->{$tag} ?? [] as $element) {
                $key = $tag.':'.(string) $element['name'];

                if ($key !== $tag.':' && ! isset($present[$key])) {
                    $present[$key] = [(string) $element['value'], isset($element['force']) ? (string) $element['force'] : null];
                }
            }
        }

        return $present;
    }

    /**
     * The owned elements for the pins: a forced `<env>` for each, and a `<server>`
     * twin for those in SERVER_TWINS and the live flags.
     *
     * @param array<string, string> $pins
     * @return array<string, array{0: string, 1: string, 2: string}> "tag:NAME" => [tag, name, value], in write order.
     * @author michtio
     */
    private function elements(array $pins): array
    {
        $elements = [];

        foreach ($pins as $name => $value) {
            $elements['env:'.$name] = ['env', $name, $value];
        }

        foreach ($pins as $name => $value) {
            if (in_array($name, self::SERVER_TWINS, true) || self::isLiveFlag($name)) {
                $elements['server:'.$name] = ['server', $name, $value];
            }
        }

        return $elements;
    }

    /**
     * One owned element, as it is written.
     *
     * @author michtio
     */
    private function element(string $tag, string $name, string $value): string
    {
        $value = htmlspecialchars($value, ENT_XML1 | ENT_QUOTES);

        return $tag === 'env'
            ? sprintf('<env name="%s" value="%s" force="true"/>', $name, $value)
            : sprintf('<server name="%s" value="%s"/>', $name, $value);
    }

    /**
     * A complete PHPUnit configuration for a project without one.
     *
     * @param array<string, array{0: string, 1: string, 2: string}> $elements
     * @author michtio
     */
    private function newFile(Project $project, array $elements): string
    {
        $suites = $project->isPackage()
            ? ['Test' => 'tests']
            : ['Unit' => 'tests/Unit', 'Feature' => 'tests/Feature'];
        $lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<phpunit xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:noNamespaceSchemaLocation="vendor/phpunit/phpunit/phpunit.xsd"',
            '         bootstrap="vendor/autoload.php"',
            '         colors="true"',
            '>',
            '    <testsuites>',
        ];

        foreach ($suites as $name => $directory) {
            $lines[] = '        <testsuite name="'.$name.'">';
            $lines[] = '            <directory>'.$directory.'</directory>';
            $lines[] = '        </testsuite>';
        }

        $lines[] = '    </testsuites>';
        $lines[] = '    <source>';
        $lines[] = '        <include>';
        $lines[] = '            <directory>'.($project->isPackage() ? 'src' : 'app').'</directory>';
        $lines[] = '        </include>';
        $lines[] = '    </source>';
        $lines[] = '    <php>';

        foreach ($elements as [$tag, $name, $value]) {
            $lines[] = '        '.$this->element($tag, $name, $value);
        }

        $lines[] = '    </php>';
        $lines[] = '</phpunit>';

        return implode("\n", $lines)."\n";
    }

    /**
     * Merge the pins into existing content as text: replace each owned element in
     * place, drop later duplicates of it, append the missing ones to `<php>`.
     *
     * @param array<string, array{0: string, 1: string, 2: string}> $elements
     * @author michtio
     */
    private function merge(string $content, array $elements): string
    {
        $eol = str_contains($content, "\r\n") ? "\r\n" : "\n";

        if (preg_match('/<php\s*\/>/', $content) === 1) {
            $content = (string) preg_replace('/<php\s*\/>/', '<php>'.$eol.'</php>', $content, 1);
        }

        if (preg_match('/<php\b[^>]*>/', $content, $open, PREG_OFFSET_CAPTURE) !== 1) {
            $indent = preg_match('/^([ \t]+)</m', $content, $child) === 1 ? $child[1] : '    ';
            $block = $indent.'<php>'.$eol.$indent.'</php>'.$eol;
            $close = strrpos($content, '</phpunit>');

            if ($close === false) {
                return $content;
            }

            $lineStart = $this->lineStart($content, $close);
            $content = substr($content, 0, $lineStart).$block.substr($content, $lineStart);

            if (preg_match('/<php\b[^>]*>/', $content, $open, PREG_OFFSET_CAPTURE) !== 1) {
                return $content;
            }
        }

        $start = (int) $open[0][1] + strlen($open[0][0]);
        $end = strpos($content, '</php>', $start);

        if ($end === false) {
            return $content;
        }

        $body = substr($content, $start, $end - $start);
        $phpIndent = $this->indentOf($content, (int) $open[0][1]);
        $indent = preg_match('/^([ \t]*)<env\b/m', $body, $match) === 1 ? $match[1] : $phpIndent.'    ';
        $missing = [];

        foreach ($elements as [$tag, $name, $value]) {
            $pattern = '/<'.$tag.'\b(?=[^>]*\bname=(["\'])'.preg_quote($name, '/').'\1)[^>]*?(?:\/>|>\s*<\/'.$tag.'>)/';
            $count = 0;
            $body = (string) preg_replace_callback(
                $pattern,
                function () use (&$count, $tag, $name, $value): string {
                    $count++;

                    return $count === 1 ? $this->element($tag, $name, $value) : '___LCS_DROP___';
                },
                $body,
            );
            $body = (string) preg_replace('/\R?[ \t]*___LCS_DROP___/', '', $body);

            if ($count === 0) {
                $missing[] = $indent.$this->element($tag, $name, $value);
            }
        }

        if ($missing !== []) {
            $trimmed = rtrim($body, " \t");
            $body = ($trimmed === '' || str_ends_with($trimmed, "\n") ? $trimmed : $trimmed.$eol)
                .implode($eol, $missing).$eol.$phpIndent;
        }

        return substr($content, 0, $start).$body.substr($content, $end);
    }

    /**
     * Offset of the start of the line that holds the given offset.
     *
     * @author michtio
     */
    private function lineStart(string $content, int $offset): int
    {
        $newline = strrpos(substr($content, 0, $offset), "\n");

        return $newline === false ? 0 : $newline + 1;
    }

    /**
     * The leading whitespace of the line that holds the given offset.
     *
     * @author michtio
     */
    private function indentOf(string $content, int $offset): string
    {
        $start = $this->lineStart($content, $offset);

        return preg_match('/^[ \t]*/', substr($content, $start, $offset - $start), $match) === 1 ? $match[0] : '';
    }
}
