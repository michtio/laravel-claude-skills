<?php

declare(strict_types=1);

return [
    'port' => (int) env('PORT'),
    'rate' => (float) env('RATE', 1.5),
    'debug' => (bool) env('DEBUG'),
    'nested' => [
        'workers' => (int) \env('WORKERS', 4),
    ],
];
