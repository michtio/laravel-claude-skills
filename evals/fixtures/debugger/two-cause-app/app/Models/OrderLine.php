<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;

/**
 * A line a customer removed from the order is soft deleted, not destroyed.
 */
class OrderLine extends Model
{
    use SoftDeletes;

    protected $guarded = [];
}
