<?php

declare(strict_types=1);

namespace Michtio\LaravelClaudeSkills\Setup;

/**
 * Renders a unified diff (as `diff -u` and git print it) between two versions of a file.
 *
 * A created file diffs from `/dev/null`, a deleted one to `/dev/null`. The files
 * the setup writes are small, so a plain longest-common-subsequence table is
 * enough; hunks carry three lines of context.
 *
 * @author michtio
 */
final class UnifiedDiff
{
    // Constants
    // =========================================================================

    /**
     * Lines of unchanged context around each change.
     */
    private const CONTEXT = 3;

    // Public Methods
    // =========================================================================

    /**
     * The diff lines for a file, headers first.
     *
     * @return list<string>
     * @author michtio
     */
    public static function render(string $path, ?string $before, ?string $after): array
    {
        $old = self::lines($before);
        $new = self::lines($after);
        $out = [
            $before === null ? '--- /dev/null' : '--- a/'.$path,
            $after === null ? '+++ /dev/null' : '+++ b/'.$path,
        ];

        foreach (self::hunks(self::operations($old, $new)) as $hunk) {
            array_push($out, ...$hunk);
        }

        return $out;
    }

    // Private Methods
    // =========================================================================

    /**
     * Split content into lines without their line endings.
     *
     * @return list<string>
     * @author michtio
     */
    private static function lines(?string $content): array
    {
        if ($content === null || $content === '') {
            return [];
        }

        $lines = preg_split('/\r\n|\n/', $content) ?: [];

        if (end($lines) === '') {
            array_pop($lines);
        }

        return $lines;
    }

    /**
     * The edit script from old to new: [op, oldIndex, newIndex, line] with op ' ', '-' or '+'.
     *
     * @param list<string> $old
     * @param list<string> $new
     * @return list<array{0: string, 1: int, 2: int, 3: string}>
     * @author michtio
     */
    private static function operations(array $old, array $new): array
    {
        $n = count($old);
        $m = count($new);
        $lcs = array_fill(0, $n + 1, array_fill(0, $m + 1, 0));

        for ($i = $n - 1; $i >= 0; $i--) {
            for ($j = $m - 1; $j >= 0; $j--) {
                $lcs[$i][$j] = $old[$i] === $new[$j]
                    ? $lcs[$i + 1][$j + 1] + 1
                    : max($lcs[$i + 1][$j], $lcs[$i][$j + 1]);
            }
        }

        $ops = [];
        $i = 0;
        $j = 0;

        while ($i < $n || $j < $m) {
            if ($i < $n && $j < $m && $old[$i] === $new[$j]) {
                $ops[] = [' ', $i, $j, $old[$i]];
                $i++;
                $j++;
            } elseif ($j < $m && ($i >= $n || $lcs[$i][$j + 1] >= $lcs[$i + 1][$j])) {
                $ops[] = ['+', $i, $j, $new[$j]];
                $j++;
            } else {
                $ops[] = ['-', $i, $j, $old[$i]];
                $i++;
            }
        }

        return $ops;
    }

    /**
     * Group the edit script into hunks with context, each starting with its @@ header.
     *
     * @param list<array{0: string, 1: int, 2: int, 3: string}> $ops
     * @return list<list<string>>
     * @author michtio
     */
    private static function hunks(array $ops): array
    {
        $changed = [];

        foreach ($ops as $index => $op) {
            if ($op[0] !== ' ') {
                $changed[] = $index;
            }
        }

        if ($changed === []) {
            return [];
        }

        // Ranges of op indexes (parallel start and end lists), merged when their context would overlap.
        $starts = [];
        $ends = [];

        foreach ($changed as $index) {
            $start = max(0, $index - self::CONTEXT);
            $end = min(count($ops) - 1, $index + self::CONTEXT);
            $last = count($ends) - 1;

            if ($last >= 0 && $start <= $ends[$last] + 1) {
                $ends[$last] = max($ends[$last], $end);
            } else {
                $starts[] = $start;
                $ends[] = $end;
            }
        }

        $hunks = [];

        foreach ($starts as $range => $start) {
            $end = $ends[$range];
            $slice = array_slice($ops, $start, $end - $start + 1);
            $oldCount = count(array_filter($slice, static fn (array $op): bool => $op[0] !== '+'));
            $newCount = count(array_filter($slice, static fn (array $op): bool => $op[0] !== '-'));
            $oldStart = $oldCount === 0 ? $slice[0][1] : $slice[0][1] + 1;
            $newStart = $newCount === 0 ? $slice[0][2] : $slice[0][2] + 1;

            $lines = [sprintf('@@ -%d,%d +%d,%d @@', $oldStart, $oldCount, $newStart, $newCount)];

            foreach ($slice as $op) {
                $lines[] = $op[0].$op[3];
            }

            $hunks[] = $lines;
        }

        return $hunks;
    }
}
