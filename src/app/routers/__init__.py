# Routers package — API route handlers.
# All routers are thin: validate input (Pydantic) → call service → return response.
# NEVER put business logic in routers. See: 00-architecture.md §8 note 4.
#
# work by adolf.
