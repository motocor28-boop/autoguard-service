from pathlib import Path
import re

ROOT = Path('mobile-scanner/pro-v2/project')
main_path = ROOT / 'app/src/main/java/com/autoguard/mobilepro/MainActivity.java'
obd_path = ROOT / 'app/src/main/java/com/autoguard/mobilepro/ObdClient.java'
build_path = ROOT / 'app/build.gradle'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'No se encontró bloque requerido: {label}')
    return text.replace(old, new, 1)

main = main_path.read_text(encoding='utf-8')
if 'java.util.concurrent.atomic.AtomicBoolean' not in main:
    main = replace_once(main, 'import java.util.concurrent.TimeUnit;', 'import java.util.concurrent.TimeUnit;\nimport java.util.concurrent.atomic.AtomicBoolean;', 'import AtomicBoolean')
if 'liveReadBusy' not in main:
    main = replace_once(main, '    private boolean monitoring;', '    private boolean monitoring;\n    private final AtomicBoolean liveReadBusy = new AtomicBoolean(false);\n    private final Map<String,Long> sensorUpdateTimes = new LinkedHashMap<>();\n    private int liveUpdateCount;\n    private long lastRpmUpdateAt;', 'campos de monitoreo')
main = main.replace('Mobile Scanner Pro v2.0', 'Mobile Scanner Pro v2.1')
pattern = re.compile(r'    private void readSensors\(\)\{.*?\n    private void updateSensors\(Map<String,Double> result\)\{.*?\n    private void toggleMonitor\(\)\{.*?\n    private void stopMonitor\(\)\{.*?\n', re.S)
replacement = '''    private void readSensors(){
        if(!connected()||!licensed())return;
        List<SensorSpec> chosen=selected();
        if(chosen.isEmpty()){toast("Seleccione sensores");return;}
        if(!liveReadBusy.compareAndSet(false,true)){status.setText("Lectura en curso...");return;}
        io.execute(()->{try{
            Map<String,Double> result=client.readSensors(chosen);
            runOnUiThread(()->updateSensors(result));
        }catch(Exception e){runOnUiThread(()->error(e.getMessage()));}
        finally{liveReadBusy.set(false);}});
    }

    private void pollSensors(){
        if(!monitoring||client==null||!client.isConnected())return;
        if(!liveReadBusy.compareAndSet(false,true))return;
        try{
            Map<String,Double> result=client.readSensorCycle(selected());
            runOnUiThread(()->updateSensors(result));
        }catch(Exception e){runOnUiThread(()->status.setText("Error temporal: "+e.getMessage()));}
        finally{liveReadBusy.set(false);}
    }

    private void updateSensors(Map<String,Double> result){
        long now=System.currentTimeMillis();
        liveUpdateCount++;
        for(Map.Entry<String,Double> e:result.entrySet()){
            String key=e.getKey(); Double value=e.getValue(); TextView t=values.get(key); SensorSpec s=catalog.get(key);
            if(value!=null){
                latest.put(key,value); sensorUpdateTimes.put(key,now); if("rpm".equals(key))lastRpmUpdateAt=now;
                if(t!=null){String label=s==null?"Voltaje adaptador":s.label; t.setText(label+": "+(s==null?String.format(Locale.US,"%.1f V",value):s.format(value)));}
            }else if(t!=null&&"rpm".equals(key)){t.setText("RPM motor: SIN DATOS");}
        }
        for(Map.Entry<String,Long> stamp:sensorUpdateTimes.entrySet())if(now-stamp.getValue()>7000L){TextView t=values.get(stamp.getKey());if(t!=null)t.setText((catalog.get(stamp.getKey())==null?"Sensor":catalog.get(stamp.getKey()).label)+": DESACTUALIZADO");}
        String rpmState=lastRpmUpdateAt==0L?"RPM sin respuesta":now-lastRpmUpdateAt>3500L?"RPM desactualizado":"RPM actualizado";
        status.setText("Ciclo #"+liveUpdateCount+" · "+rpmState+" · "+result.size()+" PIDs");
    }

    private void toggleMonitor(){
        if(monitoring){stopMonitor();return;}
        if(!connected()||!licensed())return;
        monitoring=true; liveUpdateCount=0; lastRpmUpdateAt=0L;
        liveLoop=Executors.newSingleThreadScheduledExecutor();
        liveLoop.scheduleWithFixedDelay(this::pollSensors,0,900,TimeUnit.MILLISECONDS);
        toast("Monitoreo RPM prioritario iniciado");
    }
    private void stopMonitor(){monitoring=false;if(liveLoop!=null)liveLoop.shutdownNow();liveLoop=null;liveReadBusy.set(false);}
'''
main, count = pattern.subn(replacement, main, count=1)
if count != 1:
    raise RuntimeError('No se pudo reemplazar bloque de monitoreo en MainActivity')
