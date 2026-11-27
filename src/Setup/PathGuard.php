<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * Refuses owned paths that are symlinks or resolve outside the project root.
 *
 * The setup reads, diffs and writes its own files. Through a symlink it would
 * print or overwrite a file outside the project, so every owned path and each of
 * its parent directories up to the root is checked before anything is read, and
 * again right before each write.
 *
 * @author michtio
 */
final class PathGuard
{
    // Public Methods
    // =========================================================================

    /**
     * Check one owned path (relative to the root) and its parents.
     *
     * @throws SetupException When a component is a symlink or resolves outside the root.
     * @author michtio
     */
    public static function assertSafe(string $root, string $relative): void
    {
        $prefix = '';

        foreach (explode('/', $relative) as $part) {
            $prefix = $prefix === '' ? $part : $prefix.'/'.$part;
            $path = $root.'/'.$prefix;

            if (is_link($path)) {
                throw new SetupException('Refusing to follow a symlink: '.$prefix.'. The setup never reads or writes through a symlink; replace it with a regular file or directory, then run the setup again. Nothing was written.');
            }

            if (! file_exists($path)) {
                return;
            }

            $real = realpath($path);

            if ($real === false || ($real !== $root && ! str_starts_with($real, $root.DIRECTORY_SEPARATOR))) {
                throw new SetupException('Refusing '.$prefix.': it resolves outside the project (symlink or mount). Nothing was written.');
            }
        }
    }

    /**
     * Check every given owned path.
     *
     * @param list<string> $paths
     * @throws SetupException When any of them is unsafe.
     * @author michtio
     */
    public static function assertAllSafe(string $root, array $paths): void
    {
        foreach ($paths as $path) {
            self::assertSafe($root, $path);
        }
    }
}
