import functools
import logging
import datetime

# Configure logging
logging.basicConfig(filename='match_players.log', level=logging.INFO)

def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Log the function call with timestamp
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"[{timestamp}] Function {func.__name__} called with args: {args}, kwargs: {kwargs}")

        # Call the original function
        result = func(*args, **kwargs)

        # Log additional information if needed
        logging.info(f"[{timestamp}] Function {func.__name__} completed with result: {result}")

        return result

    return wrapper