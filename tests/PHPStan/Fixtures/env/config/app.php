<?php

declare(strict_types=1);

return [
    'name' => env('APP_NAME', 'App'),
    'region' => env('REGION', 'eu'),
    'nested' => [
        'key' => env('PAYMENT_KEY'),
    ],
];
