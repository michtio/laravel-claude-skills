<?php

declare(strict_types=1);

/**
 * Builder-owned support for SetupIsolationRound2Test.php (locked). Its first case
 * reads the constant ISO_COMMENTS, which no locked file defines; the commented
 * env elements it means are ISO2_COMMENTS of the same file. This defines
 * ISO_COMMENTS with the same values (unless a gate file defines it first) and
 * checks that the two stay equal.
 */
defined('ISO_COMMENTS') || define('ISO_COMMENTS', [
    '<!-- <env name="DB_DATABASE" value="old"/> -->',
    '<!-- <env name="APP_ENV" value="x"/> -->',
]);

it('ISO_COMMENTS holds the commented env elements of the round 2 gate', function () {
    expect(ISO_COMMENTS)->toBe(ISO2_COMMENTS);
});
