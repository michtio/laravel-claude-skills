<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

use stdClass;

/**
 * Reads and writes the JSON files the setup edits in part (.mcp.json, composer.json)
 * without disturbing the rest: objects stay objects (so `{}` survives a rewrite),
 * key order is kept, and output keeps the file's indentation with slashes and
 * Unicode unescaped, as Composer and Boost write them.
 *
 * @author michtio
 */
final class JsonFile
{
    // Public Methods
    // =========================================================================

    /**
     * Decode a JSON object into stdClass objects; empty or absent content is an empty object.
     *
     * @throws SetupException When the content is not valid JSON or not an object.
     * @author michtio
     */
    public static function decode(string $path, ?string $content): stdClass
    {
        if ($content === null || trim($content) === '') {
            return new stdClass();
        }

        $data = json_decode($content);

        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new SetupException($path.' is not valid JSON ('.json_last_error_msg().'). Fix it by hand and run the setup again; nothing was written.');
        }

        if (! $data instanceof stdClass) {
            throw new SetupException($path.' is not a JSON object. Fix it by hand and run the setup again; nothing was written.');
        }

        return $data;
    }

    /**
     * Encode an object, pretty printed in the indentation of the existing content (four spaces by default).
     *
     * @author michtio
     */
    public static function encode(stdClass $data, ?string $existing): string
    {
        $indent = self::indentation($existing);
        $json = (string) json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

        if ($indent !== '    ') {
            $json = (string) preg_replace_callback(
                '/^(?: {4})+/m',
                static fn (array $match): string => str_repeat($indent, intdiv(strlen($match[0]), 4)),
                $json,
            );
        }

        return $json."\n";
    }

    /**
     * A decoded value as plain arrays, for comparisons and fingerprints.
     *
     * @author michtio
     */
    public static function toArray(mixed $value): mixed
    {
        return json_decode((string) json_encode($value), true);
    }

    /**
     * Fingerprint of a JSON value.
     *
     * @author michtio
     */
    public static function fingerprint(mixed $value): string
    {
        return SetupState::fingerprint((string) json_encode($value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    }

    // Private Methods
    // =========================================================================

    /**
     * The indentation unit of existing JSON (its first indented line), four spaces by default.
     *
     * @author michtio
     */
    private static function indentation(?string $content): string
    {
        if ($content !== null && preg_match('/^([ \t]+)"/m', str_replace("\r\n", "\n", $content), $match) === 1) {
            return $match[1];
        }

        return '    ';
    }
}
