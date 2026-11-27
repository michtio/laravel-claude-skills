<?php

declare(strict_types=1);

$local = '5';

return [
    'port' => env('PORT', 8080),
    'name' => (string) env('NAME', 'service'),
    'workers' => (int) config('services.workers'),
    'retries' => (int) $local,
    'debug' => env('DEBUG', false),
];
