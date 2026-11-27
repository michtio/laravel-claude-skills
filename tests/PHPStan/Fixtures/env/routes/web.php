<?php

declare(strict_types=1);

$enabled = env('FEATURE_Y', false);

$handler = function () {
    return env('MAINTENANCE_TOKEN');
};
