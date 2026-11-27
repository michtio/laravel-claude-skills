@php
    // On by default. Off only when .ai/skills-profile.json holds "laravel": {"house_style": false}.
    // A missing, unreadable or malformed profile keeps the guideline on.
    $houseStyle = true;

    try {
        $profilePath = base_path('.ai/skills-profile.json');

        if (is_file($profilePath) && is_readable($profilePath)) {
            $profile = json_decode((string) file_get_contents($profilePath), true);

            if (is_array($profile)
                && isset($profile['laravel'])
                && is_array($profile['laravel'])
                && array_key_exists('house_style', $profile['laravel'])
                && $profile['laravel']['house_style'] === false) {
                $houseStyle = false;
            }
        }
    } catch (\Throwable $e) {
        $houseStyle = true;
    }
@endphp
@if ($houseStyle)
## House PHP style

This project follows a house style on top of PSR-12 and Pint. It applies to every PHP file the project owns, in `app/`, `config/`, `database/`, `routes/` and `tests/`; the class and method rules apply wherever there are classes and methods.

- Strict types: every PHP file starts with `declare(strict_types=1);` after the opening tag.
- PHPDocs on every class and every method, including private methods, constructors and test helpers. The summary line says what it does and why; `@param` and `@return` are added where the native type says less than the docblock (array shapes, generics, collections), and `@throws` lists what callers must handle.
- `@author` on classes and methods only, never on properties or constants. Use the author line the project already uses, the same in every file.
- Section headers: group class members under comment headers with a `=========` rule line, in this order: Constants, Properties, Public Methods, Protected Methods, Private Methods. Leave out a section with no members.

```php
<?php

declare(strict_types=1);

namespace App\Actions;

use App\Models\Invoice;
use App\Models\User;

/**
 * Approves an invoice and records who approved it.
 *
 * @author Example Team
 */
final class ApproveInvoice
{
    // Public Methods
    // =========================================================================

    /**
     * Mark the invoice approved by the given user.
     *
     * @author Example Team
     */
    public function handle(Invoice $invoice, User $approver): void
    {
        $invoice->approve($approver);
    }
}
```

Where another guideline is silent or looser on docblocks, this section wins, and the section headers are an intended exception to any rule against inline comments. To switch it off, set `"laravel": {"house_style": false}` in `.ai/skills-profile.json` and run `boost:update`.

Before adding or recommending a Composer package, load the `laravel-package-verdicts` skill: it holds the package register (use, avoid or depends, with conditions), and the profile's own verdicts take precedence over it.
@endif
