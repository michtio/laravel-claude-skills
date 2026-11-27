<?php

namespace App\Support;

class OrderFormatter
{
    public function money(int $cents): string
    {
        $res = number_format($cents / 100, 2, '.', '');

        return $res;
    }
}
