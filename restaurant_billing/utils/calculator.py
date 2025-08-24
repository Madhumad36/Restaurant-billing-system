 
from datetime import datetime

# Coupon codes dictionary
COUPON_CODES = {
    "welcome20": 20,   # First-time customer only
    "festive10": 10,
    "newyear9": 9,
    "maincourse5": 5,
    "combodesserts3": 3
}

def is_first_time_customer(phone):
    # Placeholder logic 
    if phone and phone[-1].isdigit():
        return int(phone[-1]) % 2 == 0
    return False

def get_discount_percent(items, subtotal, payment_method, customer_phone, coupon_code):
    if subtotal > 2000:
        base_discount = 5
    elif subtotal > 1500:
        base_discount = 4
    elif subtotal > 1000:
        base_discount = 2
    else:
        base_discount = 0

    loyalty_discount = 2 if is_first_time_customer(customer_phone) else 0
    payment_discount = 2 if payment_method.lower() in ["upi", "card"] else 0

    dessert_count = sum(i['qty'] for i in items if i.get('category','').lower() == 'dessert')
    main_course_count = sum(i['qty'] for i in items if i.get('category','').lower() == 'main course')

    combo_discount = 0
    if dessert_count >= 3:
        combo_discount += 3
    if main_course_count >= 3:
        combo_discount += 5

    coupon_discount = COUPON_CODES.get(coupon_code.lower(), 0) if coupon_code else 0
    if coupon_code and coupon_code.lower() == "welcome50" and not is_first_time_customer(customer_phone):
        coupon_discount = 0

    total_discount = base_discount + loyalty_discount + payment_discount + combo_discount + coupon_discount
    return min(total_discount, 30)

def calculate_gst(items, discount_percent):
    total_gst = 0
    for item in items:
        discounted_price = item['price'] * (1 - discount_percent / 100)
        rate = 12 if item.get('category','').lower() == 'main course' else 5
        gst_item = discounted_price * item['qty'] * rate / 100
        total_gst += gst_item
    return total_gst

def calc_totals(order_items, discount_percent=0):
    subtotal = 0
    for item in order_items:
        subtotal += item['price'] * item['qty']

    discount_amount = subtotal * discount_percent / 100
    subtotal_after_discount = subtotal - discount_amount

    gst_val = calculate_gst(order_items, discount_percent)

    total = subtotal_after_discount + gst_val
    return subtotal, gst_val, total, discount_amount

def format_bill_text(order_items, subtotal, gst_total, total, discount_percent, discount_amount):
    lines = []
    lines.append("Item\tQty\tPrice\tGST(%)")
    for it in order_items:
        lines.append(f"{it['name']}\t{it['qty']}\t₹{it['price']}\t{it.get('gst', 0)}")
    lines.append("-" * 32)
    lines.append(f"Subtotal:\t\t₹{subtotal:.2f}")
    lines.append(f"Discount ({discount_percent}%):\t-₹{discount_amount:.2f}")
    lines.append(f"Subtotal after Discount:\t₹{subtotal - discount_amount:.2f}")
    lines.append(f"GST:\t\t\t₹{gst_total:.2f}")
    lines.append(f"Total:\t\t\t₹{total:.2f}")
    return '\n'.join(lines)
