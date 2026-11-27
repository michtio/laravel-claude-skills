<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Rules;

use Michtio\LaravelClaudeSkills\PHPStan\Rules\NoUnescapedLikeRule;
use PHPStan\Rules\Rule;
use PHPStan\Testing\RuleTestCase;

/**
 * Gate test for slice S4 (laravel-layer), requirements R5, R6, R7, acceptance
 * criteria AC7. Pitfall: laravel-pitfalls, edge-validation.
 *
 * The rule visits method calls and static calls named where, orWhere,
 * whereLike, orWhereLike, whereNotLike or orWhereNotLike. For where and orWhere
 * the call qualifies when its second argument is a string literal containing
 * "like" (any case, so "NOT LIKE" counts) and the pattern is the third
 * argument; for the *Like methods the pattern is the second argument. The call
 * is reported when the pattern is a concatenation or an interpolated string
 * that contains a non-literal part not passed through an accepted escaping
 * form. Accepted forms, per part: addcslashes(...), str_replace(...), or a call
 * to a method or static method named escapeLike. A pattern that is wholly a
 * literal, or a bare variable, is not reported (a bare variable cannot be
 * judged without data flow). Reported once per call, on the line of the call
 * statement (fixtures keep each query on one line).
 *
 * @extends RuleTestCase<NoUnescapedLikeRule>
 */
final class NoUnescapedLikeRuleTest extends RuleTestCase
{
    private const MESSAGE = '%s() builds a LIKE pattern from a value that is not escaped, so a %% or _ typed by the user acts as a wildcard. Escape it first, for example addcslashes($value, \'%%_\\\\\'). See laravel-pitfalls: edge-validation.';

    protected function getRule(): Rule
    {
        return new NoUnescapedLikeRule();
    }

    public function testReportsUnescapedPatterns(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/like/like-bad.php'], [
            [sprintf(self::MESSAGE, 'where'), 18],
            [sprintf(self::MESSAGE, 'where'), 23],
            [sprintf(self::MESSAGE, 'orWhere'), 28],
            [sprintf(self::MESSAGE, 'whereLike'), 33],
            [sprintf(self::MESSAGE, 'where'), 38],
            [sprintf(self::MESSAGE, 'where'), 43],
            [sprintf(self::MESSAGE, 'where'), 48],
        ]);
    }

    public function testDoesNotReportEscapedOrLiteralPatterns(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/like/like-good.php'], []);
    }
}
