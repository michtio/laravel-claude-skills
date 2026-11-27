<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Rules;

use Michtio\LaravelClaudeSkills\PHPStan\Rules\NoCastOnEnvRule;
use PHPStan\Rules\Rule;
use PHPStan\Testing\RuleTestCase;

/**
 * Gate test for slice S4 (laravel-layer), requirements R5, R6, R7, acceptance
 * criteria AC7. Pitfall: laravel-pitfalls, edge-validation.
 *
 * The rule flags an (int), (float) or (bool) cast whose operand is a direct
 * call to env() (global or fully qualified), with or without a default, in any
 * file. Casts of other expressions, and a (string) cast, are not reported.
 * Reported once per cast, on the line of the cast.
 *
 * @extends RuleTestCase<NoCastOnEnvRule>
 */
final class NoCastOnEnvRuleTest extends RuleTestCase
{
    private const MESSAGE = '(%s) cast applied directly to env() turns an unset or malformed variable into 0, 0.0 or false without an error. Give env() a default and read the value through a typed config accessor such as config()->integer(). See laravel-pitfalls: edge-validation.';

    protected function getRule(): Rule
    {
        return new NoCastOnEnvRule();
    }

    public function testReportsCastsOnEnv(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/cast/config/services-bad.php'], [
            [sprintf(self::MESSAGE, 'int'), 6],
            [sprintf(self::MESSAGE, 'float'), 7],
            [sprintf(self::MESSAGE, 'bool'), 8],
            [sprintf(self::MESSAGE, 'int'), 10],
        ]);
    }

    public function testDoesNotReportTheFixedForms(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/cast/config/services-good.php'], []);
        $this->analyse([__DIR__.'/../Fixtures/cast/app/Reader.php'], []);
    }
}