main_path.write_text(main, encoding='utf-8')

obd = obd_path.read_text(encoding='utf-8')
if 'SocketTimeoutException' not in obd:
    obd = replace_once(obd, 'import java.net.Socket;', 'import java.net.Socket;\nimport java.net.SocketTimeoutException;', 'SocketTimeoutException')
if 'import java.util.HashSet;' not in obd:
    obd = replace_once(obd, 'import java.util.UUID;', 'import java.util.UUID;\nimport java.util.HashSet;\nimport java.util.Set;', 'Set imports')
if 'supportedCommands' not in obd:
    obd = replace_once(obd, '    private int simulatorCycle;', '    private int simulatorCycle;\n    private int liveCycleIndex;\n    private final Set<String> supportedCommands = new HashSet<>();\n    private boolean supportedPidMapKnown;', 'campos OBD')
obd = obd.replace('safeQuery("0100");', 'detectSupportedPids();', 1)
obd = obd.replace('AUTOGUARD ELM327 PRO v2.0', 'AUTOGUARD ELM327 PRO v2.1')
query_pattern = re.compile(r'    public synchronized String query\(String command\) throws IOException \{.*?\n    private String safeQuery', re.S)
query_replacement = '''    public synchronized String query(String command) throws IOException { return query(command,2400); }

    public synchronized String query(String command,int timeoutMs) throws IOException {
        if(!connected)throw new IOException("Adaptador no conectado.");
        String normalized=command.trim().toUpperCase(Locale.ROOT).replace(" ","");
        if(mode==Mode.SIMULATOR)return simulatorResponse(normalized);
        drainInput();
        if(wifiSocket!=null)wifiSocket.setSoTimeout(Math.max(900,timeoutMs));
        output.write((normalized+"\\r").getBytes(StandardCharsets.US_ASCII));output.flush();
        ByteArrayOutputStream buffer=new ByteArrayOutputStream();
        long deadline=System.currentTimeMillis()+Math.max(900,timeoutMs);
        try{while(System.currentTimeMillis()<deadline){int value=input.read();if(value<0||value=='>')break;buffer.write(value);}}
        catch(SocketTimeoutException timeout){if(buffer.size()==0)throw new IOException("Tiempo de espera agotado en "+normalized);}
        String response=buffer.toString(StandardCharsets.US_ASCII);
        if(response.isBlank())throw new IOException("ELM327 no respondió a "+normalized);
        return response;
    }

    private void drainInput() throws IOException {
        if(input==null)return;int drained=0;long until=System.currentTimeMillis()+80L;
        while(System.currentTimeMillis()<until&&drained<2048){int available=input.available();if(available<=0)break;for(int i=0;i<available&&drained<2048;i++){if(input.read()<0)return;drained++;}}
    }

    private String safeQuery'''
obd, count = query_pattern.subn(query_replacement, obd, count=1)
if count != 1:
    raise RuntimeError('No se pudo reemplazar query OBD')
