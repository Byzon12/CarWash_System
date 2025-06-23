def initiate_paypal_payment(booking):
    return {
        "status": "redirect",
        "redirect_url": "https://www.sandbox.paypal.com/checkoutnow?token=EXAMPLE123"
    }
