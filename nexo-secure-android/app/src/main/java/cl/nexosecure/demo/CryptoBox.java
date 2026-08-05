package cl.nexosecure.demo;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;

final class CryptoBox {
    static final class Encrypted {
        final String nonce;
        final byte[] ciphertext;

        Encrypted(String nonce, byte[] ciphertext) {
            this.nonce = nonce;
            this.ciphertext = ciphertext;
        }

        String ciphertextBase64() {
            return Base64.getEncoder().withoutPadding().encodeToString(ciphertext);
        }
    }

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final int ITERATIONS = 150_000;

    private CryptoBox() {}

    static Encrypted encryptText(String secret, String myId, String peerId, String text) throws Exception {
        return encrypt(secret, myId, peerId, text.getBytes(StandardCharsets.UTF_8));
    }

    static String decryptText(String secret, String myId, String peerId,
                              String nonce, String ciphertext) throws Exception {
        byte[] plain = decrypt(secret, myId, peerId, nonce,
                Base64.getDecoder().decode(ciphertext));
        return new String(plain, StandardCharsets.UTF_8);
    }

    static Encrypted encrypt(String secret, String myId, String peerId,
                             byte[] plaintext) throws Exception {
        byte[] nonce = new byte[12];
        RANDOM.nextBytes(nonce);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, deriveKey(secret, myId, peerId),
                new GCMParameterSpec(128, nonce));
        cipher.updateAAD(pair(myId, peerId).getBytes(StandardCharsets.UTF_8));
        byte[] encrypted = cipher.doFinal(plaintext);
        return new Encrypted(Base64.getEncoder().withoutPadding().encodeToString(nonce), encrypted);
    }

    static byte[] decrypt(String secret, String myId, String peerId,
                          String nonceBase64, byte[] ciphertext) throws Exception {
        byte[] nonce = Base64.getDecoder().decode(nonceBase64);
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, deriveKey(secret, myId, peerId),
                new GCMParameterSpec(128, nonce));
        cipher.updateAAD(pair(myId, peerId).getBytes(StandardCharsets.UTF_8));
        return cipher.doFinal(ciphertext);
    }

    private static SecretKey deriveKey(String secret, String firstId, String secondId) throws Exception {
        if (secret == null || secret.length() < 8) {
            throw new IllegalArgumentException("La clave privada debe tener al menos 8 caracteres");
        }
        byte[] salt = MessageDigest.getInstance("SHA-256")
                .digest(("NexoSecureAlpha|" + pair(firstId, secondId))
                        .getBytes(StandardCharsets.UTF_8));
        PBEKeySpec specification = new PBEKeySpec(secret.toCharArray(), salt, ITERATIONS, 256);
        try {
            byte[] encoded = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
                    .generateSecret(specification).getEncoded();
            return new SecretKeySpec(encoded, "AES");
        } finally {
            specification.clearPassword();
            Arrays.fill(salt, (byte) 0);
        }
    }

    private static String pair(String firstId, String secondId) {
        return firstId.compareTo(secondId) <= 0
                ? firstId + "|" + secondId
                : secondId + "|" + firstId;
    }
}
