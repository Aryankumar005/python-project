class HabitTrackerException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class InvalidEmailError(HabitTrackerException): pass
class UserAlreadyExistsError(HabitTrackerException): pass
class UserNotFoundError(HabitTrackerException): pass
class InvalidPasswordError(HabitTrackerException): pass
class NetworkUnavailableError(HabitTrackerException): pass
class OTPExpiredError(HabitTrackerException): pass
class InvalidOTPError(HabitTrackerException): pass
class HabitNotFoundError(HabitTrackerException): pass
class DuplicateHabitError(HabitTrackerException): pass
class DataCorruptedError(HabitTrackerException): pass