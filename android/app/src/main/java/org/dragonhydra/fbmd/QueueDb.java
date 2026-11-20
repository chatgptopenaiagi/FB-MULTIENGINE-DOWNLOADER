package org.dragonhydra.fbmd;

import android.content.Context;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.regex.*;

public final class QueueDb extends SQLiteOpenHelper {
    public final Vault vault;
    public QueueDb(Context c) {super(c,"queue.db",null,1);vault=new Vault(c);setWriteAheadLoggingEnabled(true);}
    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE jobs(id INTEGER PRIMARY KEY,fingerprint TEXT UNIQUE,url TEXT,display TEXT,engine TEXT,status TEXT DEFAULT 'queued',done INTEGER DEFAULT 0,total INTEGER DEFAULT 0,attempts INTEGER DEFAULT 0,next_try INTEGER DEFAULT 0,error TEXT DEFAULT '',path TEXT DEFAULT '',sha256 TEXT DEFAULT '',etag TEXT DEFAULT '')");
    }
    @Override public void onUpgrade(SQLiteDatabase db,int a,int b) {throw new IllegalStateException("Unsupported schema upgrade");}
    public static String validate(String value) {
        URI u=URI.create(value.trim());
        if (!("http".equals(u.getScheme())||"https".equals(u.getScheme())) || u.getHost()==null || u.getUserInfo()!=null || value.length()>16000) throw new IllegalArgumentException("Use HTTP(S) URLs without embedded credentials");
        String host=u.getHost();
        if(!BuildConfig.DEBUG&&!"https".equals(u.getScheme()))throw new IllegalArgumentException("Release requires HTTPS");
        if(!BuildConfig.DEBUG&&(host.equals("localhost")||host.contains(":")||host.matches("[0-9.]+")||(u.getPort()!=-1&&u.getPort()!=80&&u.getPort()!=443)))throw new IllegalArgumentException("Local targets and nonstandard ports blocked");
        return value.trim();
    }
    public static String digest(byte[] bytes) {
        try {StringBuilder b=new StringBuilder();for(byte v:MessageDigest.getInstance("SHA-256").digest(bytes))b.append(String.format(Locale.ROOT,"%02x",v));return b.toString();}
        catch(Exception e){throw new IllegalStateException(e);}
    }
    public static String display(String value) {URI u=URI.create(value);return u.getScheme()+"://"+u.getHost()+u.getPath();}
    public static String identity(String value) {
        URI u=URI.create(value);String host=u.getHost();
        if (host.equals("facebook.com")||host.endsWith(".facebook.com")) {
            Matcher m=Pattern.compile("/(?:reel|videos)/(\\d+)").matcher(u.getPath());
            if(m.find())return "facebook:"+m.group(1);
            m=Pattern.compile("(?:^|&)v=(\\d+)(?:&|$)").matcher(u.getQuery()==null?"":u.getQuery());
            if(m.find())return "facebook:"+m.group(1);
        }
        return value.split("#",2)[0];
    }
    public synchronized long add(String value,String engine) {
        value=validate(value);String fingerprint=digest(identity(value).getBytes(StandardCharsets.UTF_8));
        ContentValues v=new ContentValues();v.put("fingerprint",fingerprint);v.put("url",vault.seal(value));v.put("display",display(value));v.put("engine",engine);
        getWritableDatabase().insertWithOnConflict("jobs",null,v,SQLiteDatabase.CONFLICT_IGNORE);
        try(Cursor c=getReadableDatabase().rawQuery("SELECT id FROM jobs WHERE fingerprint=?",new String[]{fingerprint})){c.moveToFirst();return c.getLong(0);}
    }
    public synchronized void update(long id,Object... fields) {
        ContentValues v=new ContentValues();
        for(int i=0;i<fields.length;i+=2) {
            Object value=fields[i+1];String key=(String)fields[i];
            if(value instanceof Number)v.put(key,((Number)value).longValue());else v.put(key,String.valueOf(value));
        }
        getWritableDatabase().update("jobs",v,"id=?",new String[]{String.valueOf(id)});
    }
    public synchronized List<Map<String,String>> rows() {
        List<Map<String,String>> list=new ArrayList<>();
        try(Cursor c=getReadableDatabase().rawQuery("SELECT * FROM jobs ORDER BY id DESC",null)) {
            while(c.moveToNext()){Map<String,String> m=new HashMap<>();for(String key:c.getColumnNames())if(!key.equals("url"))m.put(key,c.getString(c.getColumnIndexOrThrow(key)));list.add(m);}
        }
        return list;
    }
    public synchronized Map<String,String> job(long id) {
        try(Cursor c=getReadableDatabase().rawQuery("SELECT * FROM jobs WHERE id=?",new String[]{String.valueOf(id)})) {
            if(!c.moveToFirst())throw new IllegalArgumentException("Job missing");Map<String,String> m=new HashMap<>();
            for(String key:c.getColumnNames())m.put(key,c.getString(c.getColumnIndexOrThrow(key)));m.put("url",vault.open(m.get("url")));return m;
        }
    }
    public synchronized long claim() {
        SQLiteDatabase db=getWritableDatabase();db.beginTransaction();
        try(Cursor c=db.rawQuery("SELECT id FROM jobs WHERE status IN ('queued','retry') AND next_try<=? ORDER BY id LIMIT 1",new String[]{String.valueOf(System.currentTimeMillis())})) {
            long id=-1;if(c.moveToFirst()){id=c.getLong(0);db.execSQL("UPDATE jobs SET status='running',attempts=attempts+1 WHERE id=?",new Object[]{id});}
            db.setTransactionSuccessful();return id;
        } finally {db.endTransaction();}
    }
    public synchronized void recover(){getWritableDatabase().execSQL("UPDATE jobs SET status='queued',error='Recovered interrupted process' WHERE status='running'");}
    public synchronized void pause(){getWritableDatabase().execSQL("UPDATE jobs SET status='paused' WHERE status IN ('queued','running','retry')");}
    public synchronized void resume(){getWritableDatabase().execSQL("UPDATE jobs SET status='queued',attempts=0,next_try=CASE WHEN error LIKE 'RATE_LIMITED:%' THEN next_try ELSE 0 END,error='' WHERE status IN ('paused','failed','blocked','retry')");}
    public synchronized void cancel(long id){getWritableDatabase().execSQL("UPDATE jobs SET status='cancelled' WHERE id=? AND status<>'complete'",new Object[]{id});}
}
