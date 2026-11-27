<?php

namespace App\Services;

use InvalidArgumentException;

class GreetingService
{
    public function greet(string $name, bool $shout = false): string
    {
        $name = trim($name);

        if (strlen($name) > 40) {
            throw new InvalidArgumentException('The name is too long.');
        }

        $greeting = 'Hello, ' . ($name === '' ? 'world' : $name) . '!';

        return $shout ? strtoupper($greeting) : $greeting;
    }
}
