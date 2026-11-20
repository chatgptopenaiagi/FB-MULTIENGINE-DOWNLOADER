package org.dragonhydra.fbmd;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.*;
import java.net.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.regex.*;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import kotlin.Unit;
import okhttp3.Request;
import okhttp3.Response;

public final class DownloadService extends Service {
    private final AtomicBoolean working=new AtomicBoolean();
    private volatile boolean stopped;
    private QueueDb db;
    private volatile long active=-1;
    private Thread thread;
    static class Paused extends IOException {}
    static class Blocked extends IOException {}
    static class InvalidMedia extends IOException {}
    @Override public void onCreate(){super.onCreate();db=new QueueDb(this);}
    @Override public IBinder onBind(Intent i){return null;}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel("downloads","Media downloads",NotificationManager.IMPORTANCE_LOW));
        PendingIntent open=PendingIntent.getActivity(this,0,new Intent(this,MainActivity.class),PendingIntent.FLAG_IMMUTABLE);
        startForeground(1,new Notification.Builder(this,"downloads").setContentTitle("FB MultiEngine").setContentText("Downloading to this device").setSmallIcon(android.R.drawable.stat_sys_download).setContentIntent(open).setOngoing(true).build());
        if(working.compareAndSet(false,true)){
            stopped=false;thread=new Thread(()->{
                try{
                    db.recover();
                    while(!stopped){
                        long id=db.claim();
                        if(id<0){
                            boolean pending=false;for(Map<String,String> j:db.rows())if(j.get("status").equals("retry")||j.get("status").equals("queued"))pending=true;
                            if(!pending)break;Thread.sleep(300);continue;
                        }
                        active=id;download(id);active=-1;
                    }
                }catch(InterruptedException ignored){Thread.currentThread().interrupt();}
                finally{working.set(false);stopForeground(STOP_FOREGROUND_REMOVE);stopSelf();}
            },"fbmd-downloads");thread.start();
        }
        return START_NOT_STICKY;
    }
    @Override public void onDestroy(){stopped=true;if(active>=0){db.pause();YoutubeDL.getInstance().destroyProcessById("job-"+active);}super.onDestroy();}
    @Override public void onTimeout(int startId,int fgsType){stopped=true;db.pause();stopSelf();}
    private void check(long id)throws Paused{String status=db.job(id).get("status");if(stopped||status.equals("paused")||status.equals("cancelled"))throw new Paused();}
    private void download(long id){
        Map<String,String> job=db.job(id);
        try{
            String url=job.get("url"),engine=job.get("engine");
            if(engine.equals("auto"))engine=URI.create(url).getPath().matches("(?i).*\\.(mp4|webm|mov|m4a|mp3|jpg|jpeg|png|gif)$")?"http":"yt-dlp";
            File file=engine.equals("http")?http(job):ytdlp(job);
            check(id);String digest=hash(file);
            for(Map<String,String> other:db.rows()){
                if(!other.get("id").equals(String.valueOf(id))&&other.get("status").equals("complete")&&other.get("sha256").equals(digest)&&new File(other.get("path")).isFile()&&hash(new File(other.get("path"))).equals(digest)){
                    if(!file.getAbsolutePath().equals(other.get("path")))file.delete();file=new File(other.get("path"));break;
                }
            }
            db.update(id,"status","complete","path",file.getAbsolutePath(),"sha256",digest,"done",file.length(),"total",file.length(),"error","");
        }catch(Paused e){if(!db.job(id).get("status").equals("cancelled"))db.update(id,"status","paused");}
        catch(Blocked e){db.update(id,"status","blocked","error","Authentication or access restriction. No bypass attempted.");}
        catch(Exception e){
            if(db.job(id).get("status").equals("paused")){db.update(id,"status","paused");return;}
            int attempts=Integer.parseInt(job.get("attempts"));
            db.update(id,"status",attempts>=3||e instanceof InvalidMedia?"failed":"retry","next_try",System.currentTimeMillis()+(1L<<attempts)*1000,"error",e.getClass().getSimpleName()+": download failed; check source, network and engine.");
        }
    }
    private File directory(long id)throws IOException{
        File base=getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);if(base==null)throw new IOException("Storage unavailable");
        File folder=new File(base,"job-"+id+"-"+db.job(id).get("fingerprint").substring(0,12));if(!folder.isDirectory()&&!folder.mkdirs())throw new IOException("Cannot create directory");return folder;
    }
    private Response connect(String url,Map<String,String> headers)throws Exception{
        for(int count=0;count<6;count++){
            URL target=new URL(QueueDb.validate(url));
            Request.Builder builder=new Request.Builder().url(target).header("Accept-Encoding","identity").header("User-Agent","FBMD/0.1");
            for(Map.Entry<String,String> entry:headers.entrySet())builder.header(entry.getKey(),entry.getValue());
            Response c=NetworkPolicy.CLIENT.newCall(builder.build()).execute();
            int status=c.code();
            if(status>=300&&status<400){String next=c.header("Location");c.close();if(next==null)throw new IOException("Missing redirect");URL resolved=new URL(target,next);if(target.getProtocol().equals("https")&&!resolved.getProtocol().equals("https"))throw new IOException("Insecure redirect");url=resolved.toString();continue;}
            return c;
        }
        throw new IOException("Too many redirects");
    }
    private File http(Map<String,String> job)throws Exception{
        long id=Long.parseLong(job.get("id"));File dir=directory(id);
        String path=URI.create(job.get("url")).getPath(),ext=".media";
        Matcher extension=Pattern.compile("(?i)(\\.(?:mp4|webm|mov|m4a|mp3|jpg|jpeg|png|gif))$").matcher(path);if(extension.find())ext=extension.group(1).toLowerCase(Locale.ROOT);
        File part=new File(dir,"media"+ext+".part"),result=new File(dir,"media"+ext);
        if(result.isFile()){
            File receipt=new File(dir,result.getName()+".sha256");
            if(!receipt.isFile()||!new String(java.nio.file.Files.readAllBytes(receipt.toPath()),java.nio.charset.StandardCharsets.UTF_8).equals(hash(result)))throw new InvalidMedia();
            return result;
        }
        long offset=part.isFile()?part.length():0;
        Map<String,String> headers=new HashMap<>();
        if(offset>0&&!job.get("etag").isEmpty()){headers.put("Range","bytes="+offset+"-");headers.put("If-Range",job.get("etag"));}else offset=0;
        Response c=connect(job.get("url"),headers);
        try{
            int status=c.code();if(status==401||status==403)throw new Blocked();
            if(status==429){long seconds=60;String retry=c.header("Retry-After");if(retry!=null){try{seconds=Math.max(1,Long.parseLong(retry));}catch(NumberFormatException e){try{seconds=Math.max(1,(java.time.ZonedDateTime.parse(retry,java.time.format.DateTimeFormatter.RFC_1123_DATE_TIME).toInstant().toEpochMilli()-System.currentTimeMillis())/1000);}catch(Exception ignored){}}}db.update(id,"status","paused","next_try",System.currentTimeMillis()+Math.min(seconds,31536000L)*1000,"error","RATE_LIMITED: waiting for server backoff before retry.");throw new Paused();}
            long total;
            if(status==206){
                String range=c.header("Content-Range");Matcher m=Pattern.compile("bytes (\\d+)-(\\d+)/(\\d+)").matcher(range==null?"":range);
                if(!m.matches()||Long.parseLong(m.group(1))!=offset||Long.parseLong(m.group(2))>=Long.parseLong(m.group(3)))throw new InvalidMedia();
                total=Long.parseLong(m.group(3));String validator=c.header("ETag");if(validator==null)validator=c.header("Last-Modified");
                if(offset>0&&!job.get("etag").equals(validator))throw new InvalidMedia();
            }else if(status==200){offset=0;total=c.body().contentLength();}else throw new IOException("HTTP failure");
            String type=c.header("Content-Type");if(type!=null&&(type.startsWith("text/")||type.contains("json")))throw new InvalidMedia();
            String validator=c.header("ETag");if(validator!=null&&validator.startsWith("W/"))validator=null;if(validator==null)validator=c.header("Last-Modified");
            db.update(id,"etag",validator==null?"":validator,"done",offset,"total",Math.max(0,total));
            if(total>0&&dir.getUsableSpace()<total-offset+1048576)throw new IOException("Storage full");
            long count=offset,last=0;
            try(InputStream in=c.body().byteStream();FileOutputStream out=new FileOutputStream(part,offset>0)){
                byte[] buffer=new byte[65536];int n;
                while((n=in.read(buffer))!=-1){check(id);if(count==0){String prefix=new String(buffer,0,Math.min(n,100),java.nio.charset.StandardCharsets.US_ASCII).trim().toLowerCase(Locale.ROOT);if(prefix.startsWith("<html")||prefix.startsWith("<!doctype html"))throw new InvalidMedia();}
                    out.write(buffer,0,n);count+=n;if(count>10L*1024*1024*1024)throw new InvalidMedia();if(System.currentTimeMillis()-last>200){db.update(id,"done",count);last=System.currentTimeMillis();}
                }
                out.getFD().sync();
            }
            if(count==0||(total>=0&&count!=total))throw new InvalidMedia();check(id);verify(part,ext);
            java.nio.file.Files.write(new File(dir,result.getName()+".sha256").toPath(),hash(part).getBytes(java.nio.charset.StandardCharsets.UTF_8));
            if(!part.renameTo(result))throw new IOException("Cannot finalize");return result;
        }finally{c.close();}
    }
    private File ytdlp(Map<String,String> job)throws Exception{
        long id=Long.parseLong(job.get("id"));File dir=directory(id);
        String host=URI.create(job.get("url")).getHost();
        if(!(host.equals("facebook.com")||host.endsWith(".facebook.com")||host.equals("fb.watch")||(BuildConfig.DEBUG&&host.equals("127.0.0.1"))))throw new InvalidMedia();
        YoutubeDL.getInstance().init(this);
        boolean nativeMerge=NativeMedia.ensureReady(this);
        YoutubeDLRequest r=new YoutubeDLRequest(job.get("url"));
        r.addOption("--no-playlist");r.addOption("--continue");r.addOption("--no-overwrites");r.addOption("--socket-timeout","20");r.addOption("--retries","1");r.addOption("--fragment-retries","1");r.addOption("-f",nativeMerge?"bv*+ba/b":"best");r.addOption("--merge-output-format","mp4");r.addOption("-o",new File(dir,"media.%(ext)s").getAbsolutePath());
        try{
            YoutubeDL.getInstance().execute(r,"job-"+id,(progress,eta,line)->{
                db.update(id,"done",progress.longValue(),"total",100);
                if(stopped||db.job(id).get("status").equals("paused")||db.job(id).get("status").equals("cancelled"))YoutubeDL.getInstance().destroyProcessById("job-"+id);
                return Unit.INSTANCE;
            });
        }catch(Exception e){
            check(id);String message=String.valueOf(e.getMessage()).toLowerCase(Locale.ROOT);
            if(message.contains("login")||message.contains("private")||message.contains("403")||message.contains("401")||message.contains("checkpoint"))throw new Blocked();throw e;
        }
        check(id);File[] files=dir.listFiles((d,n)->n.matches("media\\.(mp4|webm|mkv|mov|mp3|m4a)"));
        if(files==null||files.length!=1||files[0].length()==0)throw new InvalidMedia();verify(files[0],files[0].getName());return files[0];
    }
    private void verify(File file,String kind)throws Exception{
        if(kind.endsWith(".mp4")||kind.endsWith(".webm")||kind.endsWith(".m4a")||kind.endsWith(".mp3")){
            android.media.MediaExtractor extractor=new android.media.MediaExtractor();
            try{extractor.setDataSource(file.getAbsolutePath());if(extractor.getTrackCount()==0)throw new InvalidMedia();}
            finally{extractor.release();}
        }
    }
    public static String hash(File file)throws Exception{
        MessageDigest md=MessageDigest.getInstance("SHA-256");try(InputStream in=new FileInputStream(file)){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)md.update(b,0,n);}
        StringBuilder out=new StringBuilder();for(byte b:md.digest())out.append(String.format(Locale.ROOT,"%02x",b));return out.toString();
    }
}
