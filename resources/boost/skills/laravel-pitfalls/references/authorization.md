# Authorization: every door, and what a refusal gives away

Gap: covered partly by Boost (laravel-best-practices, rules/security.blade.php: "Authorize protected actions"; rules/routing.md: "Scope nested bindings")

Boost says to authorize with policies, gates or form requests, and that scoped bindings constrain resolution without replacing authorization. It does not cover the ways a correct policy still leaves a hole: a second door to the same action that skips it, a refusal that tells the caller the record exists, a request body that moves a record somewhere the check never looked, and a screen that receives more than it shows.

## Pitfall 1: one action, several doors, one of them open

The same action is usually reachable from more than one place: a web controller, an API route, a bulk action, a queued job, a console command, and the sibling method that does nearly the same thing (`void()` next to `archive()`, `refund()` next to `cancel()`). A policy check written in one controller protects that controller only. The new door, added later by someone copying the service call, ships without it.

A role flag sent to the browser (a shared prop, a `can` map) only decides whether a button renders. Hiding the button does not stop anyone from sending the request.

### Fix

Put the check where every door has to pass: in the action or service method itself, as its first statement, or in one form request that every route for the action uses. Keep controllers thin (validate, authorize, delegate) so there is one implementation to protect. When a rule says "every method that does X takes the check", write X down as a test you can run (for example "every method that reverses a posting"), not as a habit.

```php
use App\Models\Invoice;
use Illuminate\Support\Facades\Gate;

final class VoidInvoice
{
    public function handle(Invoice $invoice): void
    {
        Gate::authorize('void', $invoice); // every caller: controller, API, bulk action

        $invoice->update(['status' => 'void']);
    }
}
```

A path that records something a third party has already done (a provider webhook, an import of a settled fact) has no user to ask. Leave it unchecked on purpose, keep it unreachable from any route a person can call, and say so on the class.

## Pitfall 2: 403 for a record that is not yours

Returning 403 Forbidden for another account's or tenant's record confirms that the id exists. With sequential ids, anyone can walk the range and count another customer's invoices.

### Fix

Resolve the record through the owner's scope, so a foreign id is never found and the response is 404. With a tenant global scope on the model, route model binding already does this. Scoped bindings do the same for nested routes. When a policy must refuse after the record was found, make it look like a missing record:

```php
use App\Models\Invoice;
use App\Models\User;
use Illuminate\Auth\Access\Response;

public function view(User $user, Invoice $invoice): Response
{
    return $invoice->account_id === $user->account_id
        ? Response::allow()
        : Response::denyAsNotFound();
}
```

Let the scope decide ownership and the policy decide role. A policy that checks both invites the two checks to disagree.

## Pitfall 3: the request body changes who the record belongs to

Authorizing the record as loaded is not enough when the request can repoint it. Moving a draft invoice to another client is the typical case: `client_id` arrives in the body, `exists:clients,id` passes for any client in the table, the foreign key is satisfied by a client of another tenant, and the tenant scope never sees the write. Validation is not authorization (Boost says so), and `exists` is the rule people forget it applies to.

### Fix

Re-check after populating. Constrain `exists` to the owner, or resolve the new related record through the scoped model and authorize against the populated result:

```php
use Illuminate\Validation\Rule;

'client_id' => ['required', Rule::exists('clients', 'id')->where('account_id', $this->user()->account_id)],
```

```php
$client = Client::query()->findOrFail($validated['client_id']); // tenant scope applies: foreign id is a 404
Gate::authorize('update', $client);

$invoice->client()->associate($client)->save();
```

## Pitfall 4: the screen receives the model

Passing a model to a page or JSON response serializes every attribute that is not in `$hidden`. A column added next year (an internal note, a risk score, a token) reaches the browser because nobody remembered to hide it.

### Fix

Hand the screen named fields: an API resource or a presenter that lists each field. A new column then appears only when someone adds it to that list.

## How to test it

- One test per door: call the action from each route, job and command as a user without the ability, and assert the refusal. Revert the check in the service (keep it in one controller) and the tests for the other doors go red.
- Request another tenant's record by id and assert 404, not 403.
- Submit a foreign `client_id` and assert a validation error or 404, and that the invoice's client did not change. Drop the `where()` on the rule and the test goes red.
- Assert the exact keys of a JSON response (`assertExactJson`, or `assertJsonStructure` plus a missing-key check) so a new column fails a test.

## Check

Review only. Whether every door reaches the same check, and whether a body field can move a record across owners, depends on routes, data flow and intent that a static rule cannot see. For every new route, job or command, find the check it passes through. For every foreign key in a request, find the owner constraint.
