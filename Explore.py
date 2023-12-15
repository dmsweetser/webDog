# This solution requires Python 3.9.7 to run

import psutil
import os
import time
import random
import numpy as np
import gym
import sys
from llama_cpp import Llama
import urllib.parse
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import ElementNotInteractableException  # Add this import
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

file_url = "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/blob/main/mistral-7b-instruct-v0.2.Q2_K.gguf"
file_name = "mistral-7b-instruct-v0.2.Q2_K.gguf"

# Check if the file already exists
if not os.path.exists(file_name):
    # If not, download the file
    response = requests.get(file_url)
    with open(file_name, "wb") as file:
        file.write(response.content)
    print(f"{file_name} downloaded successfully.")
else:
    print(f"{file_name} already exists in the current directory.")

model_name = file_name

# Define llama.cpp parameters
llama_params = {
    "loader": "llama.cpp",
    "cpu": False,
    "threads": 0,
    "threads_batch": 0,
    "n_batch": 512,
    "no_mmap": False,
    "mlock": True,
    "no_mul_mat_q": False,
    "n_gpu_layers": 0,
    "tensor_split": "",
    "n_ctx": 16384,
    "compress_pos_emb": 1,
    "alpha_value": 1,
    "rope_freq_base": 0,
    "numa": False,
    "model": model_name,
    "temperature": 1.0,
    "top_p": 0.99,
    "top_k": 85,
    "repetition_penalty": 1.01,
    "typical_p": 0.68,
    "tfs": 0.68
}

llama = Llama(model_name, **llama_params)

# Function to terminate chromedriver.exe processes
def terminate_chromedriver_processes():
    for process in psutil.process_iter(['pid', 'name']):
        if 'chromedriver.exe' in process.info['name']:
            try:
                print(f"Terminating existing chromedriver.exe process (PID: {process.info['pid']})")
                psutil.Process(process.info['pid']).terminate()
            except Exception as e:
                print(f"Failed to terminate process (PID: {process.info['pid']}), error: {e}")

# Terminate existing chromedriver.exe processes before starting
terminate_chromedriver_processes()

# Accept the web application URL as user input
web_app_url = input("Enter the web application URL: ")

# Define the available actions, including "select_option" and "enter_date"
actions = ["click", "input_text", "scroll", "select_option", "enter_date"]
num_actions = len(actions)

# Both of these parameters can be increased to allow more thorough testing
# Define the maximum number of episodes (testing sessions)
max_episodes = 100
# Define the maximum number of steps per episode
max_steps = 10000

# Create a subfolder for generated scripts
subfolder = "./generated-scripts"
if not os.path.exists(subfolder):
    os.makedirs(subfolder)

# Define the path to the /models directory
model_dir = "./models"

# Ensure the /models directory exists
if not os.path.exists(model_dir):
    os.makedirs(model_dir)

# Function to get the domain from a URL
def get_domain(url):
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    return parsed_url.netloc

# New function to generate a more robust XPATH with unique attributes or identifiers
def get_robust_xpath(element):
    """
    Get a more robust XPath of a WebElement using unique attributes or identifiers.
    """
    element_id = element.get_attribute("id")
    if element_id:
        return f'//*[@id="{element_id}"]'

    element_name = element.get_attribute("name")
    if element_name:
        return f'//*[@name="{element_name}"]'

    element_value = element.get_attribute("value")
    if element_value:
        return f'//*[contains(@value, "{element_value}")]'

    element_text = element.text
    if element_text:
        return f'//*[contains(text(), "{element_text}")]'

    # If no unique attributes are found, revert to a more general approach
    element_xpath = element.get_attribute("xpath")
    if not element_xpath:
        element_xpath = ""
    else:
        element_xpath += "/"
    element_xpath += f"{element.tag_name}"
    return element_xpath

# Initialize the Selenium WebDriver
chrome_driver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
chrome_service = ChromeService(executable_path=chrome_driver_path)
chrome_service.start()
capabilities = DesiredCapabilities.CHROME
capabilities['goog:loggingPrefs'] = {'browser': 'ALL'}
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Run headless for faster testing
chrome_options.add_argument("--disable-infobars")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--remote-debugging-port=9155")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--disable-logging")  # Disable logging to console
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)

