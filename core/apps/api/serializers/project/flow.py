"""
Serializers for encrypted flow operations
"""
from rest_framework import serializers


class EncryptedFlowPayloadSerializer(serializers.Serializer):
    """Serializer for encrypted flow payload"""
    encryptedKey = serializers.CharField(
        help_text="Base64-encoded encrypted AES key (RSA-OAEP encrypted)"
    )
    encryptedData = serializers.CharField(
        help_text="Base64-encoded encrypted flow data (AES-256-GCM encrypted)"
    )
    iv = serializers.CharField(
        help_text="Base64-encoded initialization vector for AES-GCM"
    )


class UpdateEncryptedFlowSerializer(serializers.Serializer):
    """Serializer for updating project flow with encrypted data"""
    payload = EncryptedFlowPayloadSerializer(
        help_text="Encrypted flow payload containing encryptedKey, encryptedData, and iv"
    )


class EncryptedFlowResponseSerializer(serializers.Serializer):
    """Serializer for encrypted flow response"""
    payload = EncryptedFlowPayloadSerializer(
        help_text="Encrypted flow data"
    )
