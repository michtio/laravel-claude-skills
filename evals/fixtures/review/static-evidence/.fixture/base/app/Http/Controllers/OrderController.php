<?php

namespace App\Http\Controllers;

use App\Models\Order;

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
}
