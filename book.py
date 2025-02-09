import logging
from dataclasses import dataclass
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
from time import sleep
import schedule
import time
from datetime import datetime
import pytz

@dataclass
class Passenger:
    name: str
    id_card: str
    prefix: str
    seat: Optional[str] = None #! seat feature is not available yet

@dataclass
class BookingConfig:
    origin_station: str
    destination_station: str
    departure_month: str
    departure_date: str
    train_name: str
    ticket_price: str
    bank_name: str
    order_phone: str
    order_address: str
    order_email: str
    bypass_captcha: bool #! captcha feature is not available yet
    select_seat: bool #! seat feature is not available yet
    schedule: dict
    passengers: List[Passenger]

class TrainBookingAutomation:
    def __init__(self, config_path: str, chromedriver_path: str, headless: bool = False):
        """
        Initialize the booking automation with configuration and webdriver setup
        
        Args:
            config_path: Path to the JSON configuration file
            chromedriver_path: Path to the ChromeDriver executable
            headless: Whether to run Chrome in headless mode
        """
        self.config = self._load_config(config_path)
        self.driver = self._setup_webdriver(chromedriver_path, headless)
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging with both file and console handlers"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('booking_sepur.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _load_config(self, config_path: str) -> BookingConfig:
        """Load and validate configuration from JSON file"""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Convert passenger dictionaries to Passenger objects
            passengers = [
                Passenger(**passenger_data)
                for passenger_data in config_data.pop('passengers')
            ]
            
            return BookingConfig(**config_data, passengers=passengers)
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")

    def _setup_webdriver(self, chromedriver_path: str, headless: bool) -> webdriver.Chrome:
        """Configure and initialize Chrome WebDriver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument(f"webdriver.chrome.driver={chromedriver_path}")
        
        return webdriver.Chrome(options=chrome_options)

    def wait_for_element(self, by: By, value: str, timeout: int = 30, clickable: bool = False):
        """
        Wait for an element to be present or clickable
        
        Args:
            by: Selenium By locator
            value: Locator value
            timeout: Maximum time to wait in seconds
            clickable: Whether to wait for element to be clickable
        """
        try:
            condition = EC.element_to_be_clickable if clickable else EC.presence_of_element_located
            return WebDriverWait(self.driver, timeout).until(condition((by, value)))
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {value}")
            raise

    def fill_input(self, by: By, value: str, text: str):
        """Fill input field with text"""
        element = self.wait_for_element(by, value)
        element.clear()  # Clear existing text first
        element.send_keys(text)
        self.logger.debug(f"Filled input {value} with {text}")

    def select_dropdown(self, by: By, value: str, option: str):
        """Select option from dropdown"""
        element = self.wait_for_element(by, value)
        Select(element).select_by_visible_text(option)
        self.logger.debug(f"Selected {option} from dropdown {value}")

    def train_book(self):
        """Handle train booking step"""
        try:
            # Origin station
            self.fill_input(By.CLASS_NAME, "origination-flexdatalist", self.config.origin_station)
            self.wait_for_element(By.XPATH, f"//span[text()='{self.config.origin_station}']").click()
            self.logger.info(f"Selected departure station: {self.config.origin_station}")
            
            # Destination station
            self.fill_input(By.CLASS_NAME, "destination-flexdatalist", self.config.destination_station)
            self.wait_for_element(By.XPATH, f"//span[text()='{self.config.destination_station}']").click()
            self.logger.info(f"Selected destination station: {self.config.destination_station}")
            
            # Date selection
            self.wait_for_element(By.ID, "departure_dateh").click()
            self.select_dropdown(By.CLASS_NAME, "ui-datepicker-month", self.config.departure_month)
            self.wait_for_element(By.XPATH, f"//a[@class='ui-state-default' and text()='{self.config.departure_date}']").click()
            
            # Set passenger count
            passenger_total = self.wait_for_element(By.NAME, "adult")
            self.driver.execute_script(
                "arguments[0].value = arguments[1];", 
                passenger_total, 
                len(self.config.passengers)
            )
            
            # Wait for scheduled time before submitting
            schedule_config = self.config.schedule
            run_date = schedule_config.get('run_date')
            run_time = schedule_config.get('run_time')
            
            if not run_date or not run_time:
                raise ValueError("Schedule configuration missing run_date or run_time")

            # Parse the scheduled date and time
            wib = pytz.timezone('Asia/Jakarta')
            scheduled_datetime = datetime.strptime(f"{run_date} {run_time}", "%Y-%m-%d %H:%M")
            scheduled_datetime = wib.localize(scheduled_datetime)
            
            # Get current time in WIB
            now = datetime.now(wib)
            
            if scheduled_datetime < now:
                self.logger.error(f"Scheduled time {scheduled_datetime} has already passed!")
                raise ValueError("Scheduled time has already passed")
                
            self.logger.info(f"Form filled. Waiting until scheduled time: {scheduled_datetime}")
            
            while True:
                now = datetime.now(wib)
                
                if now >= scheduled_datetime:
                    self.logger.info("Scheduled time reached. Submitting form...")
                    break
                    
                time_diff = scheduled_datetime - now
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.logger.info(f"Time until submission: {hours:02d}:{minutes:02d}:{seconds:02d}")
                time.sleep(1)
            
            # Submit search at scheduled time
            self.wait_for_element(By.NAME, "submit").click()
            
            # Select train
            train_xpath = (
                f"//div[contains(@class, 'name') and contains(text(), '{self.config.train_name}')]"
                "/ancestor::div[contains(@class, 'row')]"
                f"[.//div[contains(@class, 'price') and contains(text(), '{self.config.ticket_price}')]]"
                "//div[contains(@class, 'name')]"
            )
            self.wait_for_element(By.XPATH, train_xpath).click()
            self.logger.info(f"Selected train {self.config.train_name} at {self.config.ticket_price}/seat")
            
        except Exception as e:
            self.logger.error(f"Error in train booking step: {str(e)}")
            raise

    def passenger_list_step(self):
        """Handle passenger information step"""
        try:
            # Bypass login modal
            self.wait_for_element(
                By.XPATH, 
                "//button[@class='btn btn-secondary' and @data-dismiss='modal']"
            ).click()
            
            # Fill primary passenger (orderer) details
            primary = self.config.passengers[0]
            self.logger.info("Filling primary passenger details...")
            
            self.fill_input(By.ID, "pemesan_nama", primary.name)
            self.fill_input(By.ID, "pemesan_nohp", self.config.order_phone)
            self.fill_input(By.ID, "pemesan_alamat", self.config.order_address)
            self.fill_input(By.ID, "pemesan_notandapengenal", primary.id_card)
            self.fill_input(By.ID, "pemesan_email", self.config.order_email)
            
            # Copy details checkbox
            self.wait_for_element(By.ID, "cbCopy").click()
            
            # Fill additional passengers
            if len(self.config.passengers) > 1:
                self.logger.info("Filling additional passenger details...")
                for idx, passenger in enumerate(self.config.passengers[1:], start=2):
                    Select(self.wait_for_element(By.ID, f"penumpang_title{idx}")).select_by_value(passenger.prefix)
                    self.fill_input(By.ID, f"penumpang_nama{idx}", passenger.name)
                    self.fill_input(By.ID, f"penumpang_notandapengenal{idx}", passenger.id_card)
            
            # Accept terms
            self.wait_for_element(By.ID, "setuju").click()

            #! Bypass captcha
            if self.config.bypass_captcha:
                self.logger.info("Sorry, captcha bypass feature is not available yet :'<")
            
            # Wait for manual captcha and submission
            while True:
                try:
                    ok_button = self.wait_for_element(By.ID, "mSubmit", timeout=10, clickable=True)
                    ok_button.click()
                    self.logger.info("Proceeding to payment...")
                    break
                except TimeoutException:
                    self.logger.info("Waiting for manual captcha completion...")
                    sleep(2)
                    
        except Exception as e:
            self.logger.error(f"Error in passenger list step: {str(e)}")
            raise

    def choose_seat_step(self):
        """Handle seat selection step"""
        try:
            #! Select seat
            if self.config.select_seat:
                self.logger.info("Sorry, select seat feature is not available yet :'<")

            # continue to payment
            self.wait_for_element(By.ID, "mSubmit", timeout=20).click()
            self.logger.info("Proceeding to payment...")
            
        except Exception as e:
            self.logger.error(f"Error in seat selection: {str(e)}")
            raise

    def payment_step(self):
        """Handle payment selection step"""
        try:
            # Select bank
            bank = self.wait_for_element(
                By.XPATH, 
                f"//a[@class='accordion-toggle']/img[@alt='{self.config.bank_name}']", 
                timeout=20
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", bank)
            bank.click()
            
            # Click payment button
            payment_button = self.wait_for_element(
                By.XPATH,
                f"//input[@class='btn btn-primary' and @type='submit' and @value='Bayar dengan {self.config.bank_name}']",
                timeout=20
            )
            self.driver.execute_script("arguments[0].scrollIntoView();", payment_button)
            payment_button.click()
            self.logger.info(f"Selected payment method: {self.config.bank_name}")
            
        except Exception as e:
            self.logger.error(f"Error in payment step: {str(e)}")
            raise

    def run(self):
        """Execute the complete booking process"""
        self.logger.info("Starting train booking automation...")
        try:
            self.driver.get("https://booking.kai.id/")
            self.logger.info(f"Accessed booking site: {self.driver.title}")
            
            self.train_book()
            sleep(1)
            self.passenger_list_step()
            sleep(1)
            self.choose_seat_step()
            sleep(1)
            self.payment_step()
            
            input("\nPress Enter to close the browser...")
            
        except Exception as e:
            self.logger.error(f"Automation failed: {str(e)}")
            raise
        finally:
            self.driver.quit()
            self.logger.info("Browser closed. Automation complete.")

if __name__ == "__main__":
    CONFIG_PATH = "booking_data.json"
    CHROMEDRIVER_PATH = ""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('booking_sepur.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    try:
        automation = TrainBookingAutomation(
            config_path=CONFIG_PATH,
            chromedriver_path=CHROMEDRIVER_PATH,
            headless=False
        )
        automation.run()
    except Exception as e:
        logger.error(f"Failed to run automation: {str(e)}")
        raise