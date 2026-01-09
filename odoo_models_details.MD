Core 6 models:

Prefix	Key Models (The Real Tables)	What it Answers (User Intent)
res	res.partner	"Who?" (Customers, Vendors, Users). All contacts live here.
product	product.template, product.product	"What?" (Items, Services). Pricing and descriptions.
sale	sale.order, sale.order.line	"Income" (Quotations, Sales Orders). Customer demand.
purchase	purchase.order, purchase.order.line	"Spending" (RFQs, POs). Buying from vendors.
account	account.move (Invoices/Bills)	"Money" (Invoices, Bills, Payments). The financial truth.
stock	stock.quant (Current Levels), stock.picking (Transfers)	"Inventory" (On hand quantity, Delivery status).