sensor_pattern = re.compile(r'    public synchronized Map<String, Double> readSensors\(List<SensorSpec> selected\) throws IOException \{.*?\n    public synchronized List<DtcEntry> readAllDtcs', re.S)
sensor_replacement = '''    private void detectSupportedPids(){
        supportedCommands.clear();supportedPidMapKnown=false;int[] bases={0x00,0x20,0x40,0x60};
        for(int base:bases){String command=String.format(Locale.US,"01%02X",base);String response;try{response=query(command,2800);}catch(Exception e){break;}
            int[] payload=findPidPayload(response,base,4);if(payload==null)break;supportedPidMapKnown=true;
            long mask=((long)payload[0]<<24)|((long)payload[1]<<16)|((long)payload[2]<<8)|payload[3];
            for(int bit=0;bit<32;bit++)if((mask&(1L<<(31-bit)))!=0)supportedCommands.add(String.format(Locale.US,"01%02X",base+bit+1));
            if(!supportedCommands.contains(String.format(Locale.US,"01%02X",base+0x20)))break;
        }
    }
    private boolean isSupported(SensorSpec spec){return !supportedPidMapKnown||supportedCommands.contains(spec.command);}
    private Double readSensor(SensorSpec spec,int timeoutMs){if(!isSupported(spec))return null;try{return spec.decode(query(spec.command,timeoutMs));}catch(Exception e){return null;}}

    public synchronized Map<String,Double> readSensorCycle(List<SensorSpec> selected) throws IOException {
        LinkedHashMap<String,Double> result=new LinkedHashMap<>();SensorSpec rpm=null;ArrayList<SensorSpec> others=new ArrayList<>();
        for(SensorSpec spec:selected){if("rpm".equals(spec.key))rpm=spec;else if(isSupported(spec))others.add(spec);}if(rpm==null)rpm=SensorSpec.catalog().get("rpm");
        Double rpmValue=readSensor(rpm,1500);if(rpmValue==null){safeQuery("ATE0");safeQuery("ATL0");safeQuery("ATS1");safeQuery("ATH0");rpmValue=readSensor(rpm,1900);}result.put("rpm",rpmValue);
        int count=Math.min(3,others.size());for(int i=0;i<count;i++){SensorSpec spec=others.get((liveCycleIndex+i)%others.size());result.put(spec.key,readSensor(spec,1500));}
        liveCycleIndex=others.isEmpty()?0:(liveCycleIndex+count)%others.size();
        if(liveCycleIndex%3==0)try{Matcher m=Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*V",Pattern.CASE_INSENSITIVE).matcher(query("ATRV",1200));result.put("battery",m.find()?Double.parseDouble(m.group(1)):null);}catch(Exception e){result.put("battery",null);}
        return result;
    }

    public synchronized Map<String, Double> readSensors(List<SensorSpec> selected) throws IOException {
        LinkedHashMap<String,Double> values=new LinkedHashMap<>();
        for(SensorSpec spec:selected){if(!isSupported(spec)){values.put(spec.key,null);continue;}values.put(spec.key,readSensor(spec,1800));}
        try{Matcher matcher=Pattern.compile("(\\d+(?:\\.\\d+)?)\\s*V",Pattern.CASE_INSENSITIVE).matcher(query("ATRV",1200));values.put("battery",matcher.find()?Double.parseDouble(matcher.group(1)):null);}catch(Exception ignored){values.put("battery",null);}return values;
    }

    public synchronized List<DtcEntry> readAllDtcs'''
obd, count = sensor_pattern.subn(sensor_replacement, obd, count=1)
if count != 1:
    raise RuntimeError('No se pudo reemplazar lectura de sensores OBD')
obd_path.write_text(obd, encoding='utf-8')

build = build_path.read_text(encoding='utf-8').replace('versionCode 20','versionCode 21').replace("versionName '2.0.0-pro'","versionName '2.1.0-pro'")
build_path.write_text(build, encoding='utf-8')
print('Corrección RPM v2.1 aplicada')
