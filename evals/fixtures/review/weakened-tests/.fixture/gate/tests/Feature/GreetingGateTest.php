<?php

use App\Services\GreetingService;

it('greets the world for an empty name', function () {
    // expect-contains: app/Services/GreetingService.php Hello, world!
    expect((new GreetingService())->greet(''))->toBe('Hello, world!');
});

it('greets a name', function () {
    // expect-contains: app/Services/GreetingService.php Hello,
    $service = new GreetingService();

    expect($service->greet('Ada'))->toBe('Hello, Ada!');
    expect($service->greet('  Ada  '))->toBe('Hello, Ada!');
});

it('shouts when asked', function () {
    // expect-contains: app/Services/GreetingService.php strtoupper
    expect((new GreetingService())->greet('Ada', shout: true))->toBe('HELLO, ADA!');
});
