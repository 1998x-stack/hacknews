import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '..'))

import time
from functools import wraps

### 重试装饰器 ###
class EmptyContentError(Exception):
    """Custom exception raised when the content is empty or None."""
    pass
def retry(retries=3, delay=2, exceptions=(Exception,), logger=None):
    def decorator_retry(func):
        @wraps(func)
        def wrapper_retry(*args, **kwargs):
            for attempt in range(retries):
                try:
                    ret = func(*args, **kwargs)
                    if not ret:
                        raise EmptyContentError("Returned value is empty or None")
                    return ret
                except exceptions as e:
                    if logger:
                        logger.log_exception()
                    else:
                        print(f"Attempt {attempt + 1} failed with error: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
            if logger:
                logger.log_info(f"All {retries} attempts failed.")
            else:
                print(f"All {retries} attempts failed.")
            return ''
        return wrapper_retry
    return decorator_retry