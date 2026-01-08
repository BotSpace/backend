"""
Encryption/Decryption utilities for flow data using RSA-OAEP + AES-256-GCM
"""
import os
import base64
import json
from typing import Dict

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings


def load_private_key():
    """
    Load private key from FLOW_PRIVATE_KEY environment variable
    
    FLOW_PRIVATE_KEY can be:
    - Direct PEM content (from Kubernetes secrets) - recommended
    - File path (for local development)
    
    If not set, defaults to keys/private.pem file
    """
    flow_key_env = os.environ.get("FLOW_PRIVATE_KEY")
    
    if flow_key_env:
        # Check if it's PEM content (starts with -----BEGIN)
        if flow_key_env.strip().startswith("-----BEGIN"):
            # Direct PEM content from environment (Kubernetes secret)
            key_bytes = flow_key_env.encode('utf-8')
        else:
            # File path
            with open(flow_key_env, "rb") as f:
                key_bytes = f.read()
    else:
        # Default file path
        default_path = os.path.join(settings.BASE_DIR, "keys", "private.pem")
        with open(default_path, "rb") as f:
            key_bytes = f.read()
    
    return serialization.load_pem_private_key(key_bytes, password=None)


def load_public_key():
    """
    Load public key from FLOW_PUBLIC_KEY environment variable
    
    FLOW_PUBLIC_KEY can be:
    - Direct PEM content (from Kubernetes secrets) - recommended
    - File path (for local development)
    
    If not set, defaults to keys/public.pem file
    """
    flow_key_env = os.environ.get("FLOW_PUBLIC_KEY")
    
    if flow_key_env:
        # Check if it's PEM content (starts with -----BEGIN)
        if flow_key_env.strip().startswith("-----BEGIN"):
            # Direct PEM content from environment (Kubernetes secret)
            key_bytes = flow_key_env.encode('utf-8')
        else:
            # File path
            with open(flow_key_env, "rb") as f:
                key_bytes = f.read()
    else:
        # Default file path
        default_path = os.path.join(settings.BASE_DIR, "keys", "public.pem")
        with open(default_path, "rb") as f:
            key_bytes = f.read()
    
    return serialization.load_pem_public_key(key_bytes)


def decrypt_flow_payload(payload: dict) -> dict:
    """
    Decrypt flow payload using RSA-OAEP + AES-256-GCM
    
    Args:
        payload: Dictionary containing encryptedKey, encryptedData, and iv
        
    Returns:
        Decrypted flow data as dictionary
    """
    private_key = load_private_key()
    
    encrypted_key = base64.b64decode(payload["encryptedKey"])
    encrypted_data = base64.b64decode(payload["encryptedData"])
    iv = base64.b64decode(payload["iv"])
    
    # Decrypt AES key using RSA-OAEP (SHA-256)
    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    
    # Decrypt data using AES-256-GCM
    aesgcm = AESGCM(aes_key)
    decrypted_bytes = aesgcm.decrypt(iv, encrypted_data, None)
    
    decrypted_text = decrypted_bytes.decode("utf-8")
    return json.loads(decrypted_text)


def encrypt_flow_payload(flow_data: dict) -> dict:
    """
    Encrypt flow data using RSA-OAEP + AES-256-GCM
    
    Args:
        flow_data: Flow data to encrypt (will be JSON serialized)
        
    Returns:
        Dictionary containing encryptedKey, encryptedData, and iv (all base64 encoded)
    """
    public_key = load_public_key()
    
    # Generate random AES key (256-bit)
    aes_key = AESGCM.generate_key(bit_length=256)
    
    # Generate random IV (96-bit for GCM)
    iv = os.urandom(12)
    
    # Serialize flow data to JSON bytes
    flow_json = json.dumps(flow_data)
    flow_bytes = flow_json.encode("utf-8")
    
    # Encrypt data using AES-256-GCM
    aesgcm = AESGCM(aes_key)
    encrypted_data = aesgcm.encrypt(iv, flow_bytes, None)
    
    # Encrypt AES key using RSA-OAEP (SHA-256)
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    
    return {
        "encryptedKey": base64.b64encode(encrypted_key).decode("utf-8"),
        "encryptedData": base64.b64encode(encrypted_data).decode("utf-8"),
        "iv": base64.b64encode(iv).decode("utf-8"),
    }
