<?php

use App\Services\GreetingService;

it('rejects a name longer than 40 characters', function () {
    // expect-contains: app/Services/GreetingService.php InvalidArgumentException
    expect(fn () => (new GreetingService())->greet(str_repeat('a', 41)))
        ->toThrow(InvalidArgumentException::class);
});

it('trims surrounding spaces', function () {
    // expect-contains: app/Services/GreetingService.php trim(
    expect((new GreetingService())->greet(' Ada '))->toBe('Hello, Ada!');
});
