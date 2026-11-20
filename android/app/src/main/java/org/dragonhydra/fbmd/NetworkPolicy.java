package org.dragonhydra.fbmd;
import java.net.*;
import java.util.*;
import okhttp3.OkHttpClient;
import java.util.concurrent.TimeUnit;

public final class NetworkPolicy {
    static boolean denied(InetAddress a) {
        if(a.isAnyLocalAddress()||a.isLoopbackAddress()||a.isLinkLocalAddress()||a.isSiteLocalAddress()||a.isMulticastAddress())return true;
        byte[] b=a.getAddress();int first=b[0]&255;
        if(b.length==4)return first==0||first>=224||(first==100&&(b[1]&255)>=64&&(b[1]&255)<=127)||(first==198&&((b[1]&255)==18||(b[1]&255)==19));
        return (first&254)==252;
    }
    public static final OkHttpClient CLIENT=new OkHttpClient.Builder().followRedirects(false).followSslRedirects(false).connectTimeout(15,TimeUnit.SECONDS).readTimeout(30,TimeUnit.SECONDS).dns(host->{
        List<InetAddress> addresses=Arrays.asList(InetAddress.getAllByName(host));
        boolean fixture=BuildConfig.DEBUG&&(host.equals("127.0.0.1")||host.equals("10.0.2.2"));
        if(!fixture)for(InetAddress a:addresses)if(denied(a))throw new UnknownHostException("Private network target blocked");
        return addresses;
    }).build();
}
