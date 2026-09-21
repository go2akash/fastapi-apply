"""
Domain exceptions — business-level errors that are NOT HTTP errors.

WHY SEPARATE DOMAIN EXCEPTIONS?
---------------------------------
First-principles rule: Your business logic should know NOTHING about HTTP.

A service function that checks "does this email already exist?" should raise
DuplicateEmailError — NOT HTTPException(status_code=400).

Why?
1. If you call the same service from a CLI tool, there IS no HTTP status code.
2. If you call it from a background job, there IS no HTTP response.
3. The service's job is to say WHAT went wrong. The router's job is to
   decide HOW to tell the client (400? 409? 422?).

This is the Error Domain Boundary principle:
  Internal Domain Exception → mapped to → HTTP Status Code (by the router)

The same concept exists everywhere:
- Go: return custom error types, http handler maps them to status codes
- Java: throw BusinessException, @ControllerAdvice maps to ResponseEntity
- Node: throw AppError, Express error middleware maps to res.status()
"""


class DuplicateEmailError(Exception):
    """Raised when a signup attempt uses an email that's already registered."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when login credentials don't match."""
    pass


class UserNotFoundError(Exception):
    """Raised when a referenced user doesn't exist in the database."""
    pass
