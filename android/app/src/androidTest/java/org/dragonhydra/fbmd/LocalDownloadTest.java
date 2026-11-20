package org.dragonhydra.fbmd;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import static org.junit.Assert.*;
import android.content.Context;
import android.content.Intent;
import java.io.File;
import java.util.Map;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;

public class LocalDownloadTest {
    @Test
    public void testStandaloneHttpPauseResumeAndNativeExtractor() throws Exception {
        Context ctx=InstrumentationRegistry.getInstrumentation().getTargetContext();QueueDb db=new QueueDb(ctx);
        Intent activity=new Intent(ctx,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        ctx.startActivity(activity);Thread.sleep(1200);
        assertTrue("Bundled FFmpeg self-test: "+NativeMedia.report(ctx),NativeMedia.ensureReady(ctx));
        long id=db.add("http://127.0.0.1:18765/slow.mp4","http");
        assertEquals(id,db.add("http://127.0.0.1:18765/slow.mp4","http"));
        ctx.startForegroundService(new Intent(ctx,DownloadService.class));
        long end=System.currentTimeMillis()+30000;
        while(Long.parseLong(db.job(id).get("done"))<8192&&System.currentTimeMillis()<end)Thread.sleep(50);
        db.pause();Thread.sleep(1500);
        assertEquals("paused",db.job(id).get("status"));
        QueueDb reopened=new QueueDb(ctx);reopened.resume();ctx.startForegroundService(new Intent(ctx,DownloadService.class));
        Map<String,String> job=waitFor(reopened,id);
        assertEquals("complete",job.get("status"));assertTrue(new File(job.get("path")).length()>10000);
        assertEquals(job.get("sha256"),DownloadService.hash(new File(job.get("path"))));
        android.media.MediaExtractor media=new android.media.MediaExtractor();media.setDataSource(job.get("path"));assertTrue(media.getTrackCount()>=2);media.release();
        long nativeId=reopened.add("http://127.0.0.1:18765/sample.mp4","yt-dlp");
        ctx.startForegroundService(new Intent(ctx,DownloadService.class));
        Map<String,String> nativeJob=waitFor(reopened,nativeId);
        assertEquals("Native yt-dlp: "+nativeJob.get("error"),"complete",nativeJob.get("status"));
        assertEquals(job.get("sha256"),nativeJob.get("sha256"));
        assertEquals(job.get("path"),nativeJob.get("path"));
        long denied=reopened.add("http://127.0.0.1:18765/blocked.mp4","http");ctx.startForegroundService(new Intent(ctx,DownloadService.class));
        assertEquals("blocked",waitFor(reopened,denied).get("status"));
        reopened.vault.put("test-dummy","dummy-value-1827");assertEquals("dummy-value-1827",reopened.vault.get("test-dummy"));
        String ciphertext=ctx.getSharedPreferences("vault",0).getString("test-dummy","");assertFalse(ciphertext.contains("dummy-value-1827"));
        assertEquals(db.rows().size(),new QueueDb(ctx).rows().size());
    }
    private Map<String,String> waitFor(QueueDb db,long id)throws Exception{
        long end=System.currentTimeMillis()+90000;
        while(System.currentTimeMillis()<end){Map<String,String> j=db.job(id);if(j.get("status").equals("complete")||j.get("status").equals("failed")||j.get("status").equals("blocked"))return j;Thread.sleep(200);}
        return db.job(id);
    }
}
