<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\PHPStan\Rules;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;
use PhpParser\Node;
use PhpParser\Node\Expr;
use PhpParser\Node\Expr\Array_;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Expr\MethodCall;
use PhpParser\Node\Expr\NullsafeMethodCall;
use PhpParser\Node\Expr\StaticCall;
use PhpParser\Node\Identifier;
use PhpParser\Node\Name;
use PHPStan\Analyser\Scope;
use PHPStan\Rules\IdentifierRuleError;
use PHPStan\Rules\Rule;
use PHPStan\Rules\RuleErrorBuilder;
use PHPStan\Type\ObjectType;

/**
 * Reports a Log call that writes a model, the request payload or the whole request.
 *
 * Pitfall: laravel-pitfalls, pii-logs. A model serializes every attribute that
 * is not hidden, and the request payload carries whatever the client sent
 * (names, addresses, tokens, passwords on a login form). Written to the log,
 * that data is copied to every log store and kept for as long as the logs are,
 * outside the retention and erasure rules that govern the database.
 *
 * What is reported: a static call to a level method (emergency, alert,
 * critical, error, warning, notice, info, debug) on the Log facade (resolved
 * to Illuminate\Support\Facades\Log or the global alias Log) when the message
 * or the context argument is, or the context array directly holds as a value:
 * an Eloquent model ("a model instance"); all() or input() called with no
 * arguments on a Request or on request() ("the request payload"); or a Request
 * itself ("the whole request"). Once per offending argument.
 *
 * Proven by tests/PHPStan/Rules/NoPayloadInLogRuleTest.php.
 *
 * @author michtio
 * @implements Rule<StaticCall>
 */
final class NoPayloadInLogRule implements Rule
{
    // Constants
    // =========================================================================

    /**
     * Error message; the placeholders are the level method and what was logged.
     */
    public const MESSAGE = 'Log::%s() receives %s, which writes personal data to the log files and keeps it for as long as they are retained. Log ids and scalar fields instead. See laravel-pitfalls: pii-logs.';

    /**
     * Error identifier reported with every error.
     */
    public const IDENTIFIER = 'laravelPitfalls.payloadInLog';

    /**
     * Class names that resolve to the Log facade.
     */
    private const LOG_FACADES = ['Illuminate\\Support\\Facades\\Log', 'Log'];

    /**
     * PSR-3 level methods on the Log facade.
     */
    private const LEVELS = ['emergency', 'alert', 'critical', 'error', 'warning', 'notice', 'info', 'debug'];

    // Public Methods
    // =========================================================================

    /**
     * Returns the node type this rule visits.
     *
     * @return class-string<StaticCall>
     * @author michtio
     */
    public function getNodeType(): string
    {
        return StaticCall::class;
    }

    /**
     * Reports each message or context argument that carries a payload.
     *
     * @param StaticCall $node
     * @param Scope $scope
     * @return list<IdentifierRuleError>
     * @author michtio
     */
    public function processNode(Node $node, Scope $scope): array
    {
        if (!$node->class instanceof Name
            || !in_array(ltrim($node->class->toString(), '\\'), self::LOG_FACADES, true)
            || !$node->name instanceof Identifier
            || !in_array($node->name->toLowerString(), self::LEVELS, true)
            || $node->isFirstClassCallable()
        ) {
            return [];
        }

        $errors = [];
        foreach (array_slice($node->getArgs(), 0, 2) as $arg) {
            $what = $this->describe($arg->value, $scope);
            if ($what === null && $arg->value instanceof Array_) {
                foreach ($arg->value->items as $item) {
                    $what = $this->describe($item->value, $scope);
                    if ($what !== null) {
                        break;
                    }
                }
            }
            if ($what !== null) {
                $errors[] = RuleErrorBuilder::message(sprintf(self::MESSAGE, $node->name->toString(), $what))
                    ->identifier(self::IDENTIFIER)
                    ->build();
            }
        }

        return $errors;
    }

    // Private Methods
    // =========================================================================

    /**
     * Describes what the expression puts in the log, or returns null when it is harmless.
     *
     * @param Expr $expr
     * @param Scope $scope
     * @return string|null
     * @author michtio
     */
    private function describe(Expr $expr, Scope $scope): ?string
    {
        if (($expr instanceof MethodCall || $expr instanceof NullsafeMethodCall)
            && $expr->name instanceof Identifier
            && in_array($expr->name->toLowerString(), ['all', 'input'], true)
            && $expr->getArgs() === []
            && !$expr->isFirstClassCallable()
            && $this->isRequest($expr->var, $scope)
        ) {
            return 'the request payload';
        }

        if ((new ObjectType(Model::class))->isSuperTypeOf($scope->getType($expr))->yes()) {
            return 'a model instance';
        }

        if ($this->isRequest($expr, $scope)) {
            return 'the whole request';
        }

        return null;
    }

    /**
     * Whether the expression is a Request, by type or as a bare request() call.
     *
     * @param Expr $expr
     * @param Scope $scope
     * @return bool
     * @author michtio
     */
    private function isRequest(Expr $expr, Scope $scope): bool
    {
        if ($expr instanceof FuncCall
            && $expr->name instanceof Name
            && $expr->name->toLowerString() === 'request'
            && $expr->getArgs() === []
            && !$expr->isFirstClassCallable()
        ) {
            return true;
        }

        return (new ObjectType(Request::class))->isSuperTypeOf($scope->getType($expr))->yes();
    }
}
