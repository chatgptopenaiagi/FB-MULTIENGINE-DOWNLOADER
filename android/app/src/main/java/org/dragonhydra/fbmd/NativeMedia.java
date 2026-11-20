package org.dragonhydra.fbmd;
import android.content.Context;
import android.media.MediaExtractor;
import android.media.MediaFormat;
import android.os.Build;
import com.yausername.youtubedl_android.YoutubeDL;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.TimeUnit;
import org.json.JSONObject;

/** Self-test uses bundled synthetic media only; never uploads data or inspects user credentials. */
public final class NativeMedia {
    private static Boolean ready;
    public static synchronized boolean ensureReady(Context context){
        if(ready!=null)return ready;
        JSONObject report=new JSONObject();
        try{
            YoutubeDL.getInstance().init(context);extractRuntime(context);
            report.put("abi",Build.SUPPORTED_ABIS[0]);
            File executable=new File(context.getApplicationInfo().nativeLibraryDir,"libffmpeg.so");
            String version=run(context,Arrays.asList(executable.getAbsolutePath(),"-version"));
            if(!version.startsWith("ffmpeg version "))throw new IOException("Version probe failed");
            report.put("version",version.split("\n")[0]);
            File dir=new File(context.getCacheDir(),"native-self-test");if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException();
            for(String name:new String[]{"video.mp4","audio.m4a"})try(InputStream in=context.getAssets().open("fixtures/"+name);OutputStream out=new FileOutputStream(new File(dir,name))){byte[] b=new byte[65536];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}
            File result=new File(dir,"merged.mp4");
            run(context,Arrays.asList(executable.getAbsolutePath(),"-nostdin","-y","-v","error","-i",new File(dir,"video.mp4").getAbsolutePath(),"-i",new File(dir,"audio.m4a").getAbsolutePath(),"-map","0:v:0","-map","1:a:0","-c","copy",result.getAbsolutePath()));
            MediaExtractor extractor=new MediaExtractor();boolean video=false,audio=false;long duration=0;
            try{extractor.setDataSource(result.getAbsolutePath());for(int i=0;i<extractor.getTrackCount();i++){MediaFormat f=extractor.getTrackFormat(i);String mime=f.getString(MediaFormat.KEY_MIME);video|=mime.startsWith("video/");audio|=mime.startsWith("audio/");if(f.containsKey(MediaFormat.KEY_DURATION))duration=Math.max(duration,f.getLong(MediaFormat.KEY_DURATION));}}finally{extractor.release();}
            if(!video||!audio||duration<2800000||duration>3300000)throw new IOException("Stream validation failed");
            run(context,Arrays.asList(executable.getAbsolutePath(),"-nostdin","-v","error","-xerror","-i",result.getAbsolutePath(),"-f","null","-"));
            report.put("status","READY");report.put("local_merge_test","PASS");report.put("video",video);report.put("audio",audio);report.put("duration_us",duration);report.put("sha256",DownloadService.hash(result));ready=true;
        }catch(Exception e){ready=false;try{report.put("status","UNAVAILABLE");report.put("detail",e.getClass().getSimpleName()+": native media self-test failed; progressive downloads remain available");}catch(Exception ignored){}}
        context.getSharedPreferences("native-engine",0).edit().putString("report",report.toString()).apply();
        return ready;
    }
    private static String run(Context context,List<String> args)throws Exception{
        File base=new File(context.getNoBackupFilesDir(),"youtubedl-android/packages");
        File log=File.createTempFile("native-test-",".log",context.getCacheDir());
        ProcessBuilder builder=new ProcessBuilder(args).redirectErrorStream(true).redirectOutput(log);
        // Match the wrapper's library order: its Python runtime includes Android-compatible
        // variants of libraries also shipped by FFmpeg (notably liblzma).
        builder.environment().put("LD_LIBRARY_PATH",new File(base,"python/usr/lib").getAbsolutePath()+":"+new File(base,"ffmpeg/usr/lib").getAbsolutePath());
        Process process=builder.start();if(!process.waitFor(45,TimeUnit.SECONDS)){process.destroyForcibly();throw new IOException("Native timeout");}
        if(process.exitValue()!=0)throw new IOException("Native process failed");
        String output=new String(java.nio.file.Files.readAllBytes(log.toPath()),StandardCharsets.UTF_8);log.delete();return output;
    }
    private static void extractRuntime(Context context)throws Exception{
        String abi=Build.SUPPORTED_ABIS[0];
        File folder=new File(context.getNoBackupFilesDir(),"youtubedl-android/packages/ffmpeg");
        if(!folder.isDirectory()&&!folder.mkdirs())throw new IOException("Runtime folder unavailable");
        File marker=new File(folder,"fbmd-runtime-v3");
        if(marker.isFile())return;
        try(java.util.zip.ZipInputStream zip=new java.util.zip.ZipInputStream(context.getAssets().open("native/ffmpeg-"+abi+".zip"))){
            java.util.zip.ZipEntry entry;byte[] buffer=new byte[65536];
            while((entry=zip.getNextEntry())!=null){if(entry.isDirectory())continue;File file=new File(folder,entry.getName());if(!file.getCanonicalPath().startsWith(folder.getCanonicalPath()+File.separator))throw new IOException("Unsafe runtime path");if(!file.getParentFile().isDirectory()&&!file.getParentFile().mkdirs())throw new IOException();try(OutputStream out=new FileOutputStream(file)){int n;while((n=zip.read(buffer))!=-1)out.write(buffer,0,n);}}
        }
        java.nio.file.Files.write(marker.toPath(),"0.2.0-alpha.1".getBytes(StandardCharsets.UTF_8));
    }
    public static String report(Context c){return c.getSharedPreferences("native-engine",0).getString("report","Native engine self-test pending");}
}
