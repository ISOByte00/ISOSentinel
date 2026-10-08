from enum import Enum
from dataclasses import dataclass
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PolicyDecision(Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    LOG = "LOG"

@dataclass
class PolicyEvaluationResult:
    decision: PolicyDecision
    reason: str
    severity: str = "INFO"

class PolicyEngine:
    # Dokunulmaz Sistem ve Geliştirici Süreçleri
    SYSTEM_DEV_WHITELIST = [
        "python.exe", "pythonw.exe", "git.exe", "code.exe", 
        "cmd.exe", "powershell.exe", "conhost.exe", "taskhostw.exe",
        "svchost.exe", "explorer.exe", "sihost.exe", "ctfmon.exe",
        "system", "idle", "registry", "vctip.exe",
        "docker.exe", "dockerd.exe", "docker-desktop.exe", 
        "wsl.exe", "vmmem", "com.docker.backend.exe", "wslhost.exe"
    ]

    # Oyun İstemcileri / Platformlar (Kendi başlarına oyun değildir)
    LAUNCHER_WHITELIST = [
        "steam.exe", "steamwebhelper.exe", "steamservice.exe",
        "epicgameslauncher.exe", "epicwebhelper.exe",
        "uplay.exe", "ubisoftconnect.exe", "galaxyclient.exe"
    ]

    # Bilinen Güvenilir Üreticiler (PE Metadata)
    TRUSTED_COMPANIES = [
        "microsoft", "nvidia", "amd", "intel", "voidtools", 
        "logitech", "realtek", "tailscale", "google", "mozilla",
        "asus", "gigabyte", "msi", "corsair", "razer", "brave",
        "docker inc", "discord inc", "discord", "spotify",
        "kristjan skutta", "team ts3", "overwolf", "obs project",
        "git for windows", "python software foundation"
    ]

    SAFE_PATHS = [
        "c:\\windows", "system32", "program files\\google\\chrome", 
        "program files (x86)\\google\\chrome", "brave-browser", 
        "microsoft\\edge", "microsoft vs code", "docker", "wsl", "git"
    ]

    GAME_ZONES = [
        "steamapps\\common", "riot games", "epic games", "xboxgames", 
        "origin games", "ea games", "ubisoft",
        "roblox", ".minecraft", "curseforge", "ftb", 
        "technic", "tlauncher", "osu!"
    ]

    NON_GAME_WORDS = [
        "launcher", "setup", "service", "helper", "installer", 
        "client", "updater", "overlay", "renderer", "crashhandler", 
        "system", "host", "daemon"
    ]

    def __init__(self, api_key: str = None, repo=None):
        self.api_key = api_key
        self.repo = repo

    def evaluate(self, process_info: dict, session_context: dict = None) -> PolicyEvaluationResult:
        process_name = process_info.get("process_name", "").lower()
        exe_path = process_info.get("exe_path", "").lower()
        file_hash = process_info.get("file_hash", "")
        company = process_info.get("company_name", "").lower()
        is_temp_file = exe_path.endswith('.tmp') or exe_path.endswith('.temp')

        # 1. Kural: Yasaklı Parmak İzi (Blacklisted Hash)
        if self.repo and self.repo.check_if_hash_is_blocked(file_hash):
            return PolicyEvaluationResult(
                decision=PolicyDecision.BLOCK,
                reason="HASH_MATCH",
                severity="HIGH"
            )

        # 2. Kural: Sistem, Geliştirici ve Launcher Beyaz Listesi
        if process_name in self.SYSTEM_DEV_WHITELIST or process_name in self.LAUNCHER_WHITELIST:
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                reason="WHITELIST_PROCESS"
            )

        # 3. Kural: PE Metadata Güvenilir Üretici Onayı
        if not is_temp_file and any(trusted in company for trusted in self.TRUSTED_COMPANIES):
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                reason="TRUSTED_COMPANY_HEURISTIC"
            )

        # 4. Kural: Güvenli Klasörler (Safe Paths)
        if any(safe_path in exe_path for safe_path in self.SAFE_PATHS):
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                reason="SAFE_PATH"
            )

        # 5. Kural: Oyun Klasörleri (Game Zones)
        if any(zone in exe_path for zone in self.GAME_ZONES):
            if "roblox" in company or "roblox" in exe_path:
                return PolicyEvaluationResult(
                    decision=PolicyDecision.BLOCK,
                    reason="ROBLOX_DETECTED",
                    severity="HIGH"
                )
            
            return PolicyEvaluationResult(
                decision=PolicyDecision.BLOCK,
                reason="GAME_ZONE_MATCH",
                severity="HIGH"
            )

        # 6. Kural: Dış İstihbarat (RAWG API)
        if self._check_if_game_via_api(process_name):
            return PolicyEvaluationResult(
                decision=PolicyDecision.BLOCK,
                reason="RAWG_API_MATCH",
                severity="HIGH"
            )

        # Varsayılan Karar: İzin Ver
        return PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            reason="DEFAULT_ALLOW"
        )

    def _check_if_game_via_api(self, process_name: str) -> bool:
        if not self.api_key:
            return False
            
        clean_name = process_name.replace(".exe", "").strip()
        if any(word in clean_name for word in self.NON_GAME_WORDS):
            return False

        url = f"https://api.rawg.io/api/games?key={self.api_key}&search={clean_name}&page_size=1"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        try:
            response = requests.get(url, headers=headers, timeout=2, verify=False)
            if response.status_code == 200:
                data = response.json()
                if data.get("count", 0) > 0:
                    top_game = data["results"][0]
                    top_name = top_game["name"].lower()
                    if clean_name == top_name or (len(clean_name) > 3 and clean_name in top_name and not any(w in top_name for w in self.NON_GAME_WORDS)):
                        print(f"  └── [API TESPİT] '{clean_name}' OYUN olarak doğrulandı! RAWG: '{top_game['name']}'")
                        return True
        except Exception:
            pass
        return False