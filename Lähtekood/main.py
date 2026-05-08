import asyncio
import json
import random
import serial
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from gpiozero import Button, LED, DigitalInputDevice
import uvicorn

# ==========================================
# GLOBAALSED MUUTUJAD JA OLEKUD
# ==========================================
main_loop = None
STATE = "IDLE"  # Võimalikud: ERROR, IDLE, ACTIVE, QUIZ, REWARD

# Riistvara pordid
RADAR_PORT = '/dev/ttyAMA4'
ESP_PORT = '/dev/ttyUSB0'  # Või /dev/ttyACM0

# Quiz taimer
quiz_last_activity = 0
QUIZ_TIMEOUT = 30  # Sekundit, enne kui robot tüdineb

questions_db = []
current_question = None

# ==========================================
# ANDMEBAASI LAADIMINE
# ==========================================
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("VIGA: questions.json faili ei leitud!")
        return []

questions_db = load_questions()

def get_random_question():
    if not questions_db:
        return {"question": "VIGA: Andmebaas tühi!", "answers": {"A": "-", "B": "-", "C": "-", "D": "-"}, "correct_btn": "A"}
    return random.choice(questions_db)

# ==========================================
# ESP32 JA RADAR (JADAÜHENDUSED)
# ==========================================
esp_serial = None
radar_serial = None

try:
    esp_serial = serial.Serial(ESP_PORT, 115200, timeout=1)
    print("ESP32 ühendatud!")
except:
    print(f"VIGA: ESP32 ei leitud pordilt {ESP_PORT}")

try:
    radar_serial = serial.Serial(RADAR_PORT, 115200, timeout=1)
    print("Radar ühendatud!")
except:
    print(f"VIGA: Radariti ei leitud pordilt {RADAR_PORT}")

def send_esp_command(cmd: str):
    """Saadab käsu üle USB ESP32-le"""
    if esp_serial:
        try:
            esp_serial.write((cmd + '\n').encode('utf-8'))
        except Exception as e:
            print(f"ESP saatmise viga: {e}")

# ==========================================
# NUPUD JA HALL SENSOR
# ==========================================
hardware_events = asyncio.Queue()

try:
    btn_A = Button(17, pull_up=True, bounce_time=0.1) # Punane
    led_A = LED(27)
    btn_B = Button(23, pull_up=True, bounce_time=0.1) # Roheline
    led_B = LED(22)
    btn_C = Button(24, pull_up=True, bounce_time=0.1) # Sinine
    led_C = LED(25)
    btn_D = Button(16, pull_up=True, bounce_time=0.1)  # Kollane
    led_D = LED(13)
    
    # Hall sensor šokolaadi jaoks
    hall_sensor = DigitalInputDevice(18, pull_up=True)
    hardware_available = True
except Exception as e:
    print(f"GPIO viga: {e}")
    hardware_available = False

def turn_all_leds(state: bool):
    if not hardware_available: return
    if state:
        led_A.on(); led_B.on(); led_C.on(); led_D.on()
    else:
        led_A.off(); led_B.off(); led_C.off(); led_D.off()

# ==========================================
# OLEKUMASINA/FSM LOOGIKAL ALGORITM
# ==========================================
def change_state(new_state):
    global STATE, current_question, quiz_last_activity
    if STATE == new_state: return
    STATE = new_state
    print(f"--- UUS OLEK: {STATE} ---")

    # Teavita brauserit oleku muutusest
    if main_loop:
        main_loop.call_soon_threadsafe(hardware_events.put_nowait, {"event": "STATE_CHANGE", "state": STATE})

    if STATE == "IDLE":
        # turn_all_leds(False)
        send_esp_command("LED_IDLE")
        
    elif STATE == "ACTIVE":
        # Heli: "Hei! Astu ligi!"
        # Siin saad hiljem kutsuda nt: play_audio("tervitus.wav")
        # turn_all_leds(True)
        send_esp_command("LED_IDLE")

    elif STATE == "QUIZ":
        quiz_last_activity = time.time()
        turn_all_leds(True)
        current_question = get_random_question()
        if main_loop:
            main_loop.call_soon_threadsafe(hardware_events.put_nowait, {
                "event": "START_QUIZ",
                "question": current_question["question"],
                "answers": current_question["answers"],
                "correct_btn": current_question["correct_btn"]
            })
            
    elif STATE == "REWARD":
        turn_all_leds(False)
        # Heli: "Suurepärane! Siin on sulle auhind!"
        send_esp_command("LED_WIN")
        send_esp_command("DISPENSE")
        # Premeerimise lõpetab eraldi taustaprotsess (vaata allpool)

    elif STATE == "ERROR":
        turn_all_leds(False)
        send_esp_command("LED_OFF")

