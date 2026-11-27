<?php

declare(strict_types=1);

/**
 * The advisories read workflows and PHPUnit files by heuristic: these pin the edges the checker
 * found in S9d-1 (a `composer test:<name>` script, a commented-out test line, a single-quoted
 * in-memory pin).
 */

use Michtio\LaravelClaudeSkills\Setup\Advisories;
use Michtio\LaravelClaudeSkills\Setup\Kind;
use Michtio\LaravelClaudeSkills\Setup\Project;
use Michtio\LaravelClaudeSkills\Setup\Runner;

/**
 * Write one workflow into the project.
 */
function workflowAdvisoryPut(string $dir, string $name, string $run): void
{
    if (! is_dir($dir.'/.github/workflows')) {
        mkdir($dir.'/.github/workflows', 0777, true);
    }
    file_put_contents($dir.'/.github/workflows/'.$name, "name: x\non: [push]\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n".$run);
}

it('does not take a composer test:<name> script for the test suite', function () {
    $dir = $this->project('app', ddev: true);
    workflowAdvisoryPut($dir, 'lint.yml', "      - run: composer test:lint\n");
    workflowAdvisoryPut($dir, 'coverage.yml', "      - run: composer test-coverage\n");
    workflowAdvisoryPut($dir, 'suite.yml', "      - run: composer test\n");

    $line = Advisories::workflowsWithoutDatabase(new Project($dir, Kind::App, Runner::Ddev));

    expect($line)->toContain('.github/workflows/suite.yml')
        ->not->toContain('lint.yml')
        ->not->toContain('coverage.yml');
});

it('ignores a test command that only appears in a comment line', function () {
    $dir = $this->project('app', ddev: true);
    workflowAdvisoryPut($dir, 'notes.yml', "      # - run: vendor/bin/pest\n      - run: echo hello\n");

    expect(Advisories::workflowsWithoutDatabase(new Project($dir, Kind::App, Runner::Ddev)))->toBeNull();
});

it('reads a single-quoted in-memory DB_DATABASE pin as not yet moved', function () {
    $dir = $this->project('package', ddev: true);
    mkdir($dir.'/tests', 0777, true);
    file_put_contents($dir.'/tests/MemberTest.php', "<?php\n");
    file_put_contents($dir.'/phpunit.xml.dist', "<phpunit><php><env name='DB_DATABASE' value=':memory:' force='true'/></php></phpunit>\n");

    $project = new Project($dir, Kind::Package, Runner::Ddev, false, true, ['type' => 'mariadb', 'version' => '11.8']);

    expect(Advisories::movedSuite($project))->toContain('docs/profile.md');
});
