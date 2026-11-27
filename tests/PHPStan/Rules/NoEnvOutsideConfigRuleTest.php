<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Rules;

use Michtio\LaravelClaudeSkills\PHPStan\Rules\NoEnvOutsideConfigRule;
use PHPStan\Rules\Rule;
use PHPStan\Testing\RuleTestCase;

/**
 * Gate test for slice S4 (laravel-layer), requirements R5, R6, R7, acceptance
 * criteria AC7. Pitfall: laravel-pitfalls, edge-validation.
 *
 * The rule flags every call to the env() function (global or fully qualified)
 * in a file whose path has a directory segment named config. Once the
 * configuration is cached, env() outside config returns null. Method and static
 * calls that happen to be named env are not the function and are not reported.
 * Reported once per call, on the line of the call.
 *
 * @extends RuleTestCase<NoEnvOutsideConfigRule>
 */
final class NoEnvOutsideConfigRuleTest extends RuleTestCase
{
    private const MESSAGE = 'env() called outside the config directory returns null once the configuration is cached. Read it in a config file and use config() here. See laravel-pitfalls: edge-validation.';

    protected function getRule(): Rule
    {
        return new NoEnvOutsideConfigRule();
    }

    public function testReportsEnvInAnApplicationClass(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/env/app/Service.php'], [
            [self::MESSAGE, 11],
            [self::MESSAGE, 16],
            [self::MESSAGE, 21],
        ]);
    }

    public function testReportsEnvInARouteFile(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/env/routes/web.php'], [
            [self::MESSAGE, 5],
            [self::MESSAGE, 8],
        ]);
    }

    public function testDoesNotReportEnvInAConfigFile(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/env/config/app.php'], []);
    }

    public function testDoesNotReportMethodsNamedEnv(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/env/app/Good.php'], []);
    }
}
