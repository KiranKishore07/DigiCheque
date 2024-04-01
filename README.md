# DigiCheque
This Python script is designed to extract, validate and process information from scanned cheque images. It utilizes AI algorithms such as PaddleOCR and PyTesseract for text extraction, along with image processing techniques. The extracted information undergoes various checks and balances to ensure accuracy before being inserted into a MySQL database table. The script offers an end-to-end solution for digitizing cheque data efficiently.

## Features

- Extracts text from scanned cheque images using PaddleOCR.
- Validates cheque details such as date, IFSC code, and account number.
- Converts cheque amount from numeric to words and verifies consistency.
- Inserts validated cheque details into a MySQL database table.
- Handles errors gracefully and closes database connections securely.

## Requirements

- Python 3.x
- PaddleOCR
- OpenCV
- PyTesseract
- pymysql

## Usage

1. Clone the repository to your local machine.
2. Install the required dependencies using `pip install -r requirements.txt`.
3. Ensure that you have a MySQL server set up with appropriate credentials.
4. Update the database connection details in the script.
5. Place your scanned cheque images in the specified directory.
6. Run the script using `python main.py`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- OpenCV: https://github.com/opencv/opencv
- PyTesseract: https://github.com/madmaze/pytesseract

