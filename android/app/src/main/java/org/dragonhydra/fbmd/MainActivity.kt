package org.dragonhydra.fbmd

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.documentfile.provider.DocumentFile
import kotlinx.coroutines.delay
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class MainActivity : ComponentActivity() {
    private lateinit var db: QueueDb
    private var message by mutableStateOf("Paste one accessible video URL per line. Files download on this device.")
    private var input by mutableStateOf("")
    private var nativeStatus by mutableStateOf("Native engines: checking bundled runtime…")
    private val export = registerForActivityResult(ActivityResultContracts.OpenDocumentTree()) { uri ->
        if (uri != null) {
            contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            Thread {
                try {
                    val dir = DocumentFile.fromTreeUri(this, uri) ?: error("Folder unavailable")
                    var count = 0
                    for (job in db.rows().filter { it["status"] == "complete" }) {
                        val file = File(job["path"]!!)
                        val name = "fbmd-${job["id"]}-${job["sha256"]!!.take(10)}.${file.extension}"
                        if (dir.findFile(name) != null) continue
                        val target = dir.createFile(if(file.extension == "mp4") "video/mp4" else "application/octet-stream", name) ?: error("Cannot create file")
                        contentResolver.openOutputStream(target.uri)?.use { out -> file.inputStream().use { it.copyTo(out) } } ?: error("Cannot write file")
                        count++
                    }
                    runOnUiThread { message = "$count files copied to the selected folder; existing files preserved." }
                } catch (e: Exception) { runOnUiThread { message = "Export failed: ${e.javaClass.simpleName}. Check folder access." } }
            }.start()
        }
    }
    private val notifications = registerForActivityResult(ActivityResultContracts.RequestPermission()) { }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        db = QueueDb(this)
        Thread { NativeMedia.ensureReady(this); runOnUiThread { nativeStatus=NativeMedia.report(this) } }.start()
        if (intent.action == Intent.ACTION_SEND) input = intent.getStringExtra(Intent.EXTRA_TEXT) ?: ""
        if (Build.VERSION.SDK_INT >= 33) notifications.launch(Manifest.permission.POST_NOTIFICATIONS)
        setContent {
            MaterialTheme(colorScheme = darkColorScheme(primary = Color(0xFF6DDAC6), background = Color(0xFF101827), surface = Color(0xFF182438))) {
                Surface(Modifier.fillMaxSize()) { App() }
            }
        }
    }
    private fun startQueue() { startForegroundService(Intent(this, DownloadService::class.java)) }
    private fun add(engine: String) {
        try {
            val urls = input.lines().filter { it.isNotBlank() }
            require(urls.size <= 100) { "Batch limit: 100 URLs" }
            val count = urls.map { db.add(it.trim(),engine) }.distinct().size
            input="";message="$count unique jobs accepted. Tap Start to download."
        } catch(e: Exception) { message="Invalid input. Use up to 100 public HTTP(S) URLs, one per line." }
    }
    @Composable private fun App() {
        var jobs by remember { mutableStateOf(db.rows()) }
        var tab by remember { mutableIntStateOf(0) }
        var engine by remember { mutableStateOf("auto") }
        var token by remember { mutableStateOf("") }
        var objectId by remember { mutableStateOf("me") }
        LaunchedEffect(Unit) { while(true) { jobs=db.rows();delay(500) } }
        Column(Modifier.fillMaxSize().systemBarsPadding().padding(20.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Text("FB MULTIENGINE",style=MaterialTheme.typography.headlineSmall)
            Text("Local media · persistent queue",color=MaterialTheme.colorScheme.primary)
            Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                listOf("Queue","Accounts","Engines","Help").forEachIndexed { i,s -> FilterChip(selected=tab==i,onClick={tab=i},label={Text(s)}) }
            }
            when(tab) {
                0 -> {
                    OutlinedTextField(value=input,onValueChange={input=it},label={Text("Media URLs · one per line")},modifier=Modifier.fillMaxWidth(),minLines=2,maxLines=4)
                    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        listOf("auto","http","yt-dlp").forEach { e -> FilterChip(engine==e,{engine=e},label={Text(e)}) }
                    }
                    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        Button(onClick={add(engine)}){Text("Add")}
                        Button(onClick={startQueue()}){Text("Start")}
                        OutlinedButton(onClick={db.pause();message="Pause requested; partial files retained."}){Text("Pause")}
                    }
                    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick={db.resume();startQueue()}){Text("Resume / retry")}
                        OutlinedButton(onClick={export.launch(null)}){Text("Save to folder")}
                    }
                    Text("${jobs.size} jobs · ${jobs.count { it["status"]=="complete" }} complete")
                    LazyColumn(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                        items(jobs,key={it["id"]!!}) { j ->
                            Card(Modifier.fillMaxWidth()) {
                                Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                                    Text("#${j["id"]} · ${j["status"]} · ${j["engine"]}",style=MaterialTheme.typography.titleSmall)
                                    Text(j["display"]!!,maxLines=2,style=MaterialTheme.typography.bodySmall)
                                    val done=j["done"]!!.toLong();val total=j["total"]!!.toLong()
                                    if(total>0) LinearProgressIndicator(progress={ (done.toFloat()/total).coerceIn(0f,1f) },modifier=Modifier.fillMaxWidth())
                                    Text(if(j["status"]=="running"&&total==100L) "$done% · yt-dlp" else "${done/1024} KiB / ${if(total>0) "${total/1024} KiB" else "unknown"}",style=MaterialTheme.typography.bodySmall)
                                    if(!j["error"].isNullOrEmpty())Text(j["error"]!!,color=MaterialTheme.colorScheme.error,style=MaterialTheme.typography.bodySmall)
                                    if(j["status"]!="complete"&&j["status"]!="cancelled")TextButton(onClick={db.cancel(j["id"]!!.toLong())}){Text("Cancel")}
                                }
                            }
                        }
                    }
                }
                1 -> {
                    Text("Meta API · optional",style=MaterialTheme.typography.titleLarge)
                    Text("No Meta app is configured for OAuth. An existing authorized token can probe its own identity or an explicitly permitted video object. Arbitrary profile downloads are not granted by a token.")
                    OutlinedTextField(token,{token=it},label={Text("Authorized access token")},visualTransformation=PasswordVisualTransformation(),modifier=Modifier.fillMaxWidth())
                    Button(onClick={if(token.isNotBlank()){db.vault.put("meta-token",token.trim());token="";message="Token encrypted using Android Keystore."}}){Text("Save token encrypted")}
                    OutlinedTextField(objectId,{objectId=it},label={Text("Object ID or me")},modifier=Modifier.fillMaxWidth())
                    Button(onClick={lookup(objectId)}){Text("Probe authorized object")}
                    OutlinedButton(onClick={db.vault.forget();message="Local credentials removed. Revoke upstream access in Facebook settings if required."}){Text("Forget credentials")}
                    Text("Browser session capture and bulk profile discovery are desktop-only. Facebook Login in embedded WebViews is not supported.")
                    Spacer(Modifier.weight(1f))
                }
                2 -> {
                    Text("Native media engines",style=MaterialTheme.typography.titleLarge)
                    Text(nativeStatus,style=MaterialTheme.typography.bodySmall)
                    Text("READY requires this device to execute the bundled FFmpeg, merge the included synthetic audio/video fixture, inspect both tracks and decode the result. Files and credentials stay local.")
                    Text("Python and yt-dlp are embedded. This APK contains ARM64 and x86_64 libraries; architecture presence alone does not establish runtime compatibility.")
                    Spacer(Modifier.weight(1f))
                }
                else -> {
                    Text("Use a public media link or an accessible Facebook video / Reel. Share a link from your browser to FB MultiEngine, add it, then tap Start.")
                    Text("Downloads run in a foreground service on this device. The queue survives app restarts. Resume restarts unsupported servers from byte zero; stable HTTP ranges retain progress.")
                    Text("Save to folder uses Android's folder picker to copy completed files. Internal downloads are removed when the app is uninstalled. Export them first.")
                    Text("Bundled FFmpeg enables separate audio/video merging only after an on-device runtime test passes. Browser session discovery and quality selection are desktop-only. No remote downloader service receives your links or credentials.")
                    Text("Version 0.2.0-alpha.1 · native ARM64 / x86_64 engine")
                    OutlinedButton(onClick={startActivity(Intent(Intent.ACTION_VIEW,Uri.parse("https://github.com/chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER")))}){Text("Project and evidence")}
                    Spacer(Modifier.weight(1f))
                }
            }
            Text(message,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.primary)
        }
    }
    private fun lookup(id:String) {
        if(!id.matches(Regex("me|[0-9]+"))){message="Use a numeric object ID or me.";return}
        val token=db.vault.get("meta-token") ?: run { message="Save an authorized token first.";return }
        Thread {
            try {
                val fields=if(id=="me") "id,name" else "id,source"
                val c=URL("https://graph.facebook.com/v27.0/$id?fields=$fields").openConnection() as HttpURLConnection
                c.instanceFollowRedirects=false;c.connectTimeout=15000;c.readTimeout=25000;c.setRequestProperty("Authorization","Bearer $token")
                try {
                    if(c.responseCode!=200){runOnUiThread {message="Meta rejected this capability (HTTP ${c.responseCode}); check app, object and permissions."};return@Thread}
                    val result=JSONObject(c.inputStream.bufferedReader().use{it.readText()})
                    if(result.has("source")){db.add(result.getString("source"),"http");runOnUiThread{message="Authorized media source queued."}}
                    else runOnUiThread { message="Token accepted; no downloadable media source returned." }
                } finally {c.disconnect()}
            } catch(e:Exception){runOnUiThread{message="Meta request failed: ${e.javaClass.simpleName}."}}
        }.start()
    }
}
