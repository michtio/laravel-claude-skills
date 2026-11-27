<?php

namespace App\Services;

use App\Models\Order;

class InvoiceCalculator
{
    public function __construct(private DiscountCalculator $discounts)
    {
    }

    /**
     * The invoice total in cents: the lines the customer kept, minus the coupon.
     */
    public function total(Order $order): int
    {
        $subtotal = 0;

        foreach ($order->lines()->withTrashed()->get() as $line) {
            $subtotal += $line->unit_price_cents * $line->quantity;
        }

        return $subtotal - $this->discounts->amount($subtotal, $order->coupon);
    }
}
