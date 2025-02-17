import qrcode
from io import BytesIO

def test_qr():
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        qr.add_data("Test QR Code")
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save("test_qr.png")
        print("QR code test successful!")
        
    except Exception as e:
        print(f"Error testing QR code: {str(e)}")

if __name__ == "__main__":
    test_qr() 