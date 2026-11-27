<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\PHPStan\Rules;

use PhpParser\Node;
use PhpParser\Node\Expr\FuncCall;
use PhpParser\Node\Name;
use PHPStan\Analyser\Scope;
use PHPStan\Rules\IdentifierRuleError;
use PHPStan\Rules\Rule;
use PHPStan\Rules\RuleErrorBuilder;

/**
 * Reports a call to env() in a file outside a config directory.
 *
 * Pitfall: laravel-pitfalls, edge-validation. Once `php artisan config:cache`
 * has run, Laravel no longer loads the .env file, so env() returns null (or its
 * default) everywhere except while the config files are being cached. Code that
 * works locally then reads null in production.
 *
 * What is reported: every call to the env() function, global or fully
 * qualified, in a file whose path has no directory segment named `config`.
 * Methods and static methods that happen to be named env are not the function
 * and are not reported.
 *
 * Proven by tests/PHPStan/Rules/NoEnvOutsideConfigRuleTest.php.
 *
 * @author michtio
 * @implements Rule<FuncCall>
 */
final class NoEnvOutsideConfigRule implements Rule
{
    // Constants
    // =========================================================================

    /**
     * Error message.
     */
    public const MESSAGE = 'env() called outside the config directory returns null once the configuration is cached. Read it in a config file and use config() here. See laravel-pitfalls: edge-validation.';

    /**
     * Error identifier reported with every error.
     */
    public const IDENTIFIER = 'laravelPitfalls.envOutsideConfig';

    // Public Methods
    // =========================================================================

    /**
     * Returns the node type this rule visits.
     *
     * @return class-string<FuncCall>
     * @author michtio
     */
    public function getNodeType(): string
    {
        return FuncCall::class;
    }

    /**
     * Reports the env() call when the analysed file is not under a config directory.
     *
     * @param FuncCall $node
     * @param Scope $scope
     * @return list<IdentifierRuleError>
     * @author michtio
     */
    public function processNode(Node $node, Scope $scope): array
    {
        if (!$node->name instanceof Name || $node->name->toLowerString() !== 'env') {
            return [];
        }

        if ($this->isInConfigDirectory($scope->getFile())) {
            return [];
        }

        return [
            RuleErrorBuilder::message(self::MESSAGE)
                ->identifier(self::IDENTIFIER)
                ->build(),
        ];
    }

    // Private Methods
    // =========================================================================

    /**
     * Whether a directory segment of the path is named config.
     *
     * @param string $file
     * @return bool
     * @author michtio
     */
    private function isInConfigDirectory(string $file): bool
    {
        $segments = explode('/', str_replace('\\', '/', $file));
        array_pop($segments);

        return in_array('config', $segments, true);
    }
}
