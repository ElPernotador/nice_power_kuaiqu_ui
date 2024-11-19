import sys
import serial
import threading
import datetime
import matplotlib
import numpy as np

# Usar el backend 'qtagg' compatible con PyQt6
matplotlib.use('qtagg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
    QDoubleSpinBox, QGridLayout, QStatusBar, QMainWindow, QLCDNumber
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPalette, QColor, QFont

# Función para encontrar el dispositivo serial
def find_device():
    for i in range(11):  # De 0 a 10 inclusive
        port = f"/dev/ttyUSB{i}"
        try:
            ser = serial.Serial(port=port, baudrate=9600, timeout=1)
            print(f"Dispositivo encontrado en {port}")
            return ser
        except (serial.SerialException, FileNotFoundError):
            continue
    print("No se encontró el dispositivo en ttyUSB0 a ttyUSB10.")
    return None

# Inicializar conexión serial
ser = find_device()
if ser is None:
    sys.exit()

ser.flush()

# Crear un bloqueo para el puerto serial
ser_lock = threading.Lock()

# Definiciones restantes
FORMAT_SIX_DIGITS = "{:07.3f}"  # Rellenar con ceros, 7 dígitos en total (incluyendo "."), 3 decimales

def psu_write(cmd):
    with ser_lock:
        ser.write(cmd.encode())

def psu_read_decode():
    with ser_lock:
        try:
            ser.timeout = 1  # Asegurar que haya un timeout
            data = ser.read_until(b">")
            response = data.decode(errors='ignore')
            mode_byte = data[1:2]
            if mode_byte == b'1':
                mode = 'CV'  # Voltaje Constante
            elif mode_byte == b'C':
                mode = 'CC'  # Corriente Constante
            else:
                mode = 'Desconocido'
            val = float(data[3:9].decode()) * 1e-3
            return val, mode
        except Exception as e:
            print(f"Error al decodificar la respuesta del dispositivo: {e}")
            return None, 'Desconocido'

def psu_read_ok():
    with ser_lock:
        try:
            ser.timeout = 1  # Establece el timeout a 1 segundo
            data = ser.read_until(b">")
            response = data.decode(errors='ignore')  # Ignorar errores de decodificación
            if 'OK' in response:
                return 1
            else:
                return 0
        except Exception as e:
            print(f"Error al leer la respuesta del dispositivo: {e}")
            return 0

def get_voltage():
    cmd = "<02000000000>"
    psu_write(cmd)
    val, mode = psu_read_decode()
    return val, mode

def get_current():
    cmd = "<04000000000>"
    psu_write(cmd)
    val, mode = psu_read_decode()
    return val, mode

def get_all():
    voltage, mode_v = get_voltage()
    current, mode_c = get_current()
    # Asumimos que el modo es el mismo para voltaje y corriente
    mode = mode_v if mode_v == mode_c else "Desconocido"
    return voltage, current, mode

def set_psu_remote():
    cmd = "<09100000000>"
    psu_write(cmd)
    cmd = "<01004580000>"
    psu_write(cmd)
    cmd = "<03006920000>"
    psu_write(cmd)
    return psu_read_ok()

def set_psu_local():
    cmd = "<09200000000>"
    psu_write(cmd)
    return psu_read_ok()

def set_output_on():
    cmd = "<07000000000>"
    psu_write(cmd)
    return 1  # Asumimos éxito

def set_output_off():
    cmd = "<08000000000>"
    psu_write(cmd)
    return 1  # Asumimos éxito

def set_voltage(val):
    val_formatted = FORMAT_SIX_DIGITS.format(val).replace(".", "")
    cmd = "<01" + val_formatted + "000>"
    psu_write(cmd)
    return psu_read_ok()

def set_current(val):
    val_formatted = FORMAT_SIX_DIGITS.format(val).replace(".", "")
    cmd = "<03" + val_formatted + "000>"
    psu_write(cmd)
    return psu_read_ok()

class PowerSupplyGUI(QMainWindow):
    # Señales personalizadas
    data_updated = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control de Fuente de Alimentación Kuaiqu")

        # Variables
        self.voltage_var = 0.0
        self.current_var = 0.0
        self.actual_voltage = 0.0
        self.actual_current = 0.0
        self.power = 0.0
        self.mode = "Desconocido"
        self.output_state = False  # False = Apagado, True = Encendido
        self.paused = False

        # Datos para los gráficos
        self.voltage_data = []
        self.current_data = []
        self.time_data = []

        # Configuración remota
        set_psu_remote()
        set_output_off()
        set_voltage(0.0)
        set_current(0.0)

        # Aplicar modo oscuro si el sistema está en modo oscuro
        self.apply_dark_mode()

        # Crear los widgets
        self.create_widgets()

        # Iniciar la actualización de mediciones
        self.start_measurement_updates()

    def create_widgets(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Layout superior para controles de seteo
        set_layout = QHBoxLayout()

        # Controles de voltaje
        voltage_label = QLabel("Set Voltaje (V):")
        self.voltage_spinbox = QDoubleSpinBox()
        self.voltage_spinbox.setRange(0.0, 60.0)  # Ajusta según tu fuente
        self.voltage_spinbox.setSingleStep(0.1)
        self.voltage_spinbox.setDecimals(2)
        self.voltage_spinbox.setValue(self.voltage_var)
        self.voltage_spinbox.editingFinished.connect(self.set_voltage)

        # Controles de corriente
        current_label = QLabel("Set Corriente (A):")
        self.current_spinbox = QDoubleSpinBox()
        self.current_spinbox.setRange(0.0, 10.0)  # Ajusta según tu fuente
        self.current_spinbox.setSingleStep(0.1)
        self.current_spinbox.setDecimals(3)
        self.current_spinbox.setValue(self.current_var)
        self.current_spinbox.editingFinished.connect(self.set_current)

        # Botón de salida
        self.output_button = QPushButton()
        self.output_button.setIcon(QIcon.fromTheme("media-playback-start") or QIcon("start.png"))
        self.output_button.clicked.connect(self.toggle_output)
        self.output_button.setToolTip("Encender/Apagar Salida")
        self.output_button.setIconSize(QSize(32, 32))

        # Añadir controles de seteo al layout
        set_layout.addWidget(voltage_label)
        set_layout.addWidget(self.voltage_spinbox)
        set_layout.addWidget(current_label)
        set_layout.addWidget(self.current_spinbox)
        set_layout.addWidget(self.output_button)

        main_layout.addLayout(set_layout)

        # Layout para lecturas
        readings_widget = QWidget()
        readings_layout = QHBoxLayout(readings_widget)
        readings_widget.setFixedHeight(80)  # Establecer altura fija para las lecturas

        # Display de voltaje real
        voltage_read_label = QLabel("Voltaje (V):")
        voltage_read_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.voltage_display = QLCDNumber()
        self.voltage_display.setDigitCount(6)
        self.voltage_display.display("{:.2f}".format(self.actual_voltage))
        self.voltage_display.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.voltage_display.setFixedHeight(60)
        self.voltage_display.setStyleSheet("color: cyan;")
        self.voltage_display.setFont(QFont("Arial", 16))

        # Display de corriente real
        current_read_label = QLabel("Corriente (A):")
        current_read_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_display = QLCDNumber()
        self.current_display.setDigitCount(6)
        self.current_display.display("{:.3f}".format(self.actual_current))
        self.current_display.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.current_display.setFixedHeight(60)
        self.current_display.setStyleSheet("color: yellow;")
        self.current_display.setFont(QFont("Arial", 16))

        # Display de potencia
        power_label = QLabel("Potencia (W):")
        power_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_display = QLCDNumber()
        self.power_display.setDigitCount(6)
        self.power_display.display("{:.2f}".format(self.power))
        self.power_display.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        self.power_display.setFixedHeight(60)
        self.power_display.setStyleSheet("color: magenta;")
        self.power_display.setFont(QFont("Arial", 16))

        # Modo
        self.mode_label = QLabel(f"Modo: {self.mode}")
        self.mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Añadir lecturas al layout
        readings_layout.addWidget(voltage_read_label)
        readings_layout.addWidget(self.voltage_display)
        readings_layout.addWidget(current_read_label)
        readings_layout.addWidget(self.current_display)
        readings_layout.addWidget(power_label)
        readings_layout.addWidget(self.power_display)
        readings_layout.addWidget(self.mode_label)

        main_layout.addWidget(readings_widget)

        # Controles adicionales
        controls_layout = QHBoxLayout()

        # Control de velocidad de lectura
        speed_label = QLabel("Velocidad de lectura (ms):")
        self.speed_spinbox = QDoubleSpinBox()
        self.speed_spinbox.setRange(100, 5000)
        self.speed_spinbox.setSingleStep(100)
        self.speed_spinbox.setValue(200)
        self.speed_spinbox.valueChanged.connect(self.update_speed)
        controls_layout.addWidget(speed_label)
        controls_layout.addWidget(self.speed_spinbox)

        # Botón de pausa
        self.pause_button = QPushButton()
        self.pause_button.setIcon(QIcon.fromTheme("media-playback-pause") or QIcon("pause.png"))
        self.pause_button.clicked.connect(self.toggle_pause)
        self.pause_button.setToolTip("Pausar/Continuar")
        self.pause_button.setIconSize(QSize(32, 32))
        controls_layout.addWidget(self.pause_button)

        main_layout.addLayout(controls_layout)

        # Definir los gráficos
        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.ax_voltage = self.fig.add_subplot(121)  # Gráficos lado a lado
        self.ax_current = self.fig.add_subplot(122)

        self.ax_voltage.set_title("Voltaje (V)")
        self.ax_current.set_title("Corriente (A)")

        self.ax_voltage.grid(True)
        self.ax_current.grid(True)

        self.voltage_line, = self.ax_voltage.plot([], [], color='blue')
        self.current_line, = self.ax_current.plot([], [], color='red')

        # Añadir el canvas (gráficos) y ajustar estiradas
        main_layout.addWidget(self.canvas)
        main_layout.setStretch(0, 0)  # set_layout
        main_layout.setStretch(1, 0)  # readings_widget
        main_layout.setStretch(2, 0)  # controls_layout
        main_layout.setStretch(3, 1)  # canvas (gráficos)

        # Barra de estado para mensajes de error
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def apply_dark_mode(self):
        # Aplicar tema oscuro
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

        QApplication.instance().setPalette(dark_palette)

    def set_voltage(self):
        try:
            voltage = self.voltage_spinbox.value()
            if voltage < 0:
                raise ValueError("El voltaje no puede ser negativo.")
            set_voltage(voltage)
            self.voltage_var = voltage
            self.status_bar.showMessage("Voltaje establecido correctamente.", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"Error al establecer el voltaje: {e}")

    def set_current(self):
        try:
            current = self.current_spinbox.value()
            if current < 0:
                raise ValueError("La corriente no puede ser negativa.")
            set_current(current)
            self.current_var = current
            self.status_bar.showMessage("Corriente establecida correctamente.", 2000)
        except Exception as e:
            self.status_bar.showMessage(f"Error al establecer la corriente: {e}")

    def toggle_output(self):
        if self.output_state:
            set_output_off()
            self.output_button.setIcon(QIcon.fromTheme("media-playback-start") or QIcon("start.png"))
            self.output_state = False
            self.status_bar.showMessage("Salida apagada.", 2000)
            # Limpiar lecturas al apagar la salida
            self.clear_graphs()
        else:
            set_output_on()
            self.output_button.setIcon(QIcon.fromTheme("media-playback-stop") or QIcon("stop.png"))
            self.output_state = True
            self.status_bar.showMessage("Salida encendida.", 2000)
            # Limpiar gráficos al encender la salida
            self.clear_graphs()

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            self.pause_button.setIcon(QIcon.fromTheme("media-playback-start") or QIcon("start.png"))
            self.status_bar.showMessage("Lectura pausada.", 2000)
        else:
            self.pause_button.setIcon(QIcon.fromTheme("media-playback-pause") or QIcon("pause.png"))
            self.status_bar.showMessage("Lectura continuada.", 2000)

    def update_speed(self):
        interval = int(self.speed_spinbox.value())
        self.timer.setInterval(interval)

    def clear_graphs(self):
        self.time_data.clear()
        self.voltage_data.clear()
        self.current_data.clear()
        self.ax_voltage.cla()
        self.ax_current.cla()
        self.ax_voltage.set_title("Voltaje (V)")
        self.ax_current.set_title("Corriente (A)")
        self.ax_voltage.grid(True)
        self.ax_current.grid(True)
        self.voltage_line, = self.ax_voltage.plot([], [], color='blue')
        self.current_line, = self.ax_current.plot([], [], color='red')
        self.canvas.draw()

    def start_measurement_updates(self):
        # Usar QTimer para actualizaciones periódicas
        self.timer = QTimer()
        self.timer.setInterval(int(self.speed_spinbox.value()))  # Actualizar según el valor del spinbox
        self.timer.timeout.connect(self.update_measurements)
        self.timer.start()

    def update_measurements(self):
        if self.paused:
            return
        voltage, current, mode = get_all()
        if voltage is not None and current is not None:
            self.actual_voltage = voltage
            self.actual_current = current
            self.power = voltage * current
            self.mode = mode

            self.voltage_display.display("{:.2f}".format(self.actual_voltage))
            self.current_display.display("{:.3f}".format(self.actual_current))
            self.power_display.display("{:.2f}".format(self.power))
            self.mode_label.setText(f"Modo: {self.mode}")

            # Si la salida está encendida, actualizar gráficos
            if self.output_state:
                current_time = datetime.datetime.now()
                self.time_data.append(current_time)
                self.voltage_data.append(voltage)
                self.current_data.append(current)

                # Limitar datos a las últimas 50 muestras
                self.time_data = self.time_data[-50:]
                self.voltage_data = self.voltage_data[-50:]
                self.current_data = self.current_data[-50:]

                # Convertir tiempos a segundos relativos
                times = [(t - self.time_data[0]).total_seconds() for t in self.time_data]

                # Actualizar gráfico de voltaje
                self.voltage_line.set_data(times, self.voltage_data)
                self.ax_voltage.set_xlim(times[0], times[-1] if times[-1] > times[0] else times[0]+1)
                self.ax_voltage.set_ylim(min(self.voltage_data)*0.95, max(self.voltage_data)*1.05)

                # Actualizar gráfico de corriente
                self.current_line.set_data(times, self.current_data)
                self.ax_current.set_xlim(times[0], times[-1] if times[-1] > times[0] else times[0]+1)
                self.ax_current.set_ylim(min(self.current_data)*0.95, max(self.current_data)*1.05)

                # Ajustar layout para que los gráficos ocupen el máximo espacio
                self.fig.tight_layout()

                # Refrescar el canvas
                self.canvas.draw()
        else:
            # Mostrar mensaje de error
            self.status_bar.showMessage("Error al leer datos del dispositivo.")

    def closeEvent(self, event):
        set_output_off()
        set_psu_local()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = PowerSupplyGUI()
    gui.show()
    sys.exit(app.exec())
