package com.autoguard.mobilepro;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public final class MainActivity extends Activity {
    private static final int ORANGE = Color.rgb(249,115,22), TEXT = Color.rgb(249,250,251), MUTED = Color.rgb(209,213,219), BG = Color.rgb(11,15,20), GREEN = Color.rgb(34,197,94), RED = Color.rgb(239,68,68);
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private ScheduledExecutorService liveLoop;
    private final Map<String,SensorSpec> catalog = SensorSpec.catalog();
    private final Map<String,CheckBox> checks = new LinkedHashMap<>();
    private final Map<String,TextView> values = new LinkedHashMap<>();
    private final Map<String,Double> latest = new LinkedHashMap<>();
    private final Map<String,String> vehicle = new LinkedHashMap<>();
    private final List<ObdClient.DtcEntry> dtcs = new ArrayList<>();
    private final List<BluetoothDevice> btDevices = new ArrayList<>();
    private final Map<String,View> screens = new LinkedHashMap<>();
    private FrameLayout container;
    private TextView status, dtcText, licenseText;
    private Spinner modeSpinner, btSpinner;
    private EditText host, port;
    private ObdClient client;
    private ObdClient.SessionInfo session;
    private boolean monitoring;
    private LicenseManager.LicenseStatus license;

    @Override protected void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(BG); getWindow().setNavigationBarColor(BG);
        license = LicenseManager.status(this);
        setContentView(buildApp());
        refreshBluetooth();
        show("Inicio");
    }

    private View buildApp() {
        LinearLayout root=v(); root.setBackgroundColor(BG); root.setPadding(dp(10),dp(8),dp(10),dp(10));
        LinearLayout head=h(); head.setGravity(Gravity.CENTER_VERTICAL);
        ImageView logo=new ImageView(this); logo.setImageResource(R.drawable.autoguard_logo); logo.setScaleType(ImageView.ScaleType.CENTER_INSIDE); head.addView(logo,new LinearLayout.LayoutParams(dp(70),dp(70)));
        LinearLayout brand=v(); brand.addView(txt("AUTOGUARD SERVICIOS",21,ORANGE,true)); brand.addView(txt("Mobile Scanner Pro v2.0",15,TEXT,true)); brand.addView(txt("OBD-II · Sensores · Pruebas · PDF · Licencias",11,MUTED,false)); head.addView(brand,new LinearLayout.LayoutParams(0,-2,1)); root.addView(head);
        status=box("Listo para trabajar. Demo/licencia: "+license.plan); root.addView(status,mp(6));
        HorizontalScrollView navScroll=new HorizontalScrollView(this); LinearLayout nav=h();
        for(String name:new String[]{"Inicio","Conexión","Datos","Diagnóstico","Pruebas","Informe","Licencia"}){ Button b=secondary(name); b.setOnClickListener(x->show(name)); nav.addView(b); }
        navScroll.addView(nav); root.addView(navScroll,mp(6));
        container=new FrameLayout(this); root.addView(container,new LinearLayout.LayoutParams(-1,0,1));
        screens.put("Inicio",dashboard()); screens.put("Conexión",connection()); screens.put("Datos",live()); screens.put("Diagnóstico",diagnostic()); screens.put("Pruebas",tests()); screens.put("Informe",report()); screens.put("Licencia",licensing());
        return root;
    }

    private View dashboard(){ LinearLayout c=v(); c.addView(title("Centro de control")); c.addView(box("La ficha del vehículo es opcional. Puede conectar y escanear sin ingresar datos."));
        Button f=primary("Ficha opcional del vehículo"); f.setOnClickListener(x->vehicleDialog()); c.addView(f,mp(8));
        c.addView(box("Conexión: use WiFi 192.168.0.10:35000, Bluetooth Classic enlazado o Simulador."),mp(6));
        Button a=secondary("Conectar ELM327"); a.setOnClickListener(x->show("Conexión")); c.addView(a);
        Button b=secondary("Seleccionar sensores"); b.setOnClickListener(x->show("Datos")); c.addView(b);
        Button d=secondary("Pruebas funcionales guiadas"); d.setOnClickListener(x->show("Pruebas")); c.addView(d);
        return scroll(c); }

    private View connection(){ LinearLayout c=v(); c.addView(title("Conexión profesional ELM327")); c.addView(box("WiFi es prioritario. Bluetooth requiere enlazar el adaptador previamente en Ajustes de Android."));
        modeSpinner=spinner(new String[]{"WiFi","Bluetooth Classic","Simulador"}); labeled(c,"Modo",modeSpinner);
        host=edit("192.168.0.10"); host.setText("192.168.0.10"); labeled(c,"IP",host);
        port=edit("35000"); port.setText("35000"); labeled(c,"Puerto",port);
        btSpinner=spinner(new String[]{"Sin dispositivos"}); labeled(c,"Bluetooth enlazado",btSpinner);
        Button refresh=secondary("Actualizar Bluetooth"); refresh.setOnClickListener(x->refreshBluetooth()); c.addView(refresh);
        Button connect=primary("Conectar / desconectar"); connect.setOnClickListener(x->toggleConnect()); c.addView(connect,mp(8)); return scroll(c); }

    private View live(){ LinearLayout c=v(); c.addView(title("Datos en vivo seleccionables")); c.addView(box("Marque solo los sensores necesarios. Las consultas son secuenciales para no saturar el ELM327 WiFi."));
        LinearLayout choices=v(); Set<String> saved=getSharedPreferences("ag",MODE_PRIVATE).getStringSet("sensors",null);
        for(SensorSpec s:catalog.values()){ CheckBox cb=new CheckBox(this); cb.setText(s.label+" ["+s.unit+"]"); cb.setTextColor(TEXT); cb.setChecked(saved==null?SensorSpec.essentialKeys().contains(s.key):saved.contains(s.key)); checks.put(s.key,cb); choices.addView(cb); }
        c.addView(choices);
        LinearLayout actions=h(); Button essential=secondary("Esenciales"); essential.setOnClickListener(x->selectEssential()); Button all=secondary("Todos"); all.setOnClickListener(x->setAll(true)); actions.addView(essential); actions.addView(all); c.addView(actions);
        Button once=primary("Lectura única"); once.setOnClickListener(x->readSensors()); c.addView(once,mp(4)); Button monitor=secondary("Iniciar / detener monitoreo"); monitor.setOnClickListener(x->toggleMonitor()); c.addView(monitor);
        for(SensorSpec s:catalog.values()){ TextView val=box(s.label+": --"); values.put(s.key,val); c.addView(val,mp(3)); }
        TextView batt=box("Voltaje adaptador: --"); values.put("battery",batt); c.addView(batt); return scroll(c); }

    private View diagnostic(){ LinearLayout c=v(); c.addView(title("Diagnóstico OBD-II")); Button scan=primary("Leer DTC confirmados, pendientes y permanentes"); scan.setOnClickListener(x->readDtcs()); c.addView(scan,mp(5)); Button clear=secondary("Borrar DTC con confirmación"); clear.setOnClickListener(x->confirmClear()); c.addView(clear); dtcText=box("Sin lectura de códigos."); c.addView(dtcText,mp(8)); return scroll(c); }

    private View tests(){ LinearLayout c=v(); c.addView(title("Pruebas funcionales guiadas")); c.addView(box("Un ELM327 genérico no activa universalmente módulos de carrocería. Estas pruebas guían y registran la verificación; activación bidireccional real requiere interfaz OEM/J2534/UDS."));
        testCard(c,"Ventilador de radiador","Monitoree temperatura de refrigerante; active A/C si corresponde; confirme encendido y temperatura de corte.");
        testCard(c,"Ventanas eléctricas","Pruebe comando maestro y local, subida/bajada y antipinzamiento; observe lentitud o consumo anormal.");
        testCard(c,"Cierre centralizado","Bloquee y desbloquee con control, botón interior y llave; verifique todos los actuadores.");
        testCard(c,"Luces exteriores","Compruebe bajas, altas, intermitentes, freno, retroceso y patente.");
        testCard(c,"Sensores MAF/MAP/O2/TPS","Seleccione estos PIDs en Datos y compare respuesta en ralentí y aceleración controlada."); return scroll(c); }

    private View report(){ LinearLayout c=v(); c.addView(title("Informe PDF profesional")); c.addView(box("Se guardará en Descargas/Autoguard e incluirá licencia, vehículo opcional, conexión, DTC y última lectura de sensores.")); Button pdf=primary("Generar informe PDF"); pdf.setOnClickListener(x->makePdf()); c.addView(pdf); return scroll(c); }

    private View licensing(){ LinearLayout c=v(); c.addView(title("Licencia administrada por Autoguard")); licenseText=box(licenseSummary()); c.addView(licenseText,mp(8)); c.addView(box("ID del dispositivo: "+LicenseManager.deviceId(this)),mp(8)); EditText token=edit("Pegue la licencia firmada"); token.setMinLines(4); token.setSingleLine(false); c.addView(token,mp(6)); Button activate=primary("Activar licencia"); activate.setOnClickListener(x->{ license=LicenseManager.activate(this,token.getText().toString()); licenseText.setText(licenseSummary()); toast(license.message); }); c.addView(activate); return scroll(c); }

    private void show(String name){ container.removeAllViews(); View screen=screens.get(name); if(screen!=null) container.addView(screen,new FrameLayout.LayoutParams(-1,-1)); }

    private void toggleConnect(){ if(client!=null&&client.isConnected()){ stopMonitor(); client.close(); client=null; session=null; status.setText("Desconectado"); return; }
        if(!licensed())return; String mode=(String)modeSpinner.getSelectedItem(); ObdClient.Mode m=mode.startsWith("WiFi")?ObdClient.Mode.WIFI:mode.startsWith("Bluetooth")?ObdClient.Mode.BLUETOOTH:ObdClient.Mode.SIMULATOR;
        BluetoothDevice device=(m==ObdClient.Mode.BLUETOOTH&&btSpinner.getSelectedItemPosition()<btDevices.size())?btDevices.get(btSpinner.getSelectedItemPosition()):null;
        int p; try{p=Integer.parseInt(port.getText().toString());}catch(Exception e){p=35000;}
        client=new ObdClient(m,host.getText().toString().trim(),p,device); status.setText("Conectando...");
        io.execute(()->{ try{ ObdClient.SessionInfo s=client.connect(); runOnUiThread(()->{session=s; status.setText("ECU conectada · "+s.protocol+" · VIN "+(s.vin.isBlank()?"N/D":s.vin)); toast("Conexión correcta");}); }catch(Exception e){ runOnUiThread(()->error(e.getMessage())); } }); }

    private List<SensorSpec> selected(){ ArrayList<SensorSpec> list=new ArrayList<>(); java.util.HashSet<String> keys=new java.util.HashSet<>(); for(Map.Entry<String,CheckBox> e:checks.entrySet()) if(e.getValue().isChecked()){ list.add(catalog.get(e.getKey())); keys.add(e.getKey()); } getSharedPreferences("ag",MODE_PRIVATE).edit().putStringSet("sensors",keys).apply(); return list; }
    private void readSensors(){ if(!connected()||!licensed())return; List<SensorSpec> chosen=selected(); if(chosen.isEmpty()){toast("Seleccione sensores");return;} io.execute(()->{ try{Map<String,Double> result=client.readSensors(chosen); runOnUiThread(()->updateSensors(result));}catch(Exception e){runOnUiThread(()->error(e.getMessage()));}}); }
    private void updateSensors(Map<String,Double> result){ latest.putAll(result); for(Map.Entry<String,Double> e:result.entrySet()){TextView t=values.get(e.getKey()); if(t==null)continue; SensorSpec s=catalog.get(e.getKey()); String label=s==null?"Voltaje adaptador":s.label; String value=e.getValue()==null?"--":(s==null?String.format(Locale.US,"%.1f V",e.getValue()):s.format(e.getValue())); t.setText(label+": "+value);} status.setText("Datos actualizados"); }
    private void toggleMonitor(){ if(monitoring){stopMonitor();return;} if(!connected()||!licensed())return; monitoring=true; liveLoop=Executors.newSingleThreadScheduledExecutor(); liveLoop.scheduleWithFixedDelay(this::readSensors,0,3, TimeUnit.SECONDS); toast("Monitoreo iniciado"); }
    private void stopMonitor(){ monitoring=false; if(liveLoop!=null)liveLoop.shutdownNow(); liveLoop=null; }

    private void readDtcs(){ if(!connected()||!licensed())return; io.execute(()->{try{List<ObdClient.DtcEntry> r=client.readAllDtcs(); runOnUiThread(()->{dtcs.clear();dtcs.addAll(r);StringBuilder s=new StringBuilder(); if(r.isEmpty())s.append("Sin DTC registrados"); for(ObdClient.DtcEntry d:r)s.append(d.code).append(" · ").append(d.state).append("\n").append(d.description).append("\n\n"); dtcText.setText(s);});}catch(Exception e){runOnUiThread(()->error(e.getMessage()));}}); }
    private void confirmClear(){ if(!connected()||!licensed())return; new AlertDialog.Builder(this).setTitle("Borrar DTC").setMessage("Mode 04 puede borrar freeze frame y reiniciar monitores. ¿Continuar?").setNegativeButton("Cancelar",null).setPositiveButton("Borrar",(d,w)->io.execute(()->{try{boolean ok=client.clearDtcs();runOnUiThread(()->toast(ok?"Borrado aceptado":"Sin confirmación ECU"));}catch(Exception e){runOnUiThread(()->error(e.getMessage()));}})).show(); }

    private void makePdf(){ if(!licensed())return; io.execute(()->{try{Uri uri=PdfReportService.createReport(this,vehicle,session,dtcs,latest,license);runOnUiThread(()->{toast("PDF creado en Descargas/Autoguard");Intent i=new Intent(Intent.ACTION_VIEW);i.setDataAndType(uri,"application/pdf");i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);try{startActivity(i);}catch(Exception ignored){}});}catch(Exception e){runOnUiThread(()->error(e.getMessage()));}}); }

    private void vehicleDialog(){ LinearLayout form=v(); String[] keys={"client","phone","plate","vin","brand","model","year","mileage","symptoms"}; String[] labels={"Cliente","Teléfono","Patente","VIN","Marca","Modelo","Año","Kilometraje","Síntomas"}; Map<String,EditText> fields=new LinkedHashMap<>(); for(int i=0;i<keys.length;i++){EditText e=edit(labels[i]+" (opcional)");e.setText(vehicle.getOrDefault(keys[i],""));form.addView(e);fields.put(keys[i],e);} ScrollView scroll=scroll(form); new AlertDialog.Builder(this).setTitle("Ficha opcional").setView(scroll).setNeutralButton("Continuar sin datos",null).setNegativeButton("Cancelar",null).setPositiveButton("Guardar",(d,w)->{for(Map.Entry<String,EditText> e:fields.entrySet())vehicle.put(e.getKey(),e.getValue().getText().toString().trim());toast("Ficha guardada");}).show(); }

    private void testCard(LinearLayout parent,String name,String guide){ LinearLayout card=v();card.setPadding(dp(12),dp(10),dp(12),dp(10));card.setBackgroundResource(R.drawable.panel_bg);card.addView(txt(name,16,ORANGE,true));card.addView(txt(guide,12,MUTED,false));TextView result=txt("Resultado: pendiente",12,TEXT,true);card.addView(result);LinearLayout buttons=h();for(String s:new String[]{"OK","REVISAR","N/A"}){Button b=secondary(s);b.setOnClickListener(x->result.setText("Resultado: "+s));buttons.addView(b);}card.addView(buttons);parent.addView(card,mp(6)); }

    private void refreshBluetooth(){ btDevices.clear(); BluetoothAdapter adapter=BluetoothAdapter.getDefaultAdapter(); if(adapter==null)return; if(Build.VERSION.SDK_INT>=31&&checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT)!=PackageManager.PERMISSION_GRANTED){requestPermissions(new String[]{Manifest.permission.BLUETOOTH_CONNECT,Manifest.permission.BLUETOOTH_SCAN},301);return;} try{btDevices.addAll(adapter.getBondedDevices());}catch(SecurityException ignored){} if(btSpinner!=null){List<String> names=new ArrayList<>();for(BluetoothDevice d:btDevices)names.add(d.getName()+" · "+d.getAddress());if(names.isEmpty())names.add("Sin dispositivos");btSpinner.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,names));} }
    private boolean connected(){if(client==null||!client.isConnected()){error("Primero conecte el ELM327");return false;}return true;}
    private boolean licensed(){license=LicenseManager.status(this);if(!license.active){error("Demo vencida. Active una licencia Autoguard.");show("Licencia");return false;}return true;}
    private String licenseSummary(){return (license.active?"ACTIVA":"INACTIVA")+"\nPlan: "+license.plan+"\nID: "+license.licenseId+"\nVencimiento: "+license.expires+"\n"+license.message;}
    private void selectEssential(){for(Map.Entry<String,CheckBox> e:checks.entrySet())e.getValue().setChecked(SensorSpec.essentialKeys().contains(e.getKey()));}
    private void setAll(boolean on){for(CheckBox c:checks.values())c.setChecked(on);}

    private TextView title(String s){TextView t=txt(s,20,ORANGE,true);t.setPadding(0,dp(8),0,dp(10));return t;}
    private TextView box(String s){TextView t=txt(s,12,MUTED,false);t.setPadding(dp(12),dp(10),dp(12),dp(10));t.setBackgroundResource(R.drawable.panel_bg);return t;}
    private void labeled(LinearLayout p,String label,View input){TextView t=txt(label,12,ORANGE,true);t.setPadding(0,dp(8),0,dp(3));p.addView(t);p.addView(input,new LinearLayout.LayoutParams(-1,dp(50)));}
    private Spinner spinner(String[] data){Spinner s=new Spinner(this);s.setBackgroundResource(R.drawable.panel_bg);s.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,data));return s;}
    private EditText edit(String hint){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.GRAY);e.setTextColor(TEXT);e.setBackgroundResource(R.drawable.panel_bg);e.setPadding(dp(10),dp(7),dp(10),dp(7));return e;}
    private Button primary(String s){Button b=new Button(this);b.setText(s);b.setAllCaps(false);b.setTextColor(BG);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setBackgroundResource(R.drawable.button_primary);return b;}
    private Button secondary(String s){Button b=new Button(this);b.setText(s);b.setAllCaps(false);b.setTextColor(ORANGE);b.setBackgroundResource(R.drawable.button_secondary);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-2,dp(46));p.setMargins(dp(3),dp(2),dp(3),dp(2));b.setLayoutParams(p);return b;}
    private TextView txt(String s,int size,int color,boolean bold){TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private LinearLayout v(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;}
    private LinearLayout h(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);return l;}
    private ScrollView scroll(View child){ScrollView s=new ScrollView(this);s.setFillViewport(true);s.addView(child,new ScrollView.LayoutParams(-1,-2));return s;}
    private LinearLayout.LayoutParams mp(int bottom){LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.setMargins(0,0,0,dp(bottom));return p;}
    private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private void error(String m){new AlertDialog.Builder(this).setTitle("Autoguard Mobile Pro").setMessage(m==null?"Error no especificado":m).setPositiveButton("Aceptar",null).show();}
    private void toast(String m){Toast.makeText(this,m,Toast.LENGTH_LONG).show();}

    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==301)refreshBluetooth();}
    @Override protected void onDestroy(){stopMonitor();if(client!=null)client.close();io.shutdownNow();super.onDestroy();}
}