# Custom Gym environment for the web application
class WebAppEnv(gym.Env):
    def __init__(self, driver):
        super(WebAppEnv, self).__init__()
        self.action_space = gym.spaces.Discrete(num_actions)
        self.observation_space = gym.spaces.Box(low=0, high=1, shape=(max_steps,))  # Adjust the observation space accordingly
        
        self.state = 0  # Initial state
        self.current_step = 0
        self.driver = driver
        self.actions_sequence = []
        self.uft_actions_sequence = []
        self.original_domain = get_domain(web_app_url)

        # Initialize the environment by navigating to the original URL
        self.driver.get(web_app_url)
        self.actions_sequence.append(f'driver.get("{web_app_url}")')
        self.uft_actions_sequence.append(f'Browser("browser_name").Navigate {web_app_url}')

    def reset(self):
        self.state = 0
        self.current_step = 0
        self.driver.get(web_app_url)
        self.actions_sequence = [f'driver.get("{web_app_url}")']  # Reset actions sequence with the initial navigation
        self.uft_actions_sequence = [f'Browser("browser_name").Navigate {web_app_url}']
        return self.state

    def handle_interactable_exception(self, action, valid_elements):
        try:
            element_to_interact = random.choice(valid_elements)
            element_xpath = get_robust_xpath(element_to_interact)
            action_str = f'driver.find_element(By.XPATH, \'{element_xpath}\').{actions[action]}()'
            uft_action_str = f'Browser("browser_name").Page("page_name").WebButton("xpath=\'{element_xpath}\'").{actions[action]}'
            if action_str != self.actions_sequence[-1]:
                getattr(element_to_interact, actions[action])()
                self.actions_sequence.append(action_str)
                self.uft_actions_sequence.append(uft_action_str)
                
        except ElementNotInteractableException:
            # Handle ElementNotInteractableException by recursively calling the method
            valid_elements.remove(element_to_interact)
            if valid_elements:
                self.handle_interactable_exception(action, valid_elements)
            else:
                print(f"All elements are not interactable for action: {actions[action]}")

    def check_for_errors(self):
        logs = self.driver.get_log('browser')
        for log in logs:
            if log['level'] in ('SEVERE', 'ERROR'):
                print(f"[{log['level']}] - {log['message']}")
                return True

        # Check for unhandled exceptions on the page
        stack_trace_elements = self.driver.find_elements(By.XPATH, '//*[contains(text(), "unhandled exception")]')
        if stack_trace_elements:
            return True  # Indicate that an unhandled exception occurred on the page

        return False  # No errors were found

    def step(self, action):
        if self.current_step >= max_steps:
            self.log_actions()  # Log actions even if max steps are reached
            return self.state, 0, True, {}  # End of episode

        try:
            # Check if the current domain is different from the original domain
            current_domain = get_domain(self.driver.current_url)
            if current_domain != self.original_domain:
                self.driver.get(web_app_url)  # Navigate back to the original URL
                self.actions_sequence.append(f'driver.get("{web_app_url}")')
                self.uft_actions_sequence.append(f'Browser("browser_name").Navigate {web_app_url}')

                self.current_step += 1  # Increment the step count
                return self.state, 0, False, {}
            else:
                # Perform the selected action
                previous_action = self.actions_sequence[-1] if self.actions_sequence else None

                if action == 0:  # Click
                    # Find clickable elements using CSS selectors
                    clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a, button')
                    valid_clickable_elements = [element for element in clickable_elements if element.is_displayed() and element.is_enabled()]

                    if valid_clickable_elements:
                        try:
                            element_to_click = random.choice(valid_clickable_elements)
                            element_xpath = get_robust_xpath(element_to_click)
                            action_str = f'driver.find_element(By.XPATH, \'{element_xpath}\').click()'
                            uft_action_str = f'Browser("browser_name").Page("page_name").WebButton("xpath=\'{element_xpath}\'").Click'
                            if action_str != previous_action:
                                element_to_click.click()
                                self.actions_sequence.append(action_str)
                                self.uft_actions_sequence.append(uft_action_str)
                        except ElementNotInteractableException:
                            self.handle_interactable_exception(action, valid_clickable_elements)

                # Implement the rest of the actions...
                elif action == 1:  # Input Text
                    # Find input fields using CSS selectors
                    input_elements = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="password"], input[type="email"]')
                    valid_input_elements = [element for element in input_elements if element.is_displayed() and element.is_enabled()]

                    if valid_input_elements:
                        element_to_input = random.choice(valid_input_elements)
                        
                        # Get outerHTML of the element
                        outer_html = element_to_input.get_attribute("outerHTML")
                        print("Outer HTML of the element: " + outer_html)
                        
                        messages = [{"role": "system", "content": "What is a valid sample value I could use for this HTML input element? You must respond ONLY with a valid sample value AND NOTHING ELSE: " + outer_html}]
                        response = llama.create_chat_completion(messages=messages)
                        random_text = response['choices'][0]['message']['content'].strip()
                        if random_text.startswith('"') and random_text.endswith('"'):
                            random_text = random_text[1:-1]
                        print("Sample input text provided by LLM: " + random_text)

                        element_xpath = get_robust_xpath(element_to_input)
                        action_str = f'driver.find_element(By.XPATH, \'{element_xpath}\').send_keys("{random_text}")'
                        uft_action_str = f'Browser("browser_name").Page("page_name").WebEdit("xpath=\'{element_xpath}\'").Set "{random_text}"'
                        if action_str != previous_action:
                            element_to_input.send_keys(random_text)
                            self.actions_sequence.append(action_str)
                            self.uft_actions_sequence.append(uft_action_str)

                elif action == 2:  # Scroll
                    # Scroll the page (you can change the scroll amount)
                    scroll_amount = random.randint(1, 3) * 200  # You can adjust the scroll amount as needed
                    action_str = f'driver.execute_script("window.scrollBy(0, {scroll_amount});")'
                    uft_action_str = f'Browser("browser_name").Page("page_name").Object.parentWindow.scrollBy 0, {scroll_amount}'
                    if action_str != previous_action:
                        self.driver.execute_script(action_str)
                        self.actions_sequence.append(action_str)
                        self.uft_actions_sequence.append(uft_action_str)

                elif action == 3:  # Select Option
                    # Find select elements using CSS selectors
                    select_elements = self.driver.find_elements(By.CSS_SELECTOR, 'select')
                    valid_select_elements = [element for element in select_elements if element.is_displayed() and element.is_enabled()]

                    if valid_select_elements:
                        element_to_select = random.choice(valid_select_elements)
                        select = Select(element_to_select)
                        options = select.options
                        if options:
                            random_option = random.choice(options)
                            element_xpath = get_robust_xpath(element_to_select)
                            action_str = f'element = driver.find_element(By.XPATH, \'{element_xpath}\'); Select(element).select_by_value("{random_option.get_attribute("value")}")'
                            uft_action_str = f'Browser("browser_name").Page("page_name").WebList("xpath=\'{element_xpath}\'").Select "{random_option.get_attribute("value")}"'
                            if action_str != previous_action:
                                select.select_by_value(random_option.get_attribute("value"))
                                self.actions_sequence.append(action_str)
                                self.uft_actions_sequence.append(uft_action_str)

                elif action == 4:  # Enter Date
                    # Find date input fields using CSS selectors
                    date_input_elements = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="date"]')
                    valid_date_input_elements = [element for element in date_input_elements if element.is_displayed() and element.is_enabled()]

                    if valid_date_input_elements:
                        element_to_input = random.choice(valid_date_input_elements)
                        
                        # Get outerHTML of the element
                        outer_html = element_to_input.get_attribute("outerHTML")
                        print("Outer HTML of the element: " + outer_html)
                        
                        messages = [{"role": "system", "content": "What is a valid sample date I could use for this HTML input element? ONLY RESPOND with the valid sample value: " + outer_html}]
                        response = llama.create_chat_completion(messages=messages)
                        random_date = response['choices'][0]['message']['content'].strip()
                        if random_date.startswith('"') and random_date.endswith('"'):
                            random_date = random_date[1:-1]
                        print("Sample date provided by LLM: " + random_date)
                        
                        element_xpath = get_robust_xpath(element_to_input)
                        action_str = f'driver.find_element(By.XPATH, \'{element_xpath}\').send_keys("{random_date}")'
                        uft_action_str = f'Browser("browser_name").Page("page_name").WebEdit("xpath=\'{element_xpath}\'").Set "{random_date}"'
                        if action_str != previous_action:
                            element_to_input.send_keys(random_date)
                            self.actions_sequence.append(action_str)
                            self.uft_actions_sequence.append(uft_action_str)

            # Check for unexpected alerts
            try:
                alert = self.driver.switch_to.alert

                if random.choice([True, False]):  # Randomly accept or dismiss
                    alert.accept()  # Accept the alert (click OK)
                    self.actions_sequence.append('alert.accept()')
                    self.uft_actions_sequence.append('Browser("browser_name").Page("page_name").Dialog("micClass:=Dialog").Close micOk')
                else:
                    alert.dismiss()  # Dismiss the alert (click Cancel)
                    self.actions_sequence.append('alert.dismiss()')
                    self.uft_actions_sequence.append('Browser("browser_name").Page("page_name").Dialog("micClass:=Dialog").Close micCancel')

            except Exception:
                pass  # No alert found


        except Exception as e:
            pass  # Continue to the next action

        # Check for JavaScript errors in the console logs
        if self.check_for_errors():
            self.log_errors()
            self.log_actions()  # Log actions when an error is encountered
            reward = self.current_step + 1  # Reward increases with each step to maximize steps
            return self.state, reward, True, {}  # End of episode

        self.current_step += 1
        self.state = self.current_step
        return self.state, 0, False, {}

    def render(self):
        pass

    def close(self):
        self.driver.quit()

    def log_errors(self):
        current_url = self.driver.current_url
        current_time = time.strftime("%Y%m%d%H%M%S")
        sanitized_url = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in current_url)

        # Capture screenshot of the page
        screenshot_file = os.path.join(subfolder, f"Error_{current_time}.png")
        self.driver.save_screenshot(screenshot_file)
        print(f"Screenshot saved as {screenshot_file}")

        # Redirect the script output to the error log file
        error_log_file = os.path.join(subfolder, f"Error_{current_time}.log")
        with open(error_log_file, "w") as log_file:
            original_stdout = sys.stdout
            sys.stdout = log_file  # Redirect output to the log file

            # Print captured console logs to the log file
            console_logs = self.driver.get_log("browser")
            for log in console_logs:
                print(f"[{log['level']}] - {log['message']}")

            sys.stdout = original_stdout  # Restore the original stdout

        print(f"Error log saved as {error_log_file}")

    def log_actions(self):
        current_url = self.driver.current_url
        current_time = time.strftime("%Y%m%d%H%M%S")
        sanitized_url = "".join(c if c.isalnum() or c in ['.', '-', '_'] else '_' for c in current_url)

        try:
            # Save generated Selenium steps script
            if self.actions_sequence:
                selenium_steps_file = os.path.join(subfolder, f"Steps_{current_time}.py")

                with open(selenium_steps_file, "w") as actions_file:
                    for action in self.actions_sequence:
                        actions_file.write(f"{action}\n")

                print(f"Generated Selenium steps saved as {selenium_steps_file}")
                
                uft_steps_file = os.path.join(subfolder, f"UFT_Steps_{current_time}.vb")

                with open(uft_steps_file, "w") as uft_actions_file:
                    for action in self.uft_actions_sequence:
                        uft_actions_file.write(f"{action}\n")

                print(f"Generated UFT steps saved as {uft_steps_file}")
        except Exception as e:
            print(f"Exception encountered while saving actions: {e}")

try:
    # Define the model path
    model_path = os.path.join(model_dir, "ppo_web_app_model.zip")

    # Create or load the model
    env = DummyVecEnv([lambda: WebAppEnv(driver)])
    if os.path.exists(model_path):
        # Load the pre-trained reinforcement learning model
        model = PPO.load(model_path)
    else:
        model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./ppo_web_app_tensorboard/")

    print(f"Training the model")
    # Train a Proximal Policy Optimization (PPO) agent
    model.learn(total_timesteps=max_episodes * max_steps)

    print(f"Saving the model")
    # Save the trained model
    model.save(model_path)
       
    # Test the trained agent
    for episode in range(max_episodes):
        print(f"Episode {episode + 1}/{max_episodes}")
        obs = env.reset()
        total_reward = 0

        for step in range(max_steps):
            action, _ = model.predict(obs)
            obs, reward, done, _ = env.step(action)
            total_reward += reward

            if done:
                print(f"Total Reward: {total_reward}")
                break  # Add this line to exit the episode loop when done

        if episode + 1 == max_episodes:
            break  # Add this line to exit the episode loop when max_episodes is reached

    # Close the environment
    env.close()
except Exception as e:
    print(f"Exception encountered: {e}")
    terminate_chromedriver_processes()
