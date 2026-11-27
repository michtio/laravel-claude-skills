<?php

namespace App\Legacy;

class Report
{
    public function build(array $rows)
    {
        return array_map(fn ($row) => $row['name'], $rows);
    }
}
