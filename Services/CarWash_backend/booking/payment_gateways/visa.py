def initiate_visa_payment(booking):
    return {
        "status": "success",
        "message": "Visa payment initiated (mocked)",
        "reference": f"VISA{booking.id}XYZ"
    }
