# Restaurant Billing System (Streamlit Web)

A web-based restaurant billing system built with Streamlit. It enables managing orders, customers, billing, and sales analytics through an intuitive interface.

---

## Features

- **Secure Role-Based Login** Secured login page created for safe access to Manager, Admin and Cashier roles. 
  
- **User-Friendly Modern Web UI**: Clean and intuitive Streamlit interface with sidebar navigation for easy access to Billing, Analytics Dashboard, and Order History sections.
- **Billing Page**  
  - Select menu items, adjust quantities, and add to order  
  - Input customer details and apply coupon codes for discounts  
  - Preview detailed bill with GST and discount breakdown  
  - Finalize and save orders to database  
  - Print and share bills via Email and WhatsApp directly in the app
- **Analytics Dashboard** (Additional)  
  - Visualize top-selling items and revenue by payment method  
  - View revenue trends over selectable time periods  
  - Helps management monitor business performance with insightful charts
- **Order History**  
  - View past orders with detailed information  
  - Export sales reports as CSV files  
  - Quickly search and filter previous transactions for easy access



## Setup & Run

1. Install main requirements:  
     **pip install streamlit pandas**
   
2. Run the app:  
      **streamlit run main_ui.py**

   *(or if you are using advanced python version, you can try this out)*

   **python3 streamlit run main_ui.py**

---


## Login Credentials (for demo)  

| Role    | Username  | Password    |
|---------|-----------|-------------|
| Manager | manager   | manager1234 |
| Admin   | admin     | admin5678   |
| Cashier | cashier   | cashier000  |

---

## Notes

- Core billing and order history pages provide essential POS(Point of Sale) features.
- Analytics and user login are additional features to enhance management control and usability.
