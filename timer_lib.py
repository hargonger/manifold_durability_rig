import threading
import time

class PausableTimer:
    def __init__(self, interval, function):
        self.interval = interval  # Total interval time (in seconds)
        self.function = function
        self.timer = None
        self.start_time = None
        self.remaining_time = interval
        self.paused = False

    def start(self):
        """Start or resume the timer."""
        if self.paused:  # If resuming
            self.paused = False
        else:  # If starting fresh
            self.remaining_time = self.interval  

        self.start_time = time.time()
        self.timer = threading.Timer(self.remaining_time, self._execute)
        self.timer.daemon = True
        self.timer.start()
        print(f"remaining time: {self.remaining_time}")

    def _execute(self):
        """Execute the function and restart the timer."""
        self.function()
        self.start()  # Restart the timer after execution

    def pause(self):
        """Pause the timer and store remaining time."""
        if self.timer:
            self.timer.cancel()
            elapsed_time = time.time() - self.start_time
            print(f"elapsed time: {elapsed_time}")
            self.remaining_time -= elapsed_time
            self.paused = True
            print(f"remaining time: {self.remaining_time}")

    def resume(self):
        """Resume the timer with the remaining time."""
        if self.paused:
            self.start()

    def stop(self):
        """Completely stop the timer."""
        if self.timer:
            self.timer.cancel()
        self.remaining_time = self.interval
        self.paused = False

if __name__ == "__main__":

    # Example usage
    def update_temperature():
        print("Updating temperature...")

    timer = PausableTimer(12 * 3600, update_temperature)  
    timer.start()  # Start the timer

    # You can call `timer.pause()`, `timer.resume()`, and `timer.stop()` as needed.
