let socket;

function connectWebSocket() {
    socket = new WebSocket(`ws://${window.location.host}/ws`);

    socket.onopen = () => {
        console.log("WebSocket ühendatud!");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Sõnum serverilt:", data);

        // 1. OLEKU VAHETUS (FSM)
        if (data.event === "STATE_CHANGE") {
            
            // UUS: IDLE ja ACTIVE jagavad nüüd ühist näo-ekraani
            if (data.state === "IDLE" || data.state === "ACTIVE") {
                showScreen("screen-face"); // Kuvame uue ühise ekraani
                
                const face = document.getElementById("robot-face");
                const text = document.getElementById("greeting-text");
                const floatingHei = document.getElementById("floating-hei"); // UUS
                
                // Kui on ACTIVE, paneme näo naeratama ja teksti ilmuma
                if (data.state === "ACTIVE") {
                    if (face) face.classList.add("excited");
                    if (text) text.classList.add("excited-text");
                    if (floatingHei) floatingHei.classList.add("active");
                } 
                // Kui on IDLE, võtame naeratuse ja teksti ära
                else {
                    if (face) face.classList.remove("excited");
                    if (text) text.classList.remove("excited-text");
                    if (floatingHei) floatingHei.classList.remove("active"); // UUS
                }
            } else {
                // QUIZ, ERROR ja REWARD ekraanid töötavad vanamoodi edasi
                showScreen(`screen-${data.state.toLowerCase()}`);
            }
            
            // Sinu algne nuppude vilkumise loogika
            const allButtons = document.querySelectorAll('.answer-box');
            if (data.state === "ACTIVE") {
                allButtons.forEach(btn => btn.classList.add('active-blink'));
            } else {
                allButtons.forEach(btn => btn.classList.remove('active-blink'));
            }

            // Sinu algne ERROR oleku tekstide määramine
            if (data.state === "ERROR") {
                document.getElementById('error-title').innerText = "⚠️ Šokolaad on otsas!";
                document.getElementById('error-message').innerText = "Palun kutsuge töötaja.";
            }
        }

        // 2. HOOLDUSREŽIIM (Magnet eemaldati)
        if (data.event === "MAINTENANCE_MODE") {
            document.getElementById('error-title').innerText = "🔧 Hooldusrežiim";
            document.getElementById('error-message').innerText = "Palun sisestage täidetud salv ja vajutage ROHELIST nuppu.";
        }

        // 3. UUE KÜSIMUSE LAADIMINE
        if (data.event === "START_QUIZ") {
            document.getElementById("question-text").innerText = data.question;
            document.getElementById("text-A").innerText = data.answers["A"];
            document.getElementById("text-B").innerText = data.answers["B"];
            document.getElementById("text-C").innerText = data.answers["C"];
            document.getElementById("text-D").innerText = data.answers["D"];
            
            // Eemalda eelmised visuaalsed vajutused ja vilkumised
            document.querySelectorAll('.answer-box').forEach(box => {
                box.classList.remove('pressed');
                box.classList.remove('dimmed');
                box.classList.remove('active-blink');
                box.classList.remove('wrong-answer');
            });
        }

        // 4. NUPU VAJUTUSE VISUAAL (MÄNGU AJAL)
        if (data.event === "BUTTON_PRESS") {
            const btnBox = document.getElementById(`ans-${data.button}`);
            if (btnBox) {
                btnBox.classList.add('pressed');
                
                document.querySelectorAll('.answer-box').forEach(box => {
                    if (box.id !== `ans-${data.button}`) {
                        box.classList.add('dimmed');
                    }
                });

                setTimeout(() => {
                    btnBox.classList.remove('pressed');
                }, 800);
            }
        }

        // 5. VIKTORIINI TULEMUS (Valvame valesid vastuseid)
        if (data.event === "QUIZ_RESULT") {
            const questionText = document.getElementById("question-text");
            if (data.result === "WRONG") {
                questionText.innerHTML = "<span style='color: #ff4757;'>❌ VALE VASTUS!</span><br><small>Proovi järgmine kord uuesti.</small>";
                
                // Lisa värina-efekt (peab olema style.css-is defineeritud)
                document.body.style.animation = "shake 0.5s";
                setTimeout(() => { document.body.style.animation = ""; }, 500);

                if (data.button) {
                    const wrongBtn = document.getElementById(`ans-${data.button}`);
                    if (wrongBtn) {
                        wrongBtn.classList.add('wrong-answer');
                    }
                }
            }
        }

        // 6. RADARI SILUMINE (Debug HUD ekraani nurgas)
        if (data.event === "RADAR_DEBUG") {
            const radarVal = document.getElementById("radar-val");
            const debugHud = document.getElementById("debug-hud");
            if (radarVal) radarVal.innerText = data.distance;
            
            if (debugHud) {
                if (data.distance < 100) {
                    debugHud.style.color = "yellow";
                    debugHud.style.border = "1px solid yellow";
                } else {
                    debugHud.style.color = "lime";
                    debugHud.style.border = "none";
                }
            }
        }
    };

    socket.onclose = () => {
        console.log("WebSocket ühendus katkes. Proovin 2s pärast uuesti...");
        setTimeout(connectWebSocket, 2000);
    };
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.add('hidden');
    });
    const activeScreen = document.getElementById(screenId);
    if (activeScreen) {
        activeScreen.classList.remove('hidden');
    }
}

connectWebSocket();