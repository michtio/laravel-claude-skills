<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\PHPStan\Rules;

use PhpParser\Node;
use PhpParser\Node\Expr;
use PhpParser\Node\Expr\BinaryOp\Concat;
use PhpParser\Node\Expr\CallLike;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Expr\MethodCall;
use PhpParser\Node\Expr\NullsafeMethodCall;
use PhpParser\Node\Expr\StaticCall;
use PhpParser\Node\Identifier;
use PhpParser\Node\InterpolatedStringPart;
use PhpParser\Node\Name;
use PhpParser\Node\Scalar\InterpolatedString;
use PhpParser\Node\Scalar\String_;
use PHPStan\Analyser\Scope;
use PHPStan\Rules\IdentifierRuleError;
use PHPStan\Rules\Rule;
use PHPStan\Rules\RuleErrorBuilder;

/**
 * Reports a LIKE pattern built from a value that is not escaped.
 *
 * Pitfall: laravel-pitfalls, edge-validation. Query bindings stop SQL
 * injection, but they do not escape LIKE wildcards: a `%` or `_` in the user's
 * input still matches anything. A search for "%" returns every row, and a
 * filter meant to match one prefix matches many.
 *
 * What is reported: a method or static call named where or orWhere whose second
 * argument is a string literal containing "like" (any case), with the pattern as
 * third argument; or a call named whereLike, orWhereLike, whereNotLike or
 * orWhereNotLike with the pattern as second argument. The call is reported when
 * the pattern is a concatenation or an interpolated string with a non-literal
 * part that is not wrapped in addcslashes(), str_replace() or a method or
 * static method named escapeLike. A pattern that is wholly literal, or a bare
 * variable, is not reported: a bare variable cannot be judged without data flow.
 *
 * Proven by tests/PHPStan/Rules/NoUnescapedLikeRuleTest.php.
 *
 * @author michtio
 * @implements Rule<CallLike>
 */
final class NoUnescapedLikeRule implements Rule
{
    // Constants
    // =========================================================================

    /**
     * Error message; the placeholder is the query method as written.
     */
    public const MESSAGE = '%s() builds a LIKE pattern from a value that is not escaped, so a %% or _ typed by the user acts as a wildcard. Escape it first, for example addcslashes($value, \'%%_\\\\\'). See laravel-pitfalls: edge-validation.';

    /**
     * Error identifier reported with every error.
     */
    public const IDENTIFIER = 'laravelPitfalls.unescapedLike';

    /**
     * Query methods taking an operator, mapped to the pattern's argument position.
     */
    private const OPERATOR_METHODS = ['where' => 2, 'orwhere' => 2];

    /**
     * LIKE query methods, mapped to the pattern's argument position.
     */
    private const LIKE_METHODS = ['wherelike' => 1, 'orwherelike' => 1, 'wherenotlike' => 1, 'orwherenotlike' => 1];

    /**
     * Functions accepted as escaping a LIKE value.
     */
    private const ESCAPE_FUNCTIONS = ['addcslashes', 'str_replace'];

    /**
     * Method name accepted as escaping a LIKE value.
     */
    private const ESCAPE_METHOD = 'escapelike';

    // Public Methods
    // =========================================================================

    /**
     * Returns the node type this rule visits.
     *
     * @return class-string<CallLike>
     * @author michtio
     */
    public function getNodeType(): string
    {
        return CallLike::class;
    }

    /**
     * Reports a where/orWhere LIKE or where*Like call whose pattern has an unescaped part.
     *
     * @param CallLike $node
     * @param Scope $scope
     * @return list<IdentifierRuleError>
     * @author michtio
     */
    public function processNode(Node $node, Scope $scope): array
    {
        if (!$node instanceof MethodCall && !$node instanceof StaticCall && !$node instanceof NullsafeMethodCall) {
            return [];
        }
        if (!$node->name instanceof Identifier || $node->isFirstClassCallable()) {
            return [];
        }

        $method = $node->name->toString();
        $pattern = $this->pattern($node->getArgs(), $node->name->toLowerString());
        if ($pattern === null || !$this->hasUnescapedPart($pattern)) {
            return [];
        }

        return [
            RuleErrorBuilder::message(sprintf(self::MESSAGE, $method))
                ->identifier(self::IDENTIFIER)
                ->build(),
        ];
    }

    // Private Methods
    // =========================================================================

    /**
     * Returns the pattern expression when the call is a LIKE query, or null.
     *
     * @param array<Node\Arg> $args
     * @param string $method lower-cased method name
     * @return Expr|null
     * @author michtio
     */
    private function pattern(array $args, string $method): ?Expr
    {
        if (isset(self::LIKE_METHODS[$method])) {
            return ($args[self::LIKE_METHODS[$method]] ?? null)?->value;
        }

        if (isset(self::OPERATOR_METHODS[$method])) {
            $operator = ($args[1] ?? null)?->value;
            if ($operator instanceof String_ && str_contains(strtolower($operator->value), 'like')) {
                return ($args[self::OPERATOR_METHODS[$method]] ?? null)?->value;
            }
        }

        return null;
    }

    /**
     * Whether a concatenated or interpolated pattern has a non-literal part that is not escaped.
     *
     * @param Expr $pattern
     * @return bool
     * @author michtio
     */
    private function hasUnescapedPart(Expr $pattern): bool
    {
        if (!$pattern instanceof Concat && !$pattern instanceof InterpolatedString) {
            return false;
        }

        foreach ($this->parts($pattern) as $part) {
            if ($part instanceof String_ || $part instanceof InterpolatedStringPart) {
                continue;
            }
            if (!$this->isEscaped($part)) {
                return true;
            }
        }

        return false;
    }

    /**
     * Flattens a concatenation or interpolated string into its parts.
     *
     * @param Node $node
     * @return list<Node>
     * @author michtio
     */
    private function parts(Node $node): array
    {
        if ($node instanceof Concat) {
            return array_merge($this->parts($node->left), $this->parts($node->right));
        }
        if ($node instanceof InterpolatedString) {
            $parts = [];
            foreach ($node->parts as $part) {
                $parts = array_merge($parts, $this->parts($part));
            }

            return $parts;
        }

        return [$node];
    }

    /**
     * Whether a part is wrapped in an accepted escaping form.
     *
     * @param Node $part
     * @return bool
     * @author michtio
     */
    private function isEscaped(Node $part): bool
    {
        if ($part instanceof FuncCall) {
            return $part->name instanceof Name
                && in_array($part->name->toLowerString(), self::ESCAPE_FUNCTIONS, true);
        }

        if ($part instanceof MethodCall || $part instanceof StaticCall || $part instanceof NullsafeMethodCall) {
            return $part->name instanceof Identifier && $part->name->toLowerString() === self::ESCAPE_METHOD;
        }

        return false;
    }
}
