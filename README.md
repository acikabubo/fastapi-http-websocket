# Authentication and Authorization
## Overview

**Authentication** and **Authorization** are critical components in any secure web application:

- **Authentication** ensures that users are who they claim to be, typically using credentials like username and password or tokens.
- **Authorization** determines what actions authenticated users are permitted to perform based on their roles or permissions.

This FastAPI implementation leverages middleware and custom backends to handle both authentication and authorization seamlessly.
## Implementation Details

### Authentication

Authentication is handled by the `AuthenticationMiddleware` from **Starlette**.

- **Authentication Backend**:
  - A custom `AuthBackend` processes authentication logic, validating user credentials or tokens and attaching user information to the request.

### Authorization

Authorization is enforced through a custom middleware `PermAuthHTTPMiddleware`:

- **Permission Map**:
  - Defined as a JSON structure (e.g., `ACTIONS_FILE_PATH`) that maps action IDs to permissions like `"create_author"` or `"create_genre"`.
  - The middleware checks user permissions against this map to ensure they can perform requested actions.


```json
{
    "roles": [
      "role1",
      "role2",
      "role3",
    ],
    "ws": {
        "<PkgID>": "<required-role>"
    },
    "http": {
        "<request-path>": {
           "request-method": "<required-role>"
        }
    }
}
```

### Routers

#### Package router

I'll analyze the code and create comprehensive Markdown documentation explaining its purpose, components, and functionality.

# Package Router Documentation

## Overview
This code defines a robust routing and request handling system for a FastAPI-based web application, with a focus on WebSocket and API request management. The primary components are the `PackageRouter` class and the `collect_subrouters()` function.

## Key Components

### 1. PackageRouter Class

#### Purpose
The `PackageRouter` is a dynamic routing mechanism that:
- Registers request handlers for different package IDs
- Validates incoming requests
- Checks user permissions
- Routes requests to appropriate handler functions

#### Key Methods

##### `__init__()`
Initializes registries for:
- `handlers_registry`: Maps package IDs to handler functions
- `validators_registry`: Stores JSON schemas and validator functions
- `required_roles`: Defines role-based access control for different package IDs

##### `register()` Decorator
A powerful decorator that allows registering handler functions and validators for specific package IDs.

**Features:**
- Can register multiple package IDs simultaneously
- Supports optional JSON schema validation
- Prevents duplicate registrations

**Example Usage:**
```python
@pkg_router.register(PkgID.USER_LOGIN, json_schema=login_schema)
async def handle_user_login(request):
    # Login handling logic
```

##### `check_permission()`
Validates user roles against required roles for a specific package ID.

##### `handle_request()`
The core request handling method that:
1. Validates the package ID
2. Checks user permissions
3. Applies optional request validation
4. Calls the appropriate handler function

### 2. `collect_subrouters()` Function

#### Purpose
Automatically discovers and registers HTTP and WebSocket routers from specific application directories.

#### Key Features:
- Dynamically imports router modules
- Adds routers to a main `APIRouter`
- Logs registered routers

## Design Patterns and Techniques

### Dynamic Module Discovery
Uses `pkgutil.iter_modules()` to automatically discover and import router modules.

### Decorator-based Registration
Implements a flexible registration mechanism using decorators.

### Role-based Access Control
Integrates permission checking based on predefined role requirements.

### Validation Workflow
Supports optional JSON schema validation before request processing.

## Configuration

### Actions Configuration
Roles and permissions are loaded from an `actions.json` file specified by `ACTIONS_FILE_PATH`.

## Error Handling

### Request Handling Errors
Returns structured error responses for scenarios like:
- Missing package ID handlers
- Insufficient user permissions
- Validation failures

## Example Workflow

```python
# Register a handler for user login
@pkg_router.register(PkgID.USER_LOGIN, json_schema=login_schema)
async def login_handler(request):
    # Process login
    return ResponseModel.success(...)

# Automatic routing and permission checking happens in handle_request()
response = await pkg_router.handle_request(user, request)
```

---

## Workflow

1. **Middleware Integration**:
    - `PermAuthHTTPMiddleware` intercepts incoming HTTP requests.
    - It retrieves user permissions and validates them against the required action.

2. **Logged User Context**:
    - The `request.user` object, populated by `AuthBackend`, provides the current user’s details for logging and permission validation.

3. **Task Management**:
    - Background tasks like `kc_user_session_task` are initiated at application startup to manage user sessions (e.g., tracking Keycloak sessions).

# Managers

## RBAC Manager (Role-based access control `rbac_manager.py`)

### Overview
This code implements a Role-Based Access Control (RBAC) system, which acts as a security guard to check if users have permission to access different parts of an application. Think of it as a bouncer at a club who checks if people have the right type of ticket to enter different areas.

### Inputs and Outputs

#### Inputs:
- A JSON file containing role configurations that defines who can access what
- User information including their roles

#### Outputs:
- Boolean decisions (`True/False`) about whether a user is allowed to access something

### Implementation Details
The `RBACManager` class uses a design pattern called Singleton (through the `new` method) to ensure only one instance of the security checker exists. When it starts up, it reads role configurations from a JSON file and organizes them into two categories:

- **`ws`** for WebSocket permissions
- **`http`** for web request permissions

### Main Functions

#### 1. `check_ws_permission`
This function checks if a user can access WebSocket features:

- Takes a package ID number and user information as input
- Looks up what role is required for that package ID
- Checks if the user has that role in their list of roles
- Logs a message and returns `False` if permission is denied

#### 2. `check_http_permission`
This function checks if a user can access specific web endpoints:

