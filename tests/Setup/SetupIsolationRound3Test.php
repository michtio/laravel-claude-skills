<?php

declare(strict_types=1);

/**
 * Gate tests for slice S6b, round 3. Locked gate file. Uses the iso* helpers of
 * SetupIsolationTest.php.
 *
 * PINNED CONTRACT (round 3)
 *
 * 1. commit-msg, trailer forms: a Co-Authored-By trailer is recognised with or
 *    without a space after the colon, and with a tab; a "Generated with" line is
 *    recognised when the tool name is wrapped in a markdown link
 *    (`Generated with [Claude Code](https://claude.com/claude-code)`), with no emoji.
 *
 * 2. commit-msg, colliding human names: inside a Co-Authored-By trailer a tool
 *    word counts only with an AI qualifier or a vendor address: `GitHub Copilot`,
 *    `Copilot <...@github.com>`, `Gemini Code Assist`, `Cursor Agent`, `ChatGPT`,
 *    `OpenAI Codex`, `noreply@anthropic.com`, `claude[bot]`, and the Claude and
 *    Devin forms of round 2. A human "Gemini Rossi", "Cursor Black", or an
 *    address like jane@openai-fan.org is accepted.
 *
 * 3. HooksPathPlanner notice: the hooks directory named in the notice is the one
 *    `git rev-parse --git-path hooks` resolves (in a linked worktree it is the
 *    main repository's hooks directory), never a hard-coded `.git/hooks`.
 */

it('commit-msg round 3: trailer forms, colliding human names, vendor qualifiers', function (string $message, int $expected) {
    $dir = $this->project('app');
    isoSetup($dir, ['--yes' => true]);
    isoPut($dir, 'MSG', $message);

    [$code, $output] = isoRun($dir, '.githooks/commit-msg', arg: 'MSG');

    expect($code)->toBe($expected);
    if ($expected !== 0) {
        expect($output)->not->toBe('');
    }
})->with([
    // rejected: trailer forms
    'markdown link, no emoji' => ["Add thing\n\nGenerated with [Claude Code](https://claude.com/claude-code)\n", 1],
    'no space after colon' => ["Add thing\n\nCo-Authored-By:Claude Opus <n@x>\n", 1],
    'tab after colon' => ["Add thing\n\nco-authored-by:\tClaude Sonnet 4 <noreply@anthropic.com>\n", 1],
    // rejected: AI qualifier or vendor address
    'github copilot' => ["Add thing\n\nCo-authored-by: GitHub Copilot <x@example.com>\n", 1],
    'copilot with github address' => ["Add thing\n\nCo-authored-by: Copilot <copilot@github.com>\n", 1],
    'gemini code assist' => ["Add thing\n\nCo-authored-by: Gemini Code Assist <x@example.com>\n", 1],
    'cursor agent' => ["Add thing\n\nCo-authored-by: Cursor Agent <x@example.com>\n", 1],
    'chatgpt' => ["Add thing\n\nCo-authored-by: ChatGPT <x@example.com>\n", 1],
    'openai codex' => ["Add thing\n\nCo-authored-by: OpenAI Codex <x@example.com>\n", 1],
    'anthropic noreply, other name' => ["Add thing\n\nCo-authored-by: Helper <noreply@anthropic.com>\n", 1],
    'claude bot' => ["Add thing\n\nCo-authored-by: claude[bot] <x@example.com>\n", 1],
    'devin' => ["Add thing\n\nCo-authored-by: Devin AI <devin@cognition.ai>\n", 1],
    // accepted: humans whose names collide with tool names
    'human Gemini Rossi' => ["Add thing\n\nCo-Authored-By: Gemini Rossi <g@r.it>\n", 0],
    'human with openai-fan address' => ["Add thing\n\nCo-authored-by: Jane Doe <jane@openai-fan.org>\n", 0],
    'human Cursor Black' => ["Add thing\n\nCo-authored-by: Cursor Black <c@b.io>\n", 0],
    'human, no space after colon' => ["Add thing\n\nCo-authored-by:Jane Doe <jane@example.com>\n", 0],
]);

it('names the resolved hooks directory in a linked worktree, not a hard-coded .git/hooks', function () {
    $main = $this->project('app');
    isoGit($main, 'init -q');
    isoGit($main, 'config user.email t@example.com');
    isoGit($main, 'config user.name T');
    isoGit($main, 'add -A');
    isoGit($main, 'commit -q -m init');
    $worktree = $main.'-wt';
    expect(isoGit($main, 'worktree add -q '.escapeshellarg($worktree).' -b round3')[0])->toBe(0);
    isoPut($main, '.git/hooks/pre-commit', "#!/bin/sh\nexit 0\n");
    chmod($main.'/.git/hooks/pre-commit', 0755);

    try {
        [, $resolved] = isoGit($worktree, 'rev-parse --git-path hooks');
        $resolved = str_starts_with($resolved, '/') ? $resolved : $worktree.'/'.$resolved;
        [$code, $output] = isoSetup($worktree, ['--yes' => true]);

        expect($code)->toBe(0)
            ->and($output)->toContain('pre-commit')
            ->and($output)->toContain($resolved)
            ->and(isoGit($worktree, 'config --get core.hooksPath')[1])->toBe('');
    } finally {
        exec('rm -rf '.escapeshellarg($worktree));
    }
});
