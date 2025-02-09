# Sepur Bot

This script automates the process of booking train tickets on the official KAI (Kereta Api Indonesia) website using Selenium.

## Features
- Automated train ticket booking.
- Passenger information autofill.
- Payment selection automation.
- Logging system for tracking the automation process.
- **Not available yet:** Seat selection and captcha bypass.

## Requirements
- Python 3.x
- Google Chrome
- ChromeDriver
- Selenium

## Installation
1. Clone this repository:
   ```sh
   git clone https://github.com/semlakune/sepur-bot.git
   cd sepur-bot
   ```
2. Install required dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Download and place the correct ChromeDriver version in the project directory.

## Configuration
Edit the `booking_data.json` file to include your booking details:

```json
{
    "origin_station": "GAMBIR",
    "destination_station": "KEBUMEN",
    "departure_month": "Mar",
    "departure_date": "12",
    "train_name": "ARGO SEMERU",
    "ticket_price": "555.000",
    "bank_name": "BANK LAINNYA",
    "order_phone": "081234567890",
    "order_address": "Jl. Example No. 123",
    "order_email": "youremail@gmail.com",
    "bypass_captcha": false,
    "select_seat": false,
    "passengers": [
        {
            "name": "Aji Purnomo",
            "id_card": "3305220101950001",
            "prefix": "MR.",
            "seat": "feature_not_available_yet"
        },
        {
            "name": "Anisa Fitri",
            "id_card": "3305220101950002",
            "prefix": "MRS.",
            "seat": "feature_not_available_yet"
        }
    ]
}
```

## Usage
1. Run the script with:
   ```sh
   python book.py
   ```
2. Follow the logs to track the booking process.
3. Complete the CAPTCHA manually after passenger(s) detail filled then click "Pesan".

## Logging
Logs are stored in `booking_sepur.log` for debugging and tracking purposes.

## Notes
- Seat selection and captcha bypass are not implemented yet.
- Ensure the ChromeDriver version matches your installed Chrome version.
- Please replace the `booking_data.json` with your own booking details carefully and ensure the format is correct.

## License
This project is licensed under the MIT License.