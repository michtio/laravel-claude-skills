<?php

namespace App\Services;

use App\Models\Coupon;

class DiscountCalculator
{
    /**
     * The discount in cents for a subtotal in cents.
     */
    public function amount(int $subtotal, ?Coupon $coupon): int
    {
        if ($coupon === null) {
            return 0;
        }

        return $subtotal * (int) ($coupon->percent / 100);
    }
}
