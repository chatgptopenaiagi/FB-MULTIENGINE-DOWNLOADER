package org.dragonhydra.fbmd;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.nio.charset.StandardCharsets;

public final class Vault {
    private final Context context;
    private final SecretKey key;
    public Vault(Context c) {
        context=c.getApplicationContext();
        try {
            KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
            if (!ks.containsAlias("fbmd-v1")) {
                KeyGenerator gen=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
                gen.init(new KeyGenParameterSpec.Builder("fbmd-v1",KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
                gen.generateKey();
            }
            key=(SecretKey)ks.getKey("fbmd-v1",null);
        } catch(Exception e) { throw new IllegalStateException("Android credential vault unavailable",e); }
    }
    public String seal(String value) {
        try {
            Cipher c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.ENCRYPT_MODE,key);
            return Base64.encodeToString(c.getIV(),Base64.NO_WRAP)+":"+Base64.encodeToString(c.doFinal(value.getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP);
        } catch(Exception e) {throw new IllegalStateException("Encryption failed",e);}
    }
    public String open(String value) {
        try {
            String[] parts=value.split(":",2);Cipher c=Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.DECRYPT_MODE,key,new GCMParameterSpec(128,Base64.decode(parts[0],Base64.NO_WRAP)));
            return new String(c.doFinal(Base64.decode(parts[1],Base64.NO_WRAP)),StandardCharsets.UTF_8);
        } catch(Exception e) {throw new IllegalStateException("Credential decryption failed",e);}
    }
    public void put(String name,String value) {context.getSharedPreferences("vault",0).edit().putString(name,seal(value)).commit();}
    public String get(String name) {String v=context.getSharedPreferences("vault",0).getString(name,null);return v==null?null:open(v);}
    public void forget() {context.getSharedPreferences("vault",0).edit().clear().commit();}
}
