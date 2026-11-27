<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * Reads the database engine and version DDEV runs for a project, for a package on
 * `laravel.test_database: ddev` whose `.ddev/config.yaml` does not name them in
 * full. Resolved from the container, so a test can bind its own.
 *
 * @author michtio
 */
interface DdevDatabaseSource
{
    // Public Methods
    // =========================================================================

    /**
     * The database DDEV runs for the project at the root, or null when nothing can be read.
     *
     * @return array{type: string, version: string}|null Type `mariadb`, `mysql` or `postgres`; version such as `11.8`.
     * @author michtio
     */
    public function read(string $root): ?array;
}
