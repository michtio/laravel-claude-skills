<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\PHPStan\Rules;

use PhpParser\Node;
use PhpParser\Node\Expr\ArrowFunction;
use PhpParser\Node\Expr\Closure;
use PhpParser\Node\Expr\StaticCall;
use PhpParser\Node\Identifier;
use PhpParser\Node\Name;
use PhpParser\Node\Stmt\ClassLike;
use PhpParser\Node\Stmt\Function_;
use PHPStan\Analyser\Scope;
use PHPStan\Rules\IdentifierRuleError;
use PHPStan\Rules\Rule;
use PHPStan\Rules\RuleErrorBuilder;

/**
 * Reports an outbound HTTP or mail call written inside a DB::transaction() closure.
 *
 * Pitfall: laravel-pitfalls, transactions. A request sent or a mail handed over
 * inside the transaction cannot be rolled back: it fires even when the
 * transaction later fails, and it holds the row locks open while it waits on the
 * network. The fix is to make the call after the commit, or to wrap it in
 * DB::afterCommit().
 *
 * What is reported: every static call on the Http or Mail facade (resolved to
 * Illuminate\Support\Facades\Http or Mail, or the global aliases Http and Mail)
 * that sits lexically inside a closure or arrow function passed to
 * DB::transaction(), nested closures included. Calls inside a DB::afterCommit()
 * closure are the fix and are skipped. A DB::transaction() nested inside another
 * is reported by its own visit, never twice. Named functions and class bodies
 * declared inside the closure are skipped: their code does not run where it is
 * written. The beginTransaction() ... commit() form is out of scope.
 *
 * Proven by tests/PHPStan/Rules/NoSideEffectInTransactionRuleTest.php.
 *
 * @author michtio
 * @implements Rule<StaticCall>
 */
final class NoSideEffectInTransactionRule implements Rule
{
    // Constants
    // =========================================================================

    /**
     * Error message; the placeholders are the facade short name and the method.
     */
    public const MESSAGE = '%s::%s() inside a database transaction cannot be rolled back and fires even when the transaction fails. Move it after the commit or wrap it in DB::afterCommit(). See laravel-pitfalls: transactions.';

    /**
     * Error identifier reported with every error.
     */
    public const IDENTIFIER = 'laravelPitfalls.sideEffectInTransaction';

    /**
     * Class names that resolve to the DB facade.
     */
    private const DB_FACADES = ['Illuminate\\Support\\Facades\\DB', 'DB'];

    /**
     * Class names that resolve to a side-effect facade, mapped to the short name
     * used in the message.
     */
    private const SIDE_EFFECT_FACADES = [
        'Illuminate\\Support\\Facades\\Http' => 'Http',
        'Http' => 'Http',
        'Illuminate\\Support\\Facades\\Mail' => 'Mail',
        'Mail' => 'Mail',
    ];

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
     * Reports every side-effect facade call inside the closures of a DB::transaction() call.
     *
     * @param StaticCall $node
     * @param Scope $scope
     * @return list<IdentifierRuleError>
     * @author michtio
     */
    public function processNode(Node $node, Scope $scope): array
    {
        if (!$this->isDbCall($node, 'transaction')) {
            return [];
        }

        $calls = [];
        foreach ($node->getArgs() as $arg) {
            if ($arg->value instanceof Closure || $arg->value instanceof ArrowFunction) {
                $this->collect($arg->value, $calls);
            }
        }

        $errors = [];
        foreach ($calls as [$facade, $method, $line]) {
            $errors[] = RuleErrorBuilder::message(sprintf(self::MESSAGE, $facade, $method))
                ->identifier(self::IDENTIFIER)
                ->line($line)
                ->build();
        }

        return $errors;
    }

    // Private Methods
    // =========================================================================

    /**
     * Walks a node's children and collects the side-effect facade calls in them.
     *
     * Does not descend into DB::afterCommit() calls, nested DB::transaction()
     * calls (their own visit reports them), named functions or class bodies.
     *
     * @param Node $node
     * @param list<array{string, string, int}> $calls collected [facade, method, line] triples
     * @author michtio
     */
    private function collect(Node $node, array &$calls): void
    {
        foreach ($node->getSubNodeNames() as $name) {
            $children = $node->$name;
            foreach (is_array($children) ? $children : [$children] as $child) {
                if (!$child instanceof Node) {
                    continue;
                }
                if ($child instanceof ClassLike || $child instanceof Function_) {
                    continue;
                }
                if ($child instanceof StaticCall) {
                    if ($this->isDbCall($child, 'afterCommit') || $this->isDbCall($child, 'transaction')) {
                        continue;
                    }
                    $facade = $this->sideEffectFacade($child);
                    if ($facade !== null && $child->name instanceof Identifier) {
                        $calls[] = [$facade, $child->name->toString(), $child->getStartLine()];
                    }
                }
                $this->collect($child, $calls);
            }
        }
    }

    /**
     * Whether the call is DB::<method>() on the DB facade.
     *
     * @param StaticCall $call
     * @param string $method
     * @return bool
     * @author michtio
     */
    private function isDbCall(StaticCall $call, string $method): bool
    {
        return $call->class instanceof Name
            && in_array(ltrim($call->class->toString(), '\\'), self::DB_FACADES, true)
            && $call->name instanceof Identifier
            && $call->name->toLowerString() === strtolower($method);
    }

    /**
     * Returns the short facade name when the call is on Http or Mail, or null.
     *
     * @param StaticCall $call
     * @return string|null
     * @author michtio
     */
    private function sideEffectFacade(StaticCall $call): ?string
    {
        if (!$call->class instanceof Name) {
            return null;
        }

        return self::SIDE_EFFECT_FACADES[ltrim($call->class->toString(), '\\')] ?? null;
    }
}
