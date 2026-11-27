<?php

it('greets Ada', function () {
    // expect-contains: app/Services/GreetingService.php Hello, Ada!
    expect((new App\Services\GreetingService())->greet('Ada'))->toBe('Hello, Ada!');
});

it('has the greeting API token in the environment', function () {
    // expect-env: GREETING_API_TOKEN
    expect(env('GREETING_API_TOKEN'))->not->toBeEmpty();
});
