import requests
import json
import time
import paho.mqtt.client
import socket
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return ""

#nastaveni hue
hue = True
min_t = 10
max_t = 35
max_hue = 65535

#nastaveni reagovani relay na lux
illuminance_true = 50
illuminance_false = 100

ip_show_timeout = 30

d = max_hue / float( abs(max_t) + abs(min_t) )

def mgtt_on_connect(mqtt, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    mqtt.subscribe("nodes/bridge/0/#")

def mgtt_on_message(mqtt, userdata, msg):
    #print(msg.topic+" "+str(msg.payload))

    if msg.topic.endswith('set') :
        return

    try: 
        payload = json.loads(msg.payload.decode('utf-8')) 
    except:
        return
    
    if 'thermometer' in msg.topic : #/i2c0-48
        if 'temperature' in payload :
            t = payload.get('temperature', [None] )[0]
            if t != None and t != userdata['temperature'] : 
                if hue :
                    print('t', t, 'hue', round(d*t) )
                    try:
                        requests.put('http://192.168.1.3/api/bqKfglRkp1-8K2EcEFWo2dxajUPvlbJAzOKmgva4/lights/2/state', json.dumps({"hue":round(d*t)}) )
                        requests.put('http://192.168.1.3/api/bqKfglRkp1-8K2EcEFWo2dxajUPvlbJAzOKmgva4/lights/3/state', json.dumps({"hue":round(d*t)}) )
                    except:
                        pass

                mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-2":"temperature %0.2f C" % t } ) )
                userdata['temperature'] = t

    elif 'lux-meter' in msg.topic : #/i2c0-44
        illuminance = payload.get('illuminance', [None, None])[0]
        if type(illuminance) != float: 
            return

        illuminance = round(illuminance)

        if illuminance != userdata['illuminance']:

            if illuminance < illuminance_true and userdata['state'] != True:
                mqtt.publish('nodes/bridge/0/relay/i2c0-3b/set', '{"state": true}')
                userdata['state'] = True
                print('illuminance: {:7.1f}  Relay ON'.format(illuminance))
            elif illuminance > illuminance_false and userdata['state'] != False:
                mqtt.publish('nodes/bridge/0/relay/i2c0-3b/set', '{"state": false}')
                userdata['state'] = False
                print('illuminance: {:7.1f}  Relay OFF'.format(illuminance))

            text = "illuminance %d lux" % illuminance
            mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-3": text[0:21] } ) )
            userdata['illuminance'] = illuminance

    elif 'barometer' in msg.topic :
        pressure = payload.get('pressure', [None])[0]
        if pressure != None and pressure != userdata['pressure'] :
            mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-4":"pressure %0.2f kPa" % pressure } ) )
            userdata['pressure'] = pressure
        
        altitude = payload.get('altitude', [None])[0]
        if altitude != None and altitude != userdata['altitude'] :
            mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-5":"altitude %0.2f m" % altitude } ) )
            userdata['altitude'] = altitude

    elif 'humidity-sensor' in msg.topic :
        humidity = payload.get('relative-humidity', [None])[0]
        if humidity != None and humidity != userdata['humidity'] :
            mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-6":"humidity %0.2f %%" % humidity } ) )
            userdata['humidity'] = humidity

    elif 'co2-sensor' in msg.topic :
        co2 = payload.get('concentration', [None])[0]
        if co2 != None and co2 != userdata['co2'] :
            mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-7":"co2 %0.2f ppm" % co2 } ) )
            userdata['co2'] = co2
    else:
        if userdata['ip_show'] < time.time():
            ip = get_ip_address()
            if ip :
                mqtt.publish("nodes/bridge/0/display-oled/i2c0-3c/set", json.dumps( {"line-7":"ip "+ ip } ) )
                userdata['ip_show'] = time.time() + ip_show_timeout

def run():
    mqtt = paho.mqtt.client.Client(userdata={
        'temperature': None, 
        'state': None, 
        'illuminance':None,
        'pressure':None,
        'altitude':None,
        'humidity':None,
        'co2':None,
        'ip_show':0 })
    mqtt.connect("127.0.0.1", 1883, 10)
    mqtt.on_connect = mgtt_on_connect
    mqtt.on_message = mgtt_on_message
    mqtt.loop_forever()

while 1 :
    try:
        run()
    except KeyboardInterrupt:
        raise
    except:
        time.sleep(1)
