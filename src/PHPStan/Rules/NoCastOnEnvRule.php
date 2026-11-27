<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\PHPStan\Rules;

use PhpParser\Node;
use PhpParser\Node\Expr\Cast;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Name;
use PHPStan\Analyser\Scope;
use PHPStan\Rules\IdentifierRuleError;
use PHPStan\Rules\Rule;
use PHPStan\Rules\RuleErrorBuilder;

/**
 * Reports an (int), (float) or (bool) cast applied directly to env().
 *
 * Pitfall: laravel-pitfalls, edge-validation. The cast accepts anything: an
 * unset variable becomes 0, 0.0 or false, "abc" becomes 0, and the string
 * "false" becomes true. A misconfigured deployment then runs with a silent zero
 * (a timeout of 0, a rate of 0.0) instead of failing at boot.
 *
 * What is reported: a Cast\Int_, Cast\Double or Cast\Bool_ node whose operand is
 * a call to the env() function, global or fully qualified, with or without a
 * default, in any file. Casts of other expressions and (string) casts are not
 * reported.
 *
 * Proven by tests/PHPStan/Rules/NoCastOnEnvRuleTest.php.
 *
 * @author michtio
 * @implements Rule<Cast>
 */
final class NoCastOnEnvRule implements Rule
{
    // Constants
    // =========================================================================

    /**
     * Error message; the placeholder is the cast type (int, float or bool).
     */
    public const MESSAGE = '(%s) cast applied directly to env() turns an unset or malformed variable into 0, 0.0 or false without an error. Give env() a default and read the value through a typed config accessor such as config()->integer(). See laravel-pitfalls: edge-validation.';

    /**
     * Error identifier reported with every error.
     */
    public const IDENTIFIER = 'laravelPitfalls.castOnEnv';

    // Public Methods
    // =========================================================================

    /**
     * Returns the node type this rule visits.
     *
     * @return class-string<Cast>
     * @author michtio
     */
    public function getNodeType(): string
    {
        return Cast::class;
    }

    /**
     * Reports an int, float or bool cast whose operand is env().
     *
     * @param Cast $node
     * @param Scope $scope
     * @return list<IdentifierRuleError>
     * @author michtio
     */
    public function processNode(Node $node, Scope $scope): array
    {
        $type = match (true) {
            $node instanceof Cast\Int_ => 'int',
            $node instanceof Cast\Double => 'float',
            $node instanceof Cast\Bool_ => 'bool',
            default => null,
        };

        if ($type === null || !$this->isEnvCall($node->expr)) {
            return [];
        }

        return [
            RuleErrorBuilder::message(sprintf(self::MESSAGE, $type))
                ->identifier(self::IDENTIFIER)
                ->build(),
        ];
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether the expression is a call to the env() function.
     *
     * @param Node\Expr $expr
     * @return bool
     * @author michtio
     */
    private function isEnvCall(Node\Expr $expr): bool
    {
        return $expr instanceof FuncCall
            && $expr->name instanceof Name
            && $expr->name->toLowerString() === 'env';
    }
}