# ==========================================
# SÜNDMUSTE KÄSITLEJAD (Nupud & Sensor)
# ==========================================
def on_button_pressed(btn_name):
    global quiz_last_activity
    
    if STATE == "ERROR":
        # Kui oleme hoolduses, ainult ROHELINE nupp teeb midagi (kinnitab täitmise)
        if btn_name == "B" and not hall_sensor.is_active:
            print("Hooldus kinnitatud. Masin korras!")
            change_state("IDLE")
        return

    if STATE == "ACTIVE":
        # Inimene vajutas nuppu, lähme viktoriini!
        change_state("QUIZ")
        return

    if STATE == "QUIZ":
        quiz_last_activity = time.time() # Nullime taimeri
        
        # Saada vajutus UI-le visuaaliks
        if main_loop:
            main_loop.call_soon_threadsafe(hardware_events.put_nowait, {"event": "BUTTON_PRESS", "button": btn_name})
        
        # Kontrollime vastust
        if btn_name == current_question["correct_btn"]:
            change_state("REWARD")
            # Käivitame asünkroonse ootaja, mis viib tagasi IDLE olekusse pärast servo tsüklit
            if main_loop:
                main_loop.create_task(reward_sequence())
        else:
            # Heli: "Vale vastus, proovi uuesti!"
            pass 

def on_hall_sensor_changed():
    """Kutsutakse välja, kui magnet fikseerib salve tühjenemise"""
    if hall_sensor.is_active:
        print("HÄIRE: Šokolaad on otsas!")
        change_state("ERROR")
    else:
        # Magnet võeti ära, järelikult hooldaja võttis salve välja
        if STATE == "ERROR":
            print("Hooldus: Salv eemaldatud. Ootan rohelist nuppu...")
            if main_loop:
                main_loop.call_soon_threadsafe(hardware_events.put_nowait, {"event": "MAINTENANCE_MODE"})

if hardware_available:
    btn_A.when_pressed = lambda: on_button_pressed("A")
    btn_B.when_pressed = lambda: on_button_pressed("B")
    btn_C.when_pressed = lambda: on_button_pressed("C")
    btn_D.when_pressed = lambda: on_button_pressed("D")
    
    # Magnetanduri sündmused
    hall_sensor.when_activated = on_hall_sensor_changed
    hall_sensor.when_deactivated = on_hall_sensor_changed

# ==========================================
# TAUSTAPROTSESSID (Radar & Taimerid)
# ==========================================
async def reward_sequence():
    """Ootab servo väljastustsükli lõppu ja taastab ooterežiimi"""
    await asyncio.sleep(8) # ESP tsükkel võtab ca 8 sek
    if STATE == "REWARD": # Veendume, et vahepeal pole magnet salv tühjenenud
        change_state("IDLE")

async def led_blinker_task():
    """Haldab nuppude LED-ide animatsioone"""
    if not hardware_available:
        return
        
    # Nuppude LED-ide haldus
    leds = [led_A, led_B, led_C, led_D]
    wave_index = 0
    wave_direction = 1
    blink_state = False

    while True:
        if STATE == "IDLE":
            # Lainetuse (wave) rütm edasi-tagasi
            for i, led in enumerate(leds):
                if i == wave_index:
                    led.on()
                else:
                    led.off()
            
            # Arvutame järgmise tule indeksi
            wave_index += wave_direction
            if wave_index >= len(leds) - 1:
                wave_direction = -1  # Pöörab suuna tagasi
            elif wave_index <= 0:
                wave_direction = 1   # Pöörab suuna edasi
                
            await asyncio.sleep(0.3) # Laine liikumise kiirus (väiksem = kiirem)

        elif STATE == "ACTIVE":
            # Kõik nupud vilguvad sünkroonis
            blink_state = not blink_state
            turn_all_leds(blink_state)
            await asyncio.sleep(0.5) # Vilkumise kiirus (0.5s sees, 0.5s väljas)
            
        else:
            # Muudes olekutes (QUIZ, REWARD, ERROR) me animatsiooni ei tee
            # Tulede staatilise oleku määrab `change_state()` funktsioon
            await asyncio.sleep(0.5)

