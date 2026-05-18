# Data Dictionary

Schema reference for the 13 tables shipped with the challenge. All files live in `data/` as `<table>.csv.gz` once you've run `scripts/download_data.py`. A 200-row preview of every table is committed under `samples/` so you can inspect the shape without downloading.

> The dataset models a real, multi-city retail operation. Like any production data, it carries the consequences of how that operation actually runs — slow-changing dimensions, mid-period status changes, partial cancellations, return windows, overlapping campaigns, and operational disruptions. Treat every column at face value, verify your assumptions, and document the business logic you choose.

---

## Table index

| # | Table | Approx rows | Grain |
|---|---|---|---|
| 1 | `calendar` | ~820 | one row per calendar date |
| 2 | `categories` | ~135 | one row per category node |
| 3 | `stores` | 150 | one row per store |
| 4 | `store_geo_mapping` | ~155 | store → region history |
| 5 | `store_events` | ~50 | one row per operational event |
| 6 | `products` | 4,000 | one row per SKU |
| 7 | `pricing_history` | ~10,000 | price change history |
| 8 | `customers` | 400,000 | one row per customer |
| 9 | `promotions` | 3,000 | one row per promo offer |
| 10 | `inventory_snapshots` | ~9 M | weekly per (store, SKU) |
| 11 | `orders` | ~6 M | one row per order |
| 12 | `order_items` | ~16 M | one row per line item |
| 13 | `returns` | ~860 K | one row per returned line item |

---

## 1. `calendar`

Daily reference table for the analysis window.

| column | type | description |
|---|---|---|
| `date` | DATE | primary key, `YYYY-MM-DD` |
| `day_of_week` | string | Monday..Sunday |
| `day_of_month` | int | 1..31 |
| `month` | int | 1..12 |
| `month_name` | string | January..December |
| `year` | int | calendar year |
| `quarter_num` | int | 1..4 |
| `quarter` | string | e.g. `2025Q3` |
| `fiscal_year` | int | Indian fiscal year (Apr–Mar) |
| `fiscal_quarter` | string | e.g. `FY25Q1` |
| `is_weekend` | bool | |
| `is_holiday` | int | 1 on national / commercial holidays |
| `holiday_name` | string | empty when not a holiday |

---

## 2. `categories`

Three-level hierarchy: super-category → sub-category → leaf.

| column | type | description |
|---|---|---|
| `category_id` | string PK | `CAT0001` etc |
| `category_name` | string | |
| `parent_category_id` | string | NULL for top of hierarchy |
| `level` | int | 1, 2, or 3 |
| `super_category_id` | string | the level-1 ancestor |
| `super_category_name` | string | name of the level-1 ancestor |
| `is_premium` | int | premium flag |

---

## 3. `stores`

| column | type | description |
|---|---|---|
| `store_id` | string PK | `STR00001` etc |
| `store_name` | string | |
| `store_type` | string | `physical`, `dark_store`, `online_fulfillment` |
| `city` | string | |
| `state` | string | |
| `current_region_id` | string | latest region the store is associated with |
| `launch_date` | date | |
| `store_size_sqft` | int | |
| `manager_name` | string | |
| `is_active_flag` | int | 1 / 0 |

---

## 4. `store_geo_mapping`

History of which region a store has belonged to.

| column | type | description |
|---|---|---|
| `mapping_id` | int PK | |
| `store_id` | string FK → stores | |
| `region_id` | string | one of MUM, DEL, BLR, CHN, KOL, HYD, PUN, AHM |
| `region_name` | string | e.g. *Mumbai Metro* |
| `effective_from` | date | |
| `effective_to` | date | empty string for the currently-effective row |

---

## 5. `store_events`

Operational events at the store grain.

| column | type | description |
|---|---|---|
| `event_id` | string PK | |
| `store_id` | string FK | |
| `event_type` | string | `renovation`, `flood_closure`, `strike`, `system_outage`, `permanent_closure` |
| `start_date` | date | inclusive |
| `end_date` | date | inclusive; empty for ongoing |
| `impact_severity` | string | `full_closure`, `partial`, `system_only` |
| `description` | string | free text |

