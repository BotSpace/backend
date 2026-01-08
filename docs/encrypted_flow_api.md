# Encrypted Flow API Documentation

## Overview

This documentation describes the encrypted flow APIs that allow secure transmission of project flow data using RSA-OAEP + AES-256-GCM encryption.

## Encryption Method

The flow data is encrypted using a hybrid encryption scheme:
1. **AES-256-GCM** for data encryption (symmetric)
2. **RSA-OAEP with SHA-256** for AES key encryption (asymmetric)

This ensures both security and performance for large flow data.

## Endpoints

### 1. Update Project Flow (Encrypted)

Updates a project's flow using encrypted data sent from the client.

**Endpoint:** `POST /api/project/{project_id}/update-encrypted-flow/`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "payload": {
    "encryptedKey": "base64-encoded-encrypted-aes-key",
    "encryptedData": "base64-encoded-encrypted-flow-data",
    "iv": "base64-encoded-initialization-vector"
  }
}
```

**Response (Success - 200):**
```json
{
  "detail": "Flow updated"
}
```

**Response (Error - 400):**
```json
{
  "payload": "Decryption error: [error details]"
}
```

**Example using Python:**
```python
import requests
import json
import base64
import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Load public key (get from backend admin)
def load_public_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

# Encrypt flow data
def encrypt_flow(flow_data, public_key):
    # Generate random AES key (256-bit)
    aes_key = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    
    # Encrypt data with AES-256-GCM
    flow_json = json.dumps(flow_data).encode('utf-8')
    aesgcm = AESGCM(aes_key)
    encrypted_data = aesgcm.encrypt(iv, flow_json, None)
    
    # Encrypt AES key with RSA-OAEP
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    
    return {
        "encryptedKey": base64.b64encode(encrypted_key).decode('utf-8'),
        "encryptedData": base64.b64encode(encrypted_data).decode('utf-8'),
        "iv": base64.b64encode(iv).decode('utf-8'),
    }

# Example usage
public_key = load_public_key("public.pem")
flow_data = {
    "nodes": [...],
    "edges": [...]
}

encrypted_payload = encrypt_flow(flow_data, public_key)

# Send to API
response = requests.post(
    "https://api.example.com/api/project/123/update-encrypted-flow/",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"payload": encrypted_payload}
)
print(response.json())
```

### 2. Get Project Flow (Encrypted)

Retrieves a project's flow data in encrypted format.

**Endpoint:** `GET /api/project/{project_id}/get-encrypted-flow/`

**Authentication:** Required (Bearer Token)

**Response (Success - 200):**
```json
{
  "payload": {
    "encryptedKey": "base64-encoded-encrypted-aes-key",
    "encryptedData": "base64-encoded-encrypted-flow-data",
    "iv": "base64-encoded-initialization-vector"
  }
}
```

**Response (Error - 400):**
```json
{
  "error": "Encryption error: [error details]"
}
```

**Example using Python:**
```python
import requests
import json
import base64
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Load private key
def load_private_key(path):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

# Decrypt flow data
def decrypt_flow(payload, private_key):
    encrypted_key = base64.b64decode(payload["encryptedKey"])
    encrypted_data = base64.b64decode(payload["encryptedData"])
    iv = base64.b64decode(payload["iv"])
    
    # Decrypt AES key with RSA-OAEP
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    
    # Decrypt data with AES-256-GCM
    aesgcm = AESGCM(aes_key)
    decrypted_bytes = aesgcm.decrypt(iv, encrypted_data, None)
    
    return json.loads(decrypted_bytes.decode('utf-8'))

# Example usage
private_key = load_private_key("private.pem")

response = requests.get(
    "https://api.example.com/api/project/123/get-encrypted-flow/",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

encrypted_payload = response.json()["payload"]
flow_data = decrypt_flow(encrypted_payload, private_key)
print(json.dumps(flow_data, indent=2))
```

## Environment Variables

The backend uses the following environment variables for key management:

- `FLOW_PRIVATE_KEY` - Path to RSA private key (default: `keys/private.pem`)
- `FLOW_PUBLIC_KEY` - Path to RSA public key (default: `keys/public.pem`)

## Security Notes

1. **Key Management**: 
   - Private keys should never be shared or exposed
   - Public keys can be distributed to clients
   - Keys should be stored securely and not committed to version control

2. **Transport Security**:
   - Always use HTTPS in production
   - The encrypted payload provides end-to-end encryption even over HTTP

3. **Key Generation**:
   ```bash
   # Generate RSA key pair (2048-bit minimum, 4096-bit recommended)
   openssl genrsa -out private.pem 4096
   openssl rsa -in private.pem -pubout -out public.pem
   ```

## Error Handling

Common errors and their meanings:

- `Decryption error: Decryption failed` - Invalid encrypted data or wrong key
- `Encryption error: ...` - Issue encrypting data on server side
- `401 Unauthorized` - Missing or invalid authentication token
- `404 Not Found` - Project not found or not accessible

## Testing

A test script is available at `/tmp/test_encryption_simple.py` that demonstrates the encryption/decryption process without requiring Django setup.

## Complete Example

See the Python example code provided in the problem statement for a complete working implementation of the decryption process.
