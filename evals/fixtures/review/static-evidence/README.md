# Review fixture: static evidence

Not a real app. `.fixture/setup.sh` builds a base commit and leaves the change under review uncommitted. The change touches PHP, a migration, a test and `composer.json`. Larastan (a stand-in script) reports one real error in a changed file, an access on a nullable relation, and one old error in an unchanged file. `app/Support/OrderFormatter.php` carries a style quirk that no check, skill or spec states (an opinion). `composer.json` gains `laravel/ui`, which the package-verdicts register marks avoid.
