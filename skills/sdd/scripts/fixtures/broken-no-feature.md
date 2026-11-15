# Order Desk
feature: A small shop system that takes customer orders and gets them packed and sent.

## Take the order
id: take-order
feature: A customer picks products and pays, and the shop gets an order to work on.
related: stock
value: Nothing else starts without it; it turns a wish into work the shop can do. — diary: first shop design

The order is only accepted when what the customer wants is on the shelf and the payment went through.

### Check the stock
id: check-stock
related: stock
value: Stops the shop from selling what it cannot send.

- criteria: an item is available when the shelf count minus the reserved count is at least the amount asked (setting: reserve_minutes holds an item for 15 minutes)
- files: shop/stock.py, shop/basket.py

### Take the payment
id: take-payment
after: check-stock
feature: The customer pays; the order is created only after the payment is confirmed.
value: The shop is never left with an unpaid order.
open: whether a partly paid order should be kept is not known

#### Retry a failed payment
id: retry-payment
feature: When the bank says no, the customer may try again before the order is dropped.

- criteria: 3 tries, 10 minutes apart (setting: max_payment_tries)
- files: shop/payment.py

## Pack and send
id: pack-send
after: take-order
feature: The order is picked from the shelf, packed, labelled and handed to the carrier.
related: stock
value: Gets the goods to the customer, which is the point of the shop.

### Print the label
id: print-label
feature: A label with the address and the carrier's code is printed for the box.

- files: shop/label.py

### Hand over to the carrier
id: hand-over
after: print-label
feature: The packed box is scanned out so the carrier takes it and the customer is told it is on the way.

## Stock
id: stock
feature: The shop's record of what is on the shelf and what is promised to open orders.
value: Every other part trusts one number for what the shop has.

- criteria: counts change only when goods arrive, are reserved, or leave (setting: low_stock_alert at 5)
- files: shop/stock.py
