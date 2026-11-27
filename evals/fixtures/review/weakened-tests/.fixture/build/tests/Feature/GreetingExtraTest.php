<?php

use App\Services\GreetingService;

it('greets a name with an accent', function () {
    // expect-contains: app/Services/GreetingService.php Hello,
    expect((new GreetingService())->greet('Zoë'))->toBe('Hello, Zoë!');
})->only();
