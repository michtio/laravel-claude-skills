<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Tests\PHPStan\Rules;

use Michtio\LaravelClaudeSkills\PHPStan\Rules\NoPayloadInLogRule;
use PHPStan\Rules\Rule;
use PHPStan\Testing\RuleTestCase;

/**
 * Gate test for slice S4 (laravel-layer), requirements R5, R6, R7, acceptance
 * criteria AC7. Pitfall: laravel-pitfalls, pii-logs.
 *
 * The rule flags a static call to a level method (emergency, alert, critical,
 * error, warning, notice, info, debug) on the Log facade (resolved to
 * Illuminate\Support\Facades\Log or the global alias Log) when the message or
 * the context argument is, or the context array directly contains as a value:
 * an Illuminate\Database\Eloquent\Model subtype (reported "a model instance");
 * a call to all() or input() with no arguments on an Illuminate\Http\Request
 * (including request()) (reported "the request payload"); or a Request itself
 * (reported "the whole request"). Anything else, such as ids, scalar fields,
 * input('key') with an argument and other facades, is not reported.
 * Reported once per offending argument, on the line of the Log call.
 *
 * @extends RuleTestCase<NoPayloadInLogRule>
 */
final class NoPayloadInLogRuleTest extends RuleTestCase
{
    private const MESSAGE = 'Log::%s() receives %s, which writes personal data to the log files and keeps it for as long as they are retained. Log ids and scalar fields instead. See laravel-pitfalls: pii-logs.';

    protected function getRule(): Rule
    {
        return new NoPayloadInLogRule();
    }

    public function testReportsPayloadsInLogs(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/log/log-bad.php'], [
            [sprintf(self::MESSAGE, 'info', 'a model instance'), 19],
            [sprintf(self::MESSAGE, 'warning', 'a model instance'), 24],
            [sprintf(self::MESSAGE, 'info', 'the request payload'), 29],
            [sprintf(self::MESSAGE, 'debug', 'the request payload'), 34],
            [sprintf(self::MESSAGE, 'error', 'the request payload'), 39],
            [sprintf(self::MESSAGE, 'critical', 'the whole request'), 44],
        ]);
    }

    public function testDoesNotReportIdsAndScalarFields(): void
    {
        $this->analyse([__DIR__.'/../Fixtures/log/log-good.php'], []);
    }
}
