"""
Settings View for YKS Sentinel.
Configures Pomodoro durations, Health Guardrails, and Blocked Applications.
"""
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QSpinBox, QLineEdit, QMessageBox, QTabWidget
)
from PyQt6.QtCore import pyqtSignal
from config.settings import settings


class SettingsView(QWidget):
    policies_updated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_policies()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Uygulama ve Güvenlik Ayarları")
        header.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #30363d;
                background-color: #161b22;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #21262d;
                color: #8b949e;
                padding: 10px 20px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #161b22;
                color: #ffffff;
                border-bottom: 2px solid #58a6ff;
            }
        """)

        # Tab 1: Pomodoro & Health
        tab_general = QWidget()
        gen_layout = QVBoxLayout(tab_general)
        gen_layout.setContentsMargins(16, 16, 16, 16)
        gen_layout.setSpacing(16)

        # Pomodoro Box
        pomo_frame = QFrame()
        pomo_frame.setStyleSheet("background-color: #1e222d; border-radius: 8px; padding: 12px;")
        pomo_layout = QVBoxLayout(pomo_frame)
        pomo_title = QLabel("Pomodoro Süre Ayarları")
        pomo_title.setStyleSheet("color: #58a6ff; font-weight: bold; font-size: 14px;")
        pomo_layout.addWidget(pomo_title)

        pomo_grid = QHBoxLayout()
        self.spin_study = QSpinBox()
        self.spin_study.setRange(5, 120)
        self.spin_study.setValue(settings.pomodoro.study_duration_minutes)
        self.spin_study.setSuffix(" dk")

        self.spin_short_break = QSpinBox()
        self.spin_short_break.setRange(1, 30)
        self.spin_short_break.setValue(settings.pomodoro.short_break_minutes)
        self.spin_short_break.setSuffix(" dk")

        self.spin_long_break = QSpinBox()
        self.spin_long_break.setRange(5, 60)
        self.spin_long_break.setValue(settings.pomodoro.long_break_minutes)
        self.spin_long_break.setSuffix(" dk")

        pomo_grid.addWidget(QLabel("Çalışma Bloğu:"))
        pomo_grid.addWidget(self.spin_study)
        pomo_grid.addWidget(QLabel("Kısa Mola:"))
        pomo_grid.addWidget(self.spin_short_break)
        pomo_grid.addWidget(QLabel("Uzun Mola:"))
        pomo_grid.addWidget(self.spin_long_break)
        pomo_layout.addLayout(pomo_grid)
        gen_layout.addWidget(pomo_frame)

        # Health Box
        health_frame = QFrame()
        health_frame.setStyleSheet("background-color: #1e222d; border-radius: 8px; padding: 12px;")
        health_layout = QVBoxLayout(health_frame)
        health_title = QLabel("Sağlıklı Çalışma Sınırları (Health Guardrails)")
        health_title.setStyleSheet("color: #3fb950; font-weight: bold; font-size: 14px;")
        health_layout.addWidget(health_title)

        health_grid = QHBoxLayout()
        self.spin_max_study = QSpinBox()
        self.spin_max_study.setRange(60, 900)
        self.spin_max_study.setValue(settings.health.max_daily_study_minutes)
        self.spin_max_study.setSuffix(" dk")

        self.txt_sleep_start = QLineEdit(settings.health.sleep_start)
        self.txt_sleep_end = QLineEdit(settings.health.sleep_end)

        health_grid.addWidget(QLabel("Maks. Günlük Çalışma:"))
        health_grid.addWidget(self.spin_max_study)
        health_grid.addWidget(QLabel("Uyku Başlangıç:"))
        health_grid.addWidget(self.txt_sleep_start)
        health_grid.addWidget(QLabel("Uyku Bitiş:"))
        health_grid.addWidget(self.txt_sleep_end)
        health_layout.addLayout(health_grid)
        gen_layout.addWidget(health_frame)

        btn_save_general = QPushButton("Zaman ve Sağlık Ayarlarını Kaydet")
        btn_save_general.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: #ffffff;
                font-weight: bold;
                padding: 10px 18px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2ea043; }
        """)
        btn_save_general.clicked.connect(self._save_general_settings)
        gen_layout.addWidget(btn_save_general)
        gen_layout.addStretch()

        tabs.addTab(tab_general, "Zaman & Sağlık")

        # Tab 2: Blocked Apps
        tab_apps = QWidget()
        apps_layout = QVBoxLayout(tab_apps)
        apps_layout.setContentsMargins(16, 16, 16, 16)
        apps_layout.setSpacing(12)

        # Add New Rule
        add_frame = QHBoxLayout()
        self.txt_app_name = QLineEdit()
        self.txt_app_name.setPlaceholderText("Uygulama adı (örn: Discord.exe)")
        self.txt_app_reason = QLineEdit()
        self.txt_app_reason.setPlaceholderText("Yasaklama nedeni (örn: Odak dağıtıcı)")
        
        btn_add_rule = QPushButton("Yasaklı Uygulama Ekle")
        btn_add_rule.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: #ffffff;
                font-weight: bold;
                padding: 8px 14px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #388bfd; }
        """)
        btn_add_rule.clicked.connect(self._add_blocked_app)

        add_frame.addWidget(self.txt_app_name)
        add_frame.addWidget(self.txt_app_reason)
        add_frame.addWidget(btn_add_rule)
        apps_layout.addLayout(add_frame)

        # Table
        self.table_policies = QTableWidget()
        self.table_policies.setColumnCount(4)
        self.table_policies.setHorizontalHeaderLabels(["Uygulama (Exe)", "Durum", "Neden", "İşlem"])
        self.table_policies.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_policies.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 8px;
                gridline-color: #30363d;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #8b949e;
                font-weight: bold;
                padding: 8px;
                border: none;
            }
        """)
        apps_layout.addWidget(self.table_policies)

        # Toggle / Remove buttons
        pol_btn_layout = QHBoxLayout()
        btn_toggle = QPushButton("Aktif/Pasif Yap")
        btn_toggle.clicked.connect(self._toggle_selected_app)
        btn_delete = QPushButton("Listeden Kaldır")
        btn_delete.clicked.connect(self._delete_selected_app)
        
        pol_btn_layout.addWidget(btn_toggle)
        pol_btn_layout.addWidget(btn_delete)
        pol_btn_layout.addStretch()
        apps_layout.addLayout(pol_btn_layout)

        tabs.addTab(tab_apps, "Yasaklı Uygulamalar (Process Guard)")

        layout.addWidget(tabs)

    def load_policies(self):
        try:
            if settings.policies_path.exists():
                with open(settings.policies_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    apps = data.get("blocked_apps", [])
                    self.table_policies.setRowCount(len(apps))
                    for row, app in enumerate(apps):
                        self.table_policies.setItem(row, 0, QTableWidgetItem(app.get("name", "")))
                        status_str = "AKTİF" if app.get("enabled", True) else "PASİF"
                        self.table_policies.setItem(row, 1, QTableWidgetItem(status_str))
                        self.table_policies.setItem(row, 2, QTableWidgetItem(app.get("reason", "")))
                        self.table_policies.setItem(row, 3, QTableWidgetItem(app.get("action", "kill")))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Politikalar yüklenemedi: {e}")

    def _save_general_settings(self):
        settings.pomodoro.study_duration_minutes = self.spin_study.value()
        settings.pomodoro.short_break_minutes = self.spin_short_break.value()
        settings.pomodoro.long_break_minutes = self.spin_long_break.value()
        settings.health.max_daily_study_minutes = self.spin_max_study.value()
        settings.health.sleep_start = self.txt_sleep_start.text()
        settings.health.sleep_end = self.txt_sleep_end.text()
        QMessageBox.information(self, "Başarılı", "Zaman ve sağlık ayarları güncellendi.")

    def _add_blocked_app(self):
        name = self.txt_app_name.text().strip()
        reason = self.txt_app_reason.text().strip() or "Odak Koruma Kuralı"
        if not name:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir exe adı girin.")
            return

        try:
            with open(settings.policies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            data.setdefault("blocked_apps", []).append({
                "name": name,
                "paths": [],
                "sha256": [],
                "action": "kill",
                "enabled": true if hasattr(bool, 'true') else True,
                "reason": reason
            })

            with open(settings.policies_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.txt_app_name.clear()
            self.txt_app_reason.clear()
            self.load_policies()
            self.policies_updated.emit()
            QMessageBox.information(self, "Eklendi", f"{name} engellenenler listesine eklendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kayıt başarısız: {e}")

    def _toggle_selected_app(self):
        row = self.table_policies.currentRow()
        if row < 0:
            return
        name = self.table_policies.item(row, 0).text()
        try:
            with open(settings.policies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for app in data.get("blocked_apps", []):
                if app.get("name") == name:
                    app["enabled"] = not app.get("enabled", True)
                    break
            with open(settings.policies_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.load_policies()
            self.policies_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def _delete_selected_app(self):
        row = self.table_policies.currentRow()
        if row < 0:
            return
        name = self.table_policies.item(row, 0).text()
        try:
            with open(settings.policies_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["blocked_apps"] = [a for a in data.get("blocked_apps", []) if a.get("name") != name]
            with open(settings.policies_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.load_policies()
            self.policies_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))
