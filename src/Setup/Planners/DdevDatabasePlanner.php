<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup\Planners;

use Michtio\LaravelClaudeSkills\Setup\PlannedFile;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\SetupException;

/**
 * Writes `.ddev/config.claude-skills.yaml`, a DDEV config override with a
 * post-start hook that creates the test database (<slug>_test) in the db
 * container on every `ddev start`. DDEV merges every `.ddev/config.*.yaml` into
 * the project config, so `.ddev/config.yaml` is never touched.
 *
 * The hook runs in the db service with DDEV's default credentials and is
 * idempotent:
 * - MySQL and MariaDB: `CREATE DATABASE IF NOT EXISTS` plus a `GRANT ALL` to the
 *   `db` user, as root (password root);
 * - PostgreSQL: psql as `db` (password db) with
 *   `SELECT 'CREATE DATABASE …' WHERE NOT EXISTS (…)\gexec`, PostgreSQL having
 *   no IF NOT EXISTS for databases, plus a `GRANT ALL PRIVILEGES ON DATABASE`.
 * It never uses `exec-host`: nothing runs on the host.
 *
 * Written only for a DDEV application whose suite uses a server database (not a
 * package, not sqlite) on mysql, mariadb or pgsql. Any other application on a
 * server database gets a notice instead (notice()): the setup cannot create it.
 *
 * @author michtio
 */
final class DdevDatabasePlanner implements Planner
{
    // Constants
    // =========================================================================

    /**
     * Path of the DDEV override, relative to the project root.
     */
    public const PATH = '.ddev/config.claude-skills.yaml';

    /**
     * The connections the hook can create a database for.
     */
    public const CONNECTIONS = ['mysql', 'mariadb', 'pgsql'];

    /**
     * A database name that is safe unquoted in MySQL, PostgreSQL and the shell.
     */
    public const IDENTIFIER = '/^[a-z][a-z0-9_]{0,62}$/';

    // Public Methods
    // =========================================================================

    /**
     * Plan the hook file, or its absence when the project needs none.
     *
     * @throws SetupException When the test database name is not a plain identifier.
     * @author michtio
     */
    public function plan(Project $project): PlannedFile
    {
        return PlannedFile::whole($project->root, self::PATH, $this->content($project));
    }

    /**
     * The override for the project, or null when it gets none.
     *
     * @throws SetupException When the test database name is not a plain identifier.
     * @author michtio
     */
    public function content(Project $project): ?string
    {
        if (! $project->usesDdev() || $project->usesMemoryDatabase()) {
            return null;
        }

        $shell = $this->shell($project->dbConnection(), $project->testDatabase());

        if ($shell === null) {
            return null;
        }

        return implode("\n", [
            '# Written by claude-skills:setup: creates the test database '.$project->testDatabase().' in the db',
            '# container on every ddev start (idempotent). DDEV merges .ddev/config.*.yaml files.',
            'hooks:',
            '  post-start:',
            '    - exec: '.json_encode($shell, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
            '      service: db',
        ])."\n";
    }

    /**
     * The line telling the person to create the test database, or null when the
     * setup takes care of it or the suite needs none.
     *
     * Shown for an application on a server database the setup cannot create: a
     * host app (no DDEV), or a DDEV app on a connection the hook does not support.
     *
     * @author michtio
     */
    public function notice(Project $project): ?string
    {
        if ($project->usesMemoryDatabase()) {
            return null;
        }

        $connection = $project->dbConnection();
        $database = $project->testDatabase();

        if ($project->usesDdev() && in_array($connection, self::CONNECTIONS, true)) {
            return null;
        }

        return sprintf(
            'The test database %1$s must exist on your %2$s server before the suite runs: the setup creates it only inside DDEV. Create it once, for example with: CREATE DATABASE %1$s;',
            $database,
            $connection,
        );
    }

    /**
     * The shell command run in the db container, or null for an unsupported connection.
     *
     * @throws SetupException When the database name is not a plain identifier (/^[a-z][a-z0-9_]{0,62}$/),
     *                        so nothing unvalidated reaches a shell or SQL.
     * @author michtio
     */
    public function shell(string $connection, string $database): ?string
    {
        if (preg_match(self::IDENTIFIER, $database) !== 1) {
            throw new SetupException('Refusing to write the DDEV database hook: "'.$database.'" is not a plain database identifier.');
        }

        return match ($connection) {
            'mysql', 'mariadb' => sprintf(
                'mysql -uroot -proot -e "CREATE DATABASE IF NOT EXISTS %1$s; GRANT ALL ON %1$s.* TO \'db\'@\'%%\';"',
                $database,
            ),
            'pgsql' => sprintf(
                'printf \'%%s\n\' "SELECT \'CREATE DATABASE %1$s\' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = \'%1$s\')\gexec" "GRANT ALL PRIVILEGES ON DATABASE %1$s TO db;" | PGPASSWORD=db psql -v ON_ERROR_STOP=1 -U db -d postgres',
                $database,
            ),
            default => null,
        };
    }
}
