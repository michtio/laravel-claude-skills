<?php

namespace App\Support;

class OrderFormatter
{
    public function money(int $cents): string
    {
        return number_format($cents / 100, 2, '.', '');
    }
}
