<?php

declare(strict_types=1);

/**
 * Gate tests for slice S7 (laravel-layer): the profile schema.
 * Requirements R23, R24; plan AD6 and the risk "the profile schema drifts from the Craft pack's".
 * The Python half is tests/gate/test_s7.py.
 *
 * schema/skills-profile.schema.json is byte-identical to the Craft pack's file, pinned to:
 *   repo   michtio/craftcms-claude-skills (git@github.com:michtio/craftcms-claude-skills.git)
 *   ref    main at 48f0c241db45bacb0e9d6668afaeafb6473a7143 (merge of PR #32; the file is not in
 *          the v1.31.0 tag, it arrived after it)
 *   path   schema/skills-profile.schema.json, with "pattern": "^[A-Za-z0-9._-]{1,64}$" added to
 *          builders.items.properties.name (ruled 2026-11-28, both packs)
 *   blob   4cbce501a9aad3f83f02f4435c9b0d6b9948ca0e (git hash-object)
 *   sha256 39b36ee7899fcae616cfd0c050e31325e3a6d88cc391abbdb32ccdbef8102023
 * When the Craft pack changes the schema, the builder copies the new file, and this pin
 * changes with the gate writer, in both packs' gates.
 */

const SCHEMA = __DIR__.'/../../schema/skills-profile.schema.json';
const CRAFT_SCHEMA_BLOB = '4cbce501a9aad3f83f02f4435c9b0d6b9948ca0e';
const CRAFT_SCHEMA_SHA256 = '39b36ee7899fcae616cfd0c050e31325e3a6d88cc391abbdb32ccdbef8102023';

it('ships the schema file, byte for byte the Craft pack\'s pinned file', function () {
    expect(is_file(SCHEMA))->toBeTrue();

    $bytes = (string) file_get_contents(SCHEMA);

    expect(sha1('blob '.strlen($bytes)."\0".$bytes))->toBe(CRAFT_SCHEMA_BLOB)
        ->and(hash('sha256', $bytes))->toBe(CRAFT_SCHEMA_SHA256);
});

it('keeps the schema open: no additionalProperties false at any level (unknown keys are kept and ignored)', function () {
    $schema = json_decode((string) @file_get_contents(SCHEMA), true);

    expect($schema)->toBeArray();

    $walk = function (mixed $node) use (&$walk): void {
        if (! is_array($node)) {
            return;
        }

        expect($node['additionalProperties'] ?? true)->not->toBeFalse();

        foreach ($node as $child) {
            $walk($child);
        }
    };
    $walk($schema);
});
