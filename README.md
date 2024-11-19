# Power Supply Control Interface for Nice-Power / Kuaiqu

A Python GUI application to control and monitor a Kuaiqu power supply via serial communication.

## Description

This application allows you to remotely control and monitor your Kuaiqu power supply using a graphical user interface built with PyQt6. You can set voltage and current values, turn the output on/off, and visualize real-time readings through live graphs.

## Features

- **Set Voltage and Current**: Input desired voltage and current values.
- **Output Control**: Turn the power supply output on or off.
- **Real-Time Monitoring**: Display live readings of voltage, current, and calculated power.
- **Graphs**: Real-time plotting of voltage and current values.
- **Adjustable Refresh Rate**: Set the data acquisition speed.
- **Pause Functionality**: Pause and resume data acquisition.
- **Dark Mode Support**: Integrates with system dark mode settings for a consistent look.

## Requirements

- Python 3.7 or higher
- [PyQt6](https://pypi.org/project/PyQt6/)
- [PySerial](https://pypi.org/project/pyserial/)
- [Matplotlib](https://pypi.org/project/matplotlib/)
- [NumPy](https://pypi.org/project/numpy/)

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/ElPernotador/nice_power_kuaiqu_ui.git
   cd kuaiqu_power_supply_interface
   ```

2. **Install Dependencies**

   ```bash
   pip install pyqt6 pyserial matplotlib numpy
   ```

3. **Serial Port Permissions**

   Ensure your user has permission to access serial ports:

   ```bash
   sudo usermod -a -G dialout $USER
   # Log out and log back in for the changes to take effect.
   ```

## Usage

1. **Connect the Power Supply**

   - Connect your Kuaiqu power supply to your computer via USB.

2. **Run the Application**

   ```bash
   python kuaiqu_interface.py
   ```

3. **Using the Interface**

   - **Set Voltage and Current**
     - Enter the desired voltage (0.00 V to 60.00 V) and current (0.000 A to 10.000 A).
     - Press *Enter* or click outside the input fields to apply the values.
   - **Output Control**
     - Click the *Play* button to turn on the power supply output.
     - Click the *Stop* button to turn off the output.
   - **Monitoring**
     - View real-time voltage, current, and power readings on the digital displays.
     - The mode (CV or CC) is displayed alongside the readings.
   - **Graphs**
     - Real-time graphs of voltage and current are displayed below the controls.
     - The graphs show the last 50 readings and update at the set refresh rate.
   - **Adjust Refresh Rate**
     - Modify the refresh rate (in milliseconds) using the *Refresh Rate* input.
   - **Pause and Resume**
     - Use the *Pause* button to pause data acquisition.
     - Click again to resume.

## Screenshots

*(Include screenshots of the application if available.)*

## Configuration

- **Adjusting Voltage and Current Ranges**

  If your power supply has different specifications, adjust the ranges in the code:

  ```python
  # In the create_widgets method
  self.voltage_spinbox.setRange(0.0, MAX_VOLTAGE)
  self.current_spinbox.setRange(0.0, MAX_CURRENT)
  ```

  Replace `MAX_VOLTAGE` and `MAX_CURRENT` with the appropriate maximum values for your device.

- **Serial Port Detection**

  The application scans `/dev/ttyUSB0` to `/dev/ttyUSB10` to find the connected power supply. Ensure the device is properly connected and recognized by your system.

## Troubleshooting

- **Permission Errors**

  If you encounter permission errors when accessing the serial port, ensure your user is part of the `dialout` group (see Installation step 3).

- **Icons Not Displayed**

  If the icons are not appearing:

  - Ensure your system has the required icon themes installed.
  - Alternatively, place icon files (`start.png`, `stop.png`, `pause.png`) in the same directory as the script.

- **Dependencies Issues**

  Ensure all dependencies are installed and up to date:

  ```bash
  pip install --upgrade pyqt6 pyserial matplotlib numpy
  ```

- **Serial Communication Errors**

  If the application cannot communicate with the power supply:

  - Check the USB connection.
  - Ensure the power supply is turned on and in remote control mode.
  - Verify that no other application is using the serial port.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **PyQt6** for the GUI framework.
- **PySerial** for serial communication.
- **Matplotlib** and **NumPy** for data visualization.
- **Kuaiqu** for the power supply hardware.

