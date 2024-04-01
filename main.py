import re
import cv2
import pytesseract as pyt
from paddleocr import PaddleOCR
from datetime import datetime
import pymysql.cursors

# Initialises the OCR model from PaddleOCR with English language support and angle classification enabled
ocr = PaddleOCR(use_angle_cls=True, lang='en')


def format_date(date_str):
    """
    Formats a date string from DD-MM-YYYY to YYYY-MM-DD.

    Parameters:
        date_str (str): A date string in the format DD-MM-YYYY.

    Returns:
        str: The formatted date string in the format YYYY-MM-DD.
    """
    date_obj = datetime.strptime(date_str, '%d-%m-%Y')
    formatted_date = date_obj.strftime('%Y-%m-%d')
    return formatted_date



def insert_cheque_details(connection, cursor, *data):
    """
    Inserts cheque details into the MySQL database.

    Parameters:
        connection (pymysql.Connection): Connection object to the MySQL database.
        cursor (pymysql.cursors.Cursor): Cursor object for executing SQL queries.
        *data (tuple): Tuple containing the cheque details.

    Raises:
        Exception: If an error occurs during database insertion.

    Returns:
        None
    """
    try:
        data = list(data) 
        data[1] = format_date(data[1])
        print(f'The date is {data[1]}')
        data = tuple(data)  
        sql = """INSERT INTO cheque_details (cheque_number, cheque_date, account_type, 
                 account_number, payer_name, payee_name, amount_in_words, ifsc, 
                 amount_in_numbers, scanned_cheque_image) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        cursor.execute(sql, data)
        connection.commit()
        print("Data inserted successfully!")

    except Exception as e:
        connection.rollback()
        raise e


def validate_date(cheque_date):
    """
    Validates a cheque date.

    Parameters:
        cheque_date (str): A date string in the format DD-MM-YYYY.

    Raises:
        ValueError: If the date format is invalid, future date, older than 3 months, or February date is invalid.
    """
    cheque_date_obj = datetime.strptime(cheque_date, '%d-%m-%Y')
    current_date = datetime.now()

    if len(cheque_date) != 10:
        raise ValueError("Invalid date format. Date should be in DD-MM-YYYY format.")

    if cheque_date_obj > current_date:
        raise ValueError("Date cannot be a future date.")

    if (current_date - cheque_date_obj).days > 90:
        raise ValueError("Date should not be more than three months old.")

    if cheque_date_obj.month == 2:  # February
        if cheque_date_obj.year % 4 == 0:  # Leap year
            if cheque_date_obj.day > 29:
                raise ValueError("Invalid date. February in a leap year cannot have a date greater than 29.")
        else:
            if cheque_date_obj.day > 28:
                raise ValueError("Invalid date. February cannot have a date greater than 28.")
    elif cheque_date_obj.month in [4, 6, 9, 11]:  # Months with 30 days
        if cheque_date_obj.day > 30:
            raise ValueError("Invalid date. This month cannot have a date greater than 30.")


def numbers_to_words(number):
    """
    Converts a number to its equivalent words.

    Parameters:
        number (int): The number to be converted.

    Returns:
        str: The number converted to words.
    """
    ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', \
            'eight', 'nine']
    tens = ['', 'ten', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', \
            'seventy', 'eighty', 'ninety']
    teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', \
             'sixteen', 'seventeen', 'eighteen', 'nineteen']

    words = ''

    if number == 0:
        return 'zero'

    if number >= 10000000:
        words += numbers_to_words(number // 10000000) + ' crore '
        number %= 10000000

    if number >= 100000:
        words += numbers_to_words(number // 100000) + ' lakh '
        number %= 100000

    if number >= 1000:
        words += numbers_to_words(number // 1000) + ' thousand '
        number %= 1000

    if number >= 100:
        words += numbers_to_words(number // 100) + ' hundred '
        number %= 100
        if number > 0:
            words += 'and '

    if number >= 20:
        words += tens[number // 10] + ' '
        number %= 10
    elif number >= 10:
        words += teens[number - 10] + ' '
        number = 0

    if number > 0:
        words += ones[number]

    return words.strip()


def extract_numbers(text):
    """
    Extracts numerical digits from a text string.

    Parameters:
        text (str): The text string from which digits are to be extracted.

    Returns:
        str: The extracted numerical digits.
    """
    numbers = re.findall(r'\d+', text)
    return ''.join(map(str, numbers))


def extract_alphabets(text):
    """
    Extracts alphabetic characters from a text string.

    Parameters:
        text (str): The text string from which alphabetic characters are to be extracted.

    Returns:
        str: The extracted alphabetic characters.
    """
    alphabets = re.findall(r'[a-zA-Z ]+', text)
    return ''.join(alphabets)


def extract_string(text):
    """
    Extracts alphanumeric characters, hyphens, slashes, parentheses, commas, periods, and spaces from a text string.

    Parameters:
        text (str): The text string from which characters are to be extracted.

    Returns:
        str: The extracted characters.
    """
    text = re.sub('[^A-Za-z0-9-/,(). ]+', '', text)
    text = text.strip()
    text = re.sub(r'\s{2,}', ' ', text)
    return text


def read_text(image):
    """
    Reads text from an image using OCR.

    Parameters:
        image (numpy.ndarray): The image from which text is to be read.

    Returns:
        str: The text extracted from the image.
    """
    try:
        result = ocr.ocr(image)
        if len(result) < 1:
            text = None
        else:
            text = ' '.join([line[1][0] for line in result[0]])
        return text
    except Exception as e:
        print(f"Error during text extraction: {str(e)}")
        return None


def clean_micr(text):
    """
    Cleans MICR text by removing non-numeric characters.

    Parameters:
        text (str): The MICR text to be cleaned.

    Returns:
        str: The cleaned MICR text containing only numeric characters.
    """
    text = re.sub('[^0-9]', '', text)
    return text


def extract_micr(region):
    """
    Extracts MICR (Magnetic Ink Character Recognition) information from a region of interest in an image.

    Parameters:
        region (numpy.ndarray): The region of interest containing MICR information.

    Returns:
        str: The extracted MICR information.
    """
    try:
        _, binary_img = cv2.threshold(region, 0, 255, \
                                      cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, \
                                       cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=lambda x: cv2.boundingRect(x)[0])
        micr_text = ""
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 5 and h > 5:
                micr_region = binary_img[y:y + h, x:x + w]
                micr_text += pyt.image_to_string(micr_region)
        cleaned_micr = clean_micr(micr_text)
        return cleaned_micr

    except Exception as e:
        print(f"Error during MICR extraction: {str(e)}")
        return None


def process_image(img):
    """
    Processes an image by resizing it and converting it to grayscale.

    Parameters:
        img (numpy.ndarray): The input image to be processed.

    Returns:
        numpy.ndarray: The processed grayscale image.
    """
    img = cv2.resize(img, (1000, 411), interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    return img


if __name__ == '__main__':
    """
    Main function for processing scanned cheques and inserting details into a MySQL database.

    This function performs the following steps:
    1. Establishes a connection to the MySQL database.
    2. Reads the scanned cheque image and processes it.
    3. Extracts various fields from the processed image such as cheque date, IFSC code, account type, etc.
    4. Validates the extracted cheque date to ensure it is in the correct format, not a future date, and not older than three months.
    5. Validates the IFSC code to ensure it has exactly 11 characters.
    6. Validates the account number to ensure it has exactly 12 digits for regular savings accounts.
    7. Reads the text amount on the cheque and converts it to a numeric amount.
    8. Converts the numeric amount to words and compares it with the extracted amount in words to ensure consistency.
    9. Extracts MICR information using the PyTesseract algorithm from the cheque image.
    10. Inserts the extracted details into the MySQL database table 'cheque_details'.
    11. Handles any unexpected errors that may occur during the process and closes the database connection.

    Parameters:
        None

    Returns:
        None
    """


    connection = pymysql.connect(host='127.0.0.1',
                                 user='root',
                                 password='',
                                 db='digicheque',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            scanned_cheque = cv2.imread("H:\\My Drive\\namma_a_eye\\ocr_r_and_d_003.jpg")
            img = process_image(scanned_cheque)

            cheque_date_img = img[30:55, 720:970]
            cv2.imshow("image", cheque_date_img)
            extracted_text = read_text(cheque_date_img)
            cheque_date = extract_numbers(extracted_text)
            print("Date:", cheque_date)
            validate_date(cheque_date)
            formatted_cheque_date = format_date(cheque_date)

            ifsc_segmented_img = img[45:70, 180:320]
            cv2.imshow("image", ifsc_segmented_img)
            extracted_text = read_text(ifsc_segmented_img)
            ifsc = extract_string(extracted_text)[4:]
            if len(ifsc) != 11:
                raise ValueError("IFSC should be exactly 11 characters long.")
            print("IFSC of the Payer's Bank:", ifsc)

            account_type_img = img[200:230, 360:480]
            cv2.imshow("image", account_type_img)
            extracted_text = read_text(account_type_img)
            account_type = extract_alphabets(extracted_text)
            print("Account Type:", account_type)

            acc_num_segmented_img = img[200:230, 95:300]
            cv2.imshow("image", acc_num_segmented_img)
            extracted_text = read_text(acc_num_segmented_img)
            account_number = extract_numbers(extracted_text)
            if len(account_number) != 12 and account_type.lower() == "regular savings":
                raise ValueError("Account number should be exactly 12 digits for \
            regular savings accounts.")
            print("Account Number:", account_number)

            payer_name_segmented_img = img[270:300, 700:1000]
            cv2.imshow("image", payer_name_segmented_img)
            extracted_text = read_text(payer_name_segmented_img)
            payer_name = extract_alphabets(extracted_text)
            print("Cheque Payer's Name:", payer_name)

            payee_name_img = img[70:125, 6:775]
            cv2.imshow("image", payee_name_img)
            extracted_text = read_text(payee_name_img)
            payee_name = extract_alphabets(extracted_text)[3:]
            print("Cheque Receiver's / Payee's Name:", payee_name)

            amount_in_words_img = img[120:190, 145:780]
            cv2.imshow("image", amount_in_words_img)
            extracted_text = read_text(amount_in_words_img)
            amount_in_words = extract_alphabets(extracted_text)
            print("Amount in Words:", amount_in_words)

            amount_in_numbers_img = img[130:195, 750:940]
            cv2.imshow("image", amount_in_numbers_img)
            extracted_text = read_text(amount_in_numbers_img)
            amount_in_numbers = int(extract_numbers(extracted_text))
            print(f'Amount in Numbers is {amount_in_numbers}')

            words = numbers_to_words(amount_in_numbers)
            print(f"Captured words is {words}")
            print(f"Amount in words is {amount_in_words}")
            if words.lower() != amount_in_words.lower():
                raise ValueError('Extracted amount in words and amount in numbers did not match')

            micr_region = img[360:390, 220:390]
            cv2.imshow("image", micr_region)
            micr_info = extract_micr(micr_region)
            if len(micr_info) != 6:
                raise ValueError("Cheque number should be exactly 6 digits long.")
            print("Cheque Number:", micr_info)


            data = (
                int(micr_info),
                formatted_cheque_date,
                account_type,
                account_number,
                payer_name,
                payee_name,
                amount_in_words,
                ifsc,
                amount_in_numbers,
                scanned_cheque
            )

            insert_cheque_details(connection, cursor, *data)

    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
    finally:
        connection.close()
