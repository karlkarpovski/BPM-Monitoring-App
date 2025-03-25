import asyncio
import threading
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
from bleak import BleakScanner, BleakClient
import os

HEART_RATE_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

def main_menu():
    """CLI interface for scanning devices and starting heart rate monitoring."""
    while True:
        print("\n📌 Welcome to the Heart Rate Monitor App")
        print("1. Scan for Heartbeat Monitoring Devices")
        print("2. Start Heart Rate Monitoring (GUI)")
        print("0. Exit")
        choice = input("🔹 Enter your choice: ")
        
        if choice == "1":
            os.system('cls' if os.name == 'nt' else 'clear')
            asyncio.run(scanDevices())  # Run BLE scan asynchronously
        
        elif choice == "2":
            os.system('cls' if os.name == 'nt' else 'clear')
            while True:
                device_address = input("🔹 Enter the device address (0 to go back): ")
                if device_address == "0":
                    break
                print(f"📡 Connecting to {device_address}...\n")
                start_heart_rate_gui(device_address)  # Launch GUI

        elif choice == "0":
            print("🚪 Exiting program.")
            break
        else:
            print("⚠️ Invalid choice. Please enter 1, 2, or 0.")

async def scanDevices():
    """Scans for available BLE heart rate devices."""
    print("🔍 Scanning for devices...")
    devices = await BleakScanner.discover()
    if not devices:
        print("❌ No devices found. Ensure your BLE device is in pairing mode.")
        return
    print("\n🔽 Available Devices:")
    for idx, device in enumerate(devices, start=1):
        print(f"{idx}. 📡 {device.name or 'Unknown'} - {device.address}")

def start_heart_rate_gui(device_address):
    """Launches the GUI for heart rate monitoring."""
    root = tk.Tk()
    app = HeartRateApp(root, device_address)
    root.mainloop()

class HeartRateApp:
    def __init__(self, root, device_address):
        self.root = root
        self.device_address = device_address
        self.root.title("💓 Heart Rate Monitor")

        # Label for heart rate display
        self.heartRateLabel = tk.Label(root, text="Heart Rate: -- BPM", font=("Arial", 20))
        self.heartRateLabel.pack(pady=10)

        # Graph setup
        self.fig, self.ax = plt.subplots(figsize=(5, 3))
        self.ax.set_title("Heart Rate Data")
        self.ax.set_ylim(50, 100)
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("BPM")
        self.HeartRateValues = deque([0]*50, maxlen=50)

        # Embed Matplotlib in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack()

        # Start BLE thread
        self.startBLEThread()

    def startBLEThread(self):
        """Starts the BLE event loop in a separate thread to avoid blocking Tkinter."""
        loop = asyncio.new_event_loop()
        threading.Thread(target=lambda: loop.run_until_complete(self.getHeartRate(loop)), daemon=True).start()

    async def getHeartRate(self, loop):
        """Connects to the BLE Device and reads heart rate data in real time."""
        async with BleakClient(self.device_address, loop=loop) as client:
            if await client.is_connected():
                print(f"✅ Connected to {self.device_address}\n")
                print("💓 Heart rate updates will appear in the GUI and terminal.")

                # Read heart rate data
                def heartRateCallback(sender, data):
                    heartRate = data[1]  # Second byte contains the heart rate value
                    print(f"💓 Heart rate: {heartRate} BPM")
                    self.updateHeartRate(heartRate)

                await client.start_notify(HEART_RATE_UUID, heartRateCallback)
                while True:
                    await asyncio.sleep(1)  # Keep the loop running

    def updateHeartRate(self, bpm):
        """Updates the heart rate label and graph dynamically"""
        self.heartRateLabel.config(text=f"Heart Rate: {bpm} BPM")
        self.HeartRateValues.append(bpm)

        # Get current y-axis limits
        y_min, y_max = self.ax.get_ylim()

        # Expand Y-axis ONLY if BPM exceeds current max
        if bpm > y_max:
            y_max = bpm + 5
        if bpm < y_min:
            y_min = bpm - 5

        # Update the graph
        self.ax.clear()
        self.ax.set_title("Heart Rate Data")
        self.ax.set_ylim(y_min, y_max)  # Expand Y-axis dynamically
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("BPM")
        self.ax.plot(self.HeartRateValues, marker="", linestyle="-", color="red")
        self.canvas.draw()

if __name__ == "__main__":
    main_menu()
