# API Docs

The API server for High/Low is located at https://api.gethighlow.com.

In general, a request to the API will be to a URL of the form https://api.gethighlow.com/&lt;service&gt;/&lt;endpoint&gt;

## Auth

### /auth/sign_up

**Description:** Creates a new user

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `firstname<String>, lastname<String>, email<String>, password<String>, confirmpassword<String>`

**Returns:** 

```
{
	token: <String>,
	uid: <String>,
	error: <String>
}
```

**Errors:** 

- *empty-first-name*: The firstname given had a length of 0
- *empty-last-name*: The lastname given had a length of 0
- *empty-email*: The email given had a length of 0
- *email-already-taken*: The email given is in use by another user
- *invalid-email*: The email given is not a valid email
- *password-too-short*: The password was too short (minimum length of 6 characters)
- *passwords-no-match*: The password and confirmpassword do not match



### /auth/sign_in

**Description:** Signs in a user

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `email<String>, password<String>`

**Returns:** 

```
{
	token: <String>,
	uid: <String>,
	error: <String>
}
```

**Errors:** 

- *incorrect-email-or-password*: The username or password was incorrect
- *user-no-exist*: There is no user with the given email



### /auth/password_reset/<string:reset_id>

**Description:** Resets a user's password

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `password<String>, confirmpassword<String>`

**Returns:** 

```
{
	status: <String>,
	error: <String>
}
```

**Errors:** 

- *ERROR-INVALID-RESET-ID*: The reset id provided in the URL was invalid
- *passwords-no-match*: The password and confirmpassword do not match


**Additional Info:**

The `reset_id` provided in the URL must be a valid authorization token.
You probably won't ever have to call this endpoint, as it will instead appear as a link in the password reset request email.



### /auth/forgot_password

**Description:** Sends a "forgot password" email to a user, asking whether they really want to reset their password

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `email<String>`

**Returns:** 

```
{
	status: <String>,
	error: <String>
}
```

**Errors:** 

- *user-no-exist*: There is no user with the given email


### /auth/verify_token

**Description:** Determines whether a given token is valid. **NOT RECOMMENDED FOR REGULAR USE**

**Request Method:** POST

**Authorization Required:** True

**Parameters:** None

**Returns:** 

```
{
	uid: <String>,
	error: <String>
}
```

**Errors:** 

- *user-no-exist*: There is no user with the given email





## Email


### /email/send_html_email

**Description:** Sends an HTML-formatted email to a given address

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `email<String>, message<String>, password<String>`

**Returns:** 

```
{
	status: <String>
}
```

**Errors:** 

None






### /email/send_email

**Description:** Sends a plaintext email to a given address

**Request Method:** POST

**Authorization Required:** False

**Parameters:** `email<String>, message<String>, password<String>`

**Returns:** 

```
{
	status: <String>
}
```

**Errors:** 

None






## User



### /user/get/<string:property>

**Description:** Returns a property for a user

**Request Method:** POST

**Authorization Required:** True

**Parameters:** None

**Returns:**

```
{
	property: <String>,
	error: <String>
}
```

**Errors:** 
- *ERROR-INVALID-TOKEN*: The provided authentication token was invalid






### /user/set/<string:property>

**Description:** Sets a property for a user

**Request Method:** POST

**Authorization Required:** True

**Parameters:** `value<String>`

**Files:** `File (Optional; for setting profile picture)`

**Returns:**

```
{
	status: <String>,
	error: <String>
}
```

**Errors:** 
- *ERROR-INVALID-TOKEN*: The provided authentication token was invalid
- *no-file-uploaded*: No file was uploaded (only occurs when setting profile picture)








### /user/flag/<string:user>

**Description:** Flags a user for inappropriate content

**Request Method:** POST

**Authorization Required:** True

**Parameters:** None

**Returns:**

```
{
	status: <String>,
	error: <String>
}
```

**Errors:** 
- *ERROR-INVALID-TOKEN*: The provided authentication token was invalid
- *user-no-exist*: The flagged user does not exist










### /user/unflag/<string:user>

**Description:** Unflags a user for inappropriate content

**Request Method:** POST

**Authorization Required:** True

**Parameters:** None

**Returns:**

```
{
	status: <String>,
	error: <String>
}
```

**Errors:** 
- *ERROR-INVALID-TOKEN*: The provided authentication token was invalid
- *user-no-exist*: The flagged user does not exist





### /user/feed/page/<int:page>

**Description:** Fetches the items for a given page in the feed (each page can hold 10 items)

**Request Method:** GET

**Authorization Required:** True

**Parameters:** None

**Returns:**

```
[
	{
		friend_id: <String>,
		highlowid: <String>,
		high: <String>,
		low: <String>,
		high_image: <String>,
		low_image: <String>,
		_timestamp: <Timestamp>,
		total_likes: <Int>
	}
]
```

If error:

```
{
	error: <String>
}
```

**Errors:** 
- *ERROR-INVALID-TOKEN*: The provided authentication token was invalid










