<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Rules;

use Michtio\LaravelClaudeSkills\PHPStan\Rules\NoSideEffectInTransactionRule;
use PHPStan\Rules\Rule;
use PHPStan\Testing\RuleTestCase;

/**
 * Gate test for slice S3 (laravel-layer), requirements R5, R6, R7, acceptance
 * criteria AC6 and AC8. Pitfall: laravel-pitfalls, transactions.
 *
 * The rule flags an outbound HTTP call (Http facade) or mail call (Mail facade)
 * written lexically inside the closure or arrow function handed to
 * DB::transaction(). Reported once per static facade call, on the line of that
 * call. Calls inside a DB::afterCommit() closure nested in the transaction are
 * the fix and are not reported. The beginTransaction() ... commit() form is out
 * of scope for v1: it needs statement-order flow analysis across branches and
 * early exits, and a lexical approximation would report false positives.
 *
 * @extends RuleTestCase<NoSideEffectInTransactionRule>
 */
final class NoSideEffectInTransactionRuleTest extends RuleTestCase
{
    private const MESSAGE = '%s::%s() inside a database transaction cannot be rolled back and fires even when the transaction fails. Move it after the commit or wrap it in DB::afterCommit(). See laravel-pitfalls: transactions.';

    protected function getRule(): Rule
    {
        return new NoSideEffectInTransactionRule();
    }

    public function testReportsSideEffectsInsideTheTransaction(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/transaction-side-effects-bad.php'], [
            [sprintf(self::MESSAGE, 'Http', 'post'), 17],
            [sprintf(self::MESSAGE, 'Mail', 'to'), 25],
            [sprintf(self::MESSAGE, 'Http', 'post'), 31],
            [sprintf(self::MESSAGE, 'Http', 'get'), 38],
        ]);
    }

    public function testDoesNotReportTheFixedForms(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/transaction-side-effects-good.php'], []);
    }
}