---

## 6. `products`

| column | type | description |
|---|---|---|
| `product_id` | string PK | `SKU000001` etc |
| `product_name` | string | |
| `brand` | string | |
| `category_id` | string FK → categories | |
| `super_category_id` | string FK → categories | level-1 ancestor |
| `mrp` | float | maximum retail price |
| `cost_price` | float | landed cost |
| `pack_size` | string | e.g. `500g`, `Pack of 6` |
| `weight_grams` | int | |
| `launch_date` | date | |
| `is_active` | int | 1 / 0 |

---

## 7. `pricing_history`

| column | type | description |
|---|---|---|
| `pricing_id` | int PK | |
| `product_id` | string FK | |
| `store_id` | string | empty when chain-wide |
| `effective_from` | date | |
| `effective_to` | date | empty for the currently-effective row |
| `selling_price` | float | |
| `mrp_at_time` | float | |

---

## 8. `customers`

| column | type | description |
|---|---|---|
| `customer_id` | string PK | |
| `customer_name` | string | |
| `email` | string | |
| `phone` | string | |
| `gender` | string | F / M / O |
| `age_band` | string | 18-24, 25-34, … |
| `home_region_id` | string | self-declared region |
| `signup_date` | date | |
| `is_premium_member` | int | loyalty flag |

---

## 9. `promotions`

| column | type | description |
|---|---|---|
| `promo_id` | string PK | |
| `promo_name` | string | |
| `promo_type` | string | `percent_off`, `flat_off`, `bogo`, `bundle` |
| `discount_value` | int | percent / rupees / x-for-y count, depending on type |
| `applicable_scope` | string | `SKU`, `CATEGORY`, `STORE`, `GLOBAL` |
| `scope_value` | string | the SKU / category / store id; empty for `GLOBAL` |
| `start_date` | date | |
| `end_date` | date | |
| `min_order_value` | int | 0 = no threshold |
| `max_discount` | int | 0 = no cap |

---

## 10. `inventory_snapshots`

| column | type | description |
|---|---|---|
| `store_id` | string FK | |
| `product_id` | string FK | |
| `snapshot_date` | date | |
| `on_hand_units` | int | |
| `is_in_stock` | int | 1 / 0 |
| `is_store_closed` | int | 1 / 0 |
| `days_since_last_replenishment` | int | |

---

## 11. `orders`

| column | type | description |
|---|---|---|
| `order_id` | string PK | |
| `customer_id` | string FK | |
| `store_id` | string FK | the fulfilling store |
| `order_timestamp` | datetime | |
| `order_date` | date | |
| `order_status` | string | `completed`, `cancelled` |
| `channel` | string | `in_store`, `online`, `app`, `phone` |
| `payment_method` | string | UPI / CARD / CASH / WALLET / COD |
| `subtotal` | float | |
| `discount_total` | float | |
| `tax` | float | |
| `total_amount` | float | |
| `num_items` | int | |

---

## 12. `order_items`

| column | type | description |
|---|---|---|
| `order_item_id` | string PK | |
| `order_id` | string FK | |
| `product_id` | string FK | |
| `store_id` | string FK | |
| `quantity` | int | |
| `unit_price` | float | transacted price |
| `mrp_at_time` | float | |
| `line_discount` | float | item-level discount applied |
| `line_total` | float | the realised line value (after discount, before tax) |
| `is_cancelled` | int | 1 / 0 |
| `promo_id_applied` | string | empty when no promo applied |

---

## 13. `returns`

| column | type | description |
|---|---|---|
| `return_id` | string PK | |
| `order_id` | string FK | |
| `order_item_id` | string FK | |
| `quantity_returned` | int | |
| `refund_amount` | float | |
| `return_reason` | string | damaged / wrong_item / quality / not_as_described / size_mismatch / changed_mind |
| `refund_status` | string | refunded / pending / rejected |
| `return_offset_days` | int | days after the order date the return was filed |
