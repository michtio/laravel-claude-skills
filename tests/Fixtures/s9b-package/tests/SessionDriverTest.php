<?php

declare(strict_types=1);

namespace Tests;

use Orchestra\Testbench\TestCase;

/**
 * Proves the `env` pins of laravel.test_pins: a SESSION_DRIVER or QUEUE_CONNECTION set in the shell
 * reaches the suite, and the phpunit default (array, sync) applies when nothing is set.
 * S9B_EXPECT_SESSION and S9B_EXPECT_QUEUE name what the caller expects; both are unset in the
 * plain `composer test` run. QUEUE_CONNECTION is the sharper case: a forced pin also writes a
 * server twin, which beats a shell value, while SESSION_DRIVER has none.
 */
class SessionDriverTest extends TestCase
{
    /**
     * The session driver the suite sees is the shell's, or array without one.
     */
    public function test_the_session_driver_follows_the_shell_or_the_phpunit_default(): void
    {
        $this->assertSame($this->expected('S9B_EXPECT_SESSION', 'array'), config('session.driver'));
    }

    /**
     * The queue connection the suite sees is the shell's, or sync without one.
     */
    public function test_the_queue_connection_follows_the_shell_or_the_phpunit_default(): void
    {
        $this->assertSame($this->expected('S9B_EXPECT_QUEUE', 'sync'), config('queue.default'));
    }

    /**
     * The value the caller expects, or the default when the variable is unset or empty.
     */
    private function expected(string $name, string $default): string
    {
        $value = getenv($name);

        return $value === false || $value === '' ? $default : $value;
    }
}
