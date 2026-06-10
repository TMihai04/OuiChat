# Configuration constants for the app


APP_TITLE = "Ouichat backend"
APP_DESCRIPTION = """Back-end API for the OuiChat messaging app.
    
### Websocket endpoint(s)
    
**Global websocket endpoint**: `/ws/global`

Frontend should connect to this endpoint on start-up right after aquiring the access token. This websocket is used for streaming live updates from the backend to the frontend (eg. new user registered on the server, new chat created), as well as streaming certain details from the frontent to the backend (eg. last time user viewed a chat).

Since the connection remains open, it will inevitably outlive the lifespan of the access token used for authentication. For this reason, the backend will send a notification 60 seconds before token expiry. Frontend should respond with a new access token in the necessary format. Failure to provide the access token will result in the websocket connection being closed by the backend.

**Note**: This requirement is *per connection* not *per user*, so if the same user is connected from multiple devices, the backend will terminate all connections that failed to reauthenticate in the alloted timespan.

**Args**:
* `payload`: The access token for the API. Connection url will follow the format: `ws[s]://<backend_domain>[:<port>]/ws/global?payload=<access_token>`

**Event format**:

Events are formatted after the following schema:
```json
{
    "type": {str} "create" | "update" | "delete" | "system",
    "scope": {str:pattern} ^[\w]+(.[\w]+)*$,
    "data": {
        "additionalProp1": {any} $value1,
        "additionalProp2": {any} $value2,
        ...
    }
}
```

**Event list**:

Bellow is a list of all possible events emitted by the backend.

* Access token about to expire. **This one is the most important; for keeping the connection going**
```json
{
    "type": {str} "system",
    "scope": {str} "token.access",
    "data": {
        "message": {str} "Current access token is about to expire"
    }
}
```

* New user added to server
```json
{
    "type": {str} "create",
    "scope": {str} "user",
    "data": {
        "username": {str} $username,
        "profile": {
            "status: {str} $status,
            "picture_id": {str} $picture_id
        }
    }
}
```

* Existent user removed from server
```json
{
    "type": {str} "delete",
    "scope": {str} "user",
    "data": {
        "username": {str} $username
    }
}
```

* Current user gets blacklisted
```json
{
    "type": {str} "update",
    "scope": {str} "user.blacklist",
    "data": {
        "username": {str} $username,
        "is_blacklisted": {bool} true
    }
}
```

* Current user gets whitelisted
```json
{
    "type": {str} "update",
    "scope": {str} "user.blacklist",
    "data": {
        "username": {str} $username,
        "is_blacklisted": {bool} false
    }
}
```

* A user updates their profile status
```json
{
    "type": {str} "update",
    "scope": {str} "user.status",
    "data": {
        "username": {str} $username,
        "status": {str} $status
    }
}
```

* A user updates their profile picture
```json
{
    "type": {str} "update",
    "scope": {str} "user.picture",
    "data": {
        "username": {str} $username,
        "picture_id": {str} $pic_id
    }
}
```

* A user logs into the server
```json
{
    "type": {str} "update",
    "scope": {str} "user.login",
    "data": {
        "username": {sttr} $username,
        "last_login": {int} $login_time
    }
}
```

* New conversation added to server
```json
{
    "type": {str} "create",
    "scope": {str} "conversation",
    "data": {dict} $conversation_schema
}
```

* An existent conversation is deleted
```json
{
    "type": {str} "delete",
    "scope": {str} "conversation",
    "data": {
        "conversation_id": {str} $conv_id
    }
}
```

* Conversation admin states altered
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.admins,
    "data": {
        "conversation_id": {str} $conv_id,
        "make_admin": [
            {str} $username_m1,
            ...
        ],
        "remove_admin": [
            {str} $username_r1,
            ...
        ]
    }
}
```

* User(s) added to a conversation
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.participants",
    "data": {
        "conversation_id": {str} #conv_id,
        "operation": {str} "added",
        "who": [
            {str} $username_a1,
            ...
        ]
    }
}
```

* User(s) removed from conversation
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.participants",
    "data": {
        "conversation_id": {str} $conv_id,
        "operation": {str} "removed",
        "who": [
            {str} $username_r1,
            ...
        ]
    }
}
```

* Conversation display name updated
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.name",
    "data": {
        "conversation_id": {str} $conv_id,
        "name": {str} $name
    }
}
```

* Conversation display description updated
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.description",
    "data": {
        "conversation_id": {str} $conv_id,
        "description": {str} $description
    }
}
```

* Conversation display picture updated
```json
{
    "type": {str} "update",
    "scope": {str} "conversation.picture",
    "data": {
        "conversation_id": {str} $conv_id,
        "picture_id": {str} $pic_id
    }
}
```"""