- Takes a web request as input
- Examines the URL path and request type (GET, POST, etc.)
- Checks if the user has the required role
- Logs detailed messages for denied permissions

### Logic Flow
1. Load configuration from JSON file
2. When a permission check is needed, look up the required role
3. Check if the user has that role
4. Return `True` if they have permission, `False` if they don't

### Data Transformation
The code transforms the JSON configuration into easily searchable dictionaries (like lookup tables) where it can quickly find what role is needed for any given access attempt. This makes the permission-checking process fast and efficient.

### Purpose
This security system helps protect different parts of the application by ensuring users can only access features they're supposed to, based on their assigned roles.

## Websocket connection manager

The `ConnectionManager` class manages WebSocket connections for a FastAPI application, enabling connection handling and message broadcasting.

### Key Features

- **Connection Management**:
  - Maintains a list of active WebSocket connections (`active_connections`).
  - Provides methods to add (`connect`) and remove (`disconnect`) WebSocket connections.

- **Broadcasting**:
  - Allows sending a message to all active WebSocket connections using the `broadcast` method.

- **Logging**:
  - Logs connection and disconnection events for debugging purposes, including the unique identifier of each WebSocket object.

### Methods

#### `connect(websocket: WebSocket)`
- Accepts and adds a new WebSocket connection to the `active_connections` list.
- Logs the addition of the WebSocket connection.

#### `disconnect(websocket: WebSocket)`
- Removes a WebSocket connection from the `active_connections` list.
- Logs the removal of the WebSocket connection.
- Includes a TODO to handle cases where the user might not be logged in.

#### `broadcast(message: dict)`
- Sends a JSON-encoded message to all active WebSocket connections asynchronously.

### Purpose

The `ConnectionManager` class centralizes WebSocket connection management and simplifies real-time communication in a FastAPI application. It is particularly useful for scenarios like:
- Broadcasting updates to multiple clients.
- Managing active WebSocket connections efficiently.

### Example Usage

```python
from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await connection_manager.broadcast(data)
    except:
        connection_manager.disconnect(websocket)
```

## Keycloak manager

The `KeycloakManager` class is a **singleton** that simplifies interactions with a Keycloak server by managing two clients:

1. **`KeycloakAdmin` Client**: Handles administrative tasks within Keycloak.
2. **`KeycloakOpenID` Client**: Supports OpenID Connect operations, such as user authentication.

### Key Features

- **Singleton Design Pattern**:
  - Ensures only one instance of `KeycloakManager` exists in the application.
  - Managed via the `__new__` method.

- **Initialization**:
  - Configures the `KeycloakAdmin` and `KeycloakOpenID` clients with credentials and settings from environment variables:
    - `KEYCLOAK_ADMIN_USERNAME`
    - `KEYCLOAK_ADMIN_PASSWORD`
    - `KEYCLOAK_BASE_URL`
    - `KEYCLOAK_REALM`
    - `KEYCLOAK_CLIENT_ID`

- **Login Functionality**:
  - Provides a `login` method to authenticate a user using their **username** and **password**.
  - Returns an access token for subsequent API calls.

### Purpose

The `KeycloakManager` class centralizes configuration and functionality for:
- Authenticating users.
- Performing administrative tasks.
- Ensuring thread safety through the singleton design.

This design improves reusability, simplifies code management, and abstracts the complexity of interacting with Keycloak.

### Example Usage

```python
keycloak_manager = KeycloakManager()

# Authenticate a user
token = keycloak_manager.login(username="user1", password="password123")
print(f"Access Token: {token}")
```

# API and WS handers documentation

## Establish WebSocket connection

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as Backend-Server
    participant DB as PostgreSQL

    alt Establishing WebSocket connection
        C->>WA: <br/>
        WA->>S: GET /web
        WA->>S: Established WebSocket connection
        S->>WA: Send initial data to client
    end
```

## Make WebSocket Request/Response

### Request data format

#### Regular request data
```json
{
    "pkg_id": "<int>",
    "req_id": "<uuid>",
    "data": {...}
}
```

#### Request for paginated data
```json
{
    "pkg_id": "<int>",
    "req_id": "<uuid>",
}

Without pagination params default are page=1 and per_page=20

{
    "pkg_id": 2,
    "req_id": "<uuid>",
    "data": {
        "page": 1,
        "per_page": 5
    }
}
```

### Response data format

#### Response for regular request
```json
{
    "pkg_id": "Same <int> like request",
    "req_id": "Same <UUID> like request",
    "status": 0,
    "data": {...}
}
```

#### Response for paginated request
```json
{
    "pkg_id": "Same <int> like request",
    "req_id": "Same <UUID> like request",
    "status_code": 0,
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 4,
        "pages": 1
    },
    "data": [...]
}
```

```json
{
    "pkg_id": "Same <int> like request",
    "req_id": "Same <UUID> like request",
    "status_code": 0,
    "meta": {
        "page": 1,
        "per_page": 5,
        "total": 4,
        "pages": 1
    },
    "data": [...]
}
```

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as BackendServer

    alt Make WebSocket Request/Response
        C->>WA: <br/>
        WA->>S: GET /web
        S-->>WA: 101 Switching Protocols
        WA->>S: Send request with data like above
        S->>S: Handler the request
        S-->WA: Return the response
    end
```

## Make HTTP Request/Response

```mermaid
sequenceDiagram
    actor C as Client
    participant WA as Web Application
    participant S as BackendServer


    alt Make HTTP Rest Request/Response
        C->>WA: <br/>
        WA->>S: GET /web
        S->>WA: Server send response
    end
```
