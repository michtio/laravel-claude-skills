<?php

namespace App\Http\Controllers;

use App\Models\Order;
use App\Support\OrderFormatter;

class OrderController extends Controller
{
    /**
     * @return array{id: int, total: int}
     */
    public function summary(Order $order): array
    {
        $this->authorize('view', $order);

        return ['id' => $order->id, 'total' => $order->total];
    }

    /**
     * @return array{email: string, total: string}
     */
    public function show(Order $order): array
    {
        $this->authorize('view', $order);

        $formatter = new OrderFormatter();

        return ['email' => $order->customer->email, 'total' => $formatter->money($order->total)];
    }
}