async def radar_listener():
    last_seen_time = 0
    presence_start_time = None  # Stopperi algusaeg
    REQUIRED_PRESENCE = 5.0     # Mitu sekundit peab inimene paigal seisma
    
    while True:
        if radar_serial and radar_serial.in_waiting > 0:
            try:
                line = radar_serial.readline().decode('utf-8').strip()
                # Puhastame sisendi ja teisendame numbriks
                distance = int(''.join(filter(str.isdigit, line))) 
                
                # Silumiseks saadame endiselt andmed HUDi (lõpus eemaldame)
                if main_loop:
                    main_loop.call_soon_threadsafe(hardware_events.put_nowait, {
                        "event": "RADAR_DEBUG", 
                        "distance": distance
                    })

                if distance < 100: 
                    last_seen_time = time.time() # Viimati nähtud üldse
                    
                    # Kui keegi just sisenes, paneme stopperi käima
                    if presence_start_time is None:
                        presence_start_time = time.time()
                        print("Radar: Keegi sisenes tsooni, alustan ootamist...")

                    # Kontrollime, kas 5 sekundit on täis
                    elapsed = time.time() - presence_start_time
                    if STATE == "IDLE" and elapsed >= REQUIRED_PRESENCE:
                        print(f"Radar: Inimene on viibinud tsooni {REQUIRED_PRESENCE}s. Aktiveerin!")
                        change_state("ACTIVE")
                else:
                    # Kui vaateväli on tühi, nullime stopperi koheselt
                    if presence_start_time is not None:
                        print("Radar: Tsoon tühjenes, nullin stopperi.")
                    presence_start_time = None
                    
            except Exception as e:
                # ignoreeri lugemisvigu
                pass
                
        # Kui oleme ACTIVE olekus ja kedagi pole näha olnud 3 sekundit, läheb IDLE-sse
        if STATE == "ACTIVE" and (time.time() - last_seen_time > 3.0):
            change_state("IDLE")
            presence_start_time = None # Igaks juhuks nullime ka siin
            
        await asyncio.sleep(0.05)

async def quiz_timeout_watcher():
    """Põgenemise stsenaarium: Viskab mängust välja, kui nuppu ei vajutata"""
    while True:
        if STATE == "QUIZ" and (time.time() - quiz_last_activity > QUIZ_TIMEOUT):
            print("TIMEOUT: Inimene lahkus mängu ajal.")
            change_state("IDLE")
        await asyncio.sleep(1)

# ==========================================
# FASTAPI JA SÜSTEEMI KÄIVITUMINE
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global main_loop
    main_loop = asyncio.get_running_loop()
    
    # Käivitame taustaprotsessid
    asyncio.create_task(broadcast_hardware_events())
    asyncio.create_task(radar_listener())
    asyncio.create_task(quiz_timeout_watcher())
    asyncio.create_task(led_blinker_task())
    
    # Kontrollime kohe alguses, kas šokolaadi on
    if hardware_available and hall_sensor.is_active:
        change_state("ERROR")
    else:
        change_state("IDLE")
        
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/gui", StaticFiles(directory="frontend", html=True), name="gui")
active_websockets = []

async def broadcast_hardware_events():
    global current_question # Vajalik, et teaksime, mis on õige vastus
    
    while True:
        event = await hardware_events.get()
        
        # 1. SAADAME SÜNDMUSE BRAUSERISSE (nagu varem)
        # See paneb nupu ekraanil helendama
        for ws in active_websockets:
            try:
                await ws.send_json(event)
            except:
                pass

        # 2. LOGIKA KONTROLL: Kui on käimas QUIZ ja vajutati nuppu
        if STATE == "QUIZ" and event.get("event") == "BUTTON_PRESS":
            user_choice = event.get("button") # Nt "A"
            
            # Kontrollime, kas current_question on olemas ja sisaldab õiget vastust
            if current_question and "correct_btn" in current_question:
                correct_choice = current_question["correct_btn"]

                if user_choice == correct_choice:
                    print(f"RAAL-AJU: Õige vastus! ({user_choice})")
                    change_state("REWARD")
                else:
                    print(f"RAAL-AJU: Vale vastus! Valiti {user_choice}, aga õige oli {correct_choice}")
                    
                    # Teavitame brauserit, et vastus oli vale
                    for ws in active_websockets:
                        try:
                            await ws.send_json({
                                "event": "QUIZ_RESULT",
                                "result": "WRONG",
                                "button": user_choice
                            })
                        except:
                            pass
                    
                    # Jätame veateate 3-ks sekundiks ekraanile ja siis läheme ootele
                    await asyncio.sleep(3)
                    
                    if STATE == "QUIZ":
                        # Taastame ekraani, saates SAMA küsimuse uuesti.
                        # Kuna app.js juba teab, et START_QUIZ puhastab vanad stiilid ära,
                        # siis ekraan läheb ilusti tagasi algsesse "ootan vastust" seisu.
                        for ws in active_websockets:
                            try:
                                await ws.send_json({
                                    "event": "START_QUIZ",
                                    "question": current_question["question"],
                                    "answers": current_question["answers"],
                                    "correct_btn": current_question["correct_btn"]
                                })
                            except:
                                pass
        
        # Märgime järjekorra elemendi töödelduks
        hardware_events.task_done()
        
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    # Saadame kohe algse oleku uuele brauserile
    await websocket.send_json({"event": "STATE_CHANGE", "state": STATE})
    try:
        while True:
            await websocket.receive_text() # Hoiame ühendust elus
    except WebSocketDisconnect:
        active_websockets.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